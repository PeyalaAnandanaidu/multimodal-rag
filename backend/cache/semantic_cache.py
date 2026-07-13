import os
import time
import hashlib
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from threading import Lock

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"


@dataclass
class CacheEntry:
    query:        str
    answer:       str
    sources:      list
    embedding:    np.ndarray
    pdf_id:       str
    created_at:   float             = field(default_factory=time.time)
    accessed_at:  float             = field(default_factory=time.time)
    hit_count:    int               = 0
    query_hash:   str               = ""

    def is_expired(self, ttl_seconds: int) -> bool:
        return (time.time() - self.created_at) > ttl_seconds

    def touch(self):
        self.accessed_at = time.time()
        self.hit_count  += 1


@dataclass
class CacheResult:
    hit:            bool
    answer:         Optional[str]   = None
    sources:        list            = field(default_factory=list)
    similarity:     float           = 0.0
    cache_key:      Optional[str]   = None
    hit_count:      int             = 0
    age_seconds:    float           = 0.0
    from_exact:     bool            = False


class SemanticCache:
    """
    Two-level cache:
    1. Exact match (hash-based) — instant lookup
    2. Semantic match (cosine similarity) — fuzzy lookup

    Scoped per PDF so queries don't leak across documents.
    Supports LRU eviction + TTL expiration.
    """

    def __init__(
        self,
        max_entries:        int   = 500,
        similarity_threshold: float = 0.92,
        ttl_seconds:        int   = 3600,   # 1 hour
        exact_ttl:          int   = 7200,   # 2 hours
    ):
        self.max_entries          = max_entries
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds          = ttl_seconds
        self.exact_ttl            = exact_ttl

        # pdf_id → {query_hash: CacheEntry}
        self._exact_cache:    dict[str, dict[str, CacheEntry]] = {}
        # pdf_id → list[CacheEntry]  (for semantic search)
        self._semantic_cache: dict[str, list[CacheEntry]]      = {}

        self._lock        = Lock()
        self._total_hits  = 0
        self._total_misses= 0

    # ──────────────────────────────────────────────────────
    @staticmethod
    def _hash_query(query: str) -> str:
        return hashlib.sha256(
            query.strip().lower().encode()
        ).hexdigest()

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _init_pdf(self, pdf_id: str):
        if pdf_id not in self._exact_cache:
            self._exact_cache[pdf_id]    = {}
            self._semantic_cache[pdf_id] = []

    def _evict_if_needed(self, pdf_id: str):
        """LRU eviction when max entries reached."""
        semantic = self._semantic_cache[pdf_id]
        exact    = self._exact_cache[pdf_id]

        if len(semantic) >= self.max_entries:
            # Sort by last accessed time, remove oldest 10%
            semantic.sort(key=lambda e: e.accessed_at)
            remove_count = max(1, len(semantic) // 10)
            to_remove    = semantic[:remove_count]

            for entry in to_remove:
                semantic.remove(entry)
                if entry.query_hash in exact:
                    del exact[entry.query_hash]

    def _clean_expired(self, pdf_id: str):
        """Remove expired entries."""
        now      = time.time()
        semantic = self._semantic_cache.get(pdf_id, [])
        exact    = self._exact_cache.get(pdf_id, {})

        # Clean semantic
        expired = [e for e in semantic if e.is_expired(self.ttl_seconds)]
        for entry in expired:
            semantic.remove(entry)
            if entry.query_hash in exact:
                del exact[entry.query_hash]

    # ──────────────────────────────────────────────────────
    def get(
    self,
    pdf_id:    str,
    query:     str,
    embedding: np.ndarray
) -> CacheResult:
     with self._lock:
        self._init_pdf(pdf_id)
        self._clean_expired(pdf_id)

        query_hash    = self._hash_query(query)
        query_lower   = query.strip().lower()

        # ── Level 1: Exact match ───────────────────────
        exact = self._exact_cache[pdf_id]
        if query_hash in exact:
            entry = exact[query_hash]
            if not entry.is_expired(self.exact_ttl):
                entry.touch()
                self._total_hits += 1
                return CacheResult(
                    hit        = True,
                    answer     = entry.answer,
                    sources    = entry.sources,
                    similarity = 1.0,
                    cache_key  = query_hash,
                    hit_count  = entry.hit_count,
                    age_seconds= time.time() - entry.created_at,
                    from_exact = True
                )
            else:
                del exact[query_hash]

        # ── Level 2: Semantic match ────────────────────
        semantic  = self._semantic_cache[pdf_id]
        best_sim  = 0.0
        best_entry: Optional[CacheEntry] = None

        for entry in semantic:
            if entry.is_expired(self.ttl_seconds):
                continue

            sim = self._cosine_similarity(embedding, entry.embedding)
            if sim > best_sim:
                best_sim   = sim
                best_entry = entry

        if best_entry and best_sim >= self.similarity_threshold:
            # ── Extra safety: check query intent matches ──
            cached_lower = best_entry.query.strip().lower()

            # Extract key question words to verify intent
            question_words = {
                "what", "who", "where", "when", "why", "how",
                "which", "list", "summarize", "describe", "explain",
                "email", "phone", "name", "project", "skill",
                "education", "experience", "contact"
            }

            def get_intent_words(q: str) -> set:
                words = set(q.lower().split())
                return words & question_words

            cached_intent = get_intent_words(cached_lower)
            query_intent  = get_intent_words(query_lower)

            # If intents share NO common words, don't use cache
            intent_overlap = len(cached_intent & query_intent)
            if intent_overlap == 0 and len(query_intent) > 0:
                self._total_misses += 1
                return CacheResult(hit=False)

            best_entry.touch()
            self._total_hits += 1
            return CacheResult(
                hit        = True,
                answer     = best_entry.answer,
                sources    = best_entry.sources,
                similarity = best_sim,
                cache_key  = best_entry.query_hash,
                hit_count  = best_entry.hit_count,
                age_seconds= time.time() - best_entry.created_at,
                from_exact = False
            )

        self._total_misses += 1
        return CacheResult(hit=False)

    # ──────────────────────────────────────────────────────
    def set(
        self,
        pdf_id:    str,
        query:     str,
        answer:    str,
        sources:   list,
        embedding: np.ndarray
    ) -> str:
        with self._lock:
            self._init_pdf(pdf_id)
            self._evict_if_needed(pdf_id)

            query_hash = self._hash_query(query)

            entry = CacheEntry(
                query      = query,
                answer     = answer,
                sources    = sources,
                embedding  = embedding.copy(),
                pdf_id     = pdf_id,
                query_hash = query_hash
            )

            # Store in both caches
            self._exact_cache[pdf_id][query_hash]  = entry
            self._semantic_cache[pdf_id].append(entry)

            return query_hash

    # ──────────────────────────────────────────────────────
    def invalidate_pdf(self, pdf_id: str):
        """Remove all cache entries for a PDF."""
        with self._lock:
            self._exact_cache.pop(pdf_id, None)
            self._semantic_cache.pop(pdf_id, None)

    def clear_all(self):
        with self._lock:
            self._exact_cache.clear()
            self._semantic_cache.clear()
            self._total_hits   = 0
            self._total_misses = 0

    def get_stats(self, pdf_id: Optional[str] = None) -> dict:
        with self._lock:
            total_hits   = self._total_hits
            total_misses = self._total_misses
            total        = total_hits + total_misses
            hit_rate     = (total_hits / total * 100) if total > 0 else 0.0

            if pdf_id:
                pdf_entries = len(self._semantic_cache.get(pdf_id, []))
            else:
                pdf_entries = sum(
                    len(v) for v in self._semantic_cache.values()
                )

            return {
                "total_hits":      total_hits,
                "total_misses":    total_misses,
                "hit_rate_pct":    round(hit_rate, 2),
                "cached_entries":  pdf_entries,
                "total_pdfs":      len(self._exact_cache),
                "threshold":       self.similarity_threshold,
                "ttl_seconds":     self.ttl_seconds,
            }