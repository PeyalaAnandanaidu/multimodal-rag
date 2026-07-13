import os
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Callable

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from .semantic_cache import SemanticCache, CacheResult


@dataclass
class ManagedCacheResult:
    hit:           bool
    answer:        Optional[str]   = None
    sources:       list            = field(default_factory=list)
    similarity:    float           = 0.0
    from_exact:    bool            = False
    hit_count:     int             = 0
    age_seconds:   float           = 0.0
    latency_ms:    float           = 0.0
    cache_key:     Optional[str]   = None


class CacheManager:
    """
    High-level cache manager wrapping SemanticCache.
    Provides:
    - Simple get/set interface
    - Automatic embedding generation
    - Cache warming
    - Statistics & monitoring
    - PDF lifecycle management
    """

    def __init__(
        self,
        embed_fn:             Callable,   # function to generate embeddings
        max_entries:          int   = 500,
        similarity_threshold: float = 0.92,
        ttl_seconds:          int   = 3600,
    ):
        self.embed_fn = embed_fn
        self.cache    = SemanticCache(
            max_entries          = max_entries,
            similarity_threshold = similarity_threshold,
            ttl_seconds          = ttl_seconds,
        )

    # ──────────────────────────────────────────────────────
    def lookup(self, pdf_id: str, query: str) -> ManagedCacheResult:
        """
        Look up cache for a query.
        Generates embedding internally.
        """
        start = time.perf_counter()

        embedding = self.embed_fn(query)
        result    = self.cache.get(pdf_id, query, embedding)
        latency   = (time.perf_counter() - start) * 1000

        if result.hit:
            return ManagedCacheResult(
                hit        = True,
                answer     = result.answer,
                sources    = result.sources,
                similarity = result.similarity,
                from_exact = result.from_exact,
                hit_count  = result.hit_count,
                age_seconds= result.age_seconds,
                latency_ms = latency,
                cache_key  = result.cache_key,
            )

        return ManagedCacheResult(hit=False, latency_ms=latency)

    def store(
        self,
        pdf_id:    str,
        query:     str,
        answer:    str,
        sources:   list,
        embedding: Optional[np.ndarray] = None
    ) -> str:
        """Store a new cache entry."""
        if embedding is None:
            embedding = self.embed_fn(query)

        return self.cache.set(pdf_id, query, answer, sources, embedding)

    def on_pdf_deleted(self, pdf_id: str):
        """Clear cache when PDF is deleted."""
        self.cache.invalidate_pdf(pdf_id)

    def get_stats(self, pdf_id: Optional[str] = None) -> dict:
        return self.cache.get_stats(pdf_id)

    def clear(self, pdf_id: Optional[str] = None):
        if pdf_id:
            self.cache.invalidate_pdf(pdf_id)
        else:
            self.cache.clear_all()