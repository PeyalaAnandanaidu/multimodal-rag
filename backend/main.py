# ============================================================
# Fix Windows OpenMP conflict — MUST be first
# ============================================================
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"]       = "1"

# ============================================================
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")

from rag_engine import (
    process_pdf, run_rag_pipeline,
    list_pdfs, delete_pdf, get_pdf_info,
    embed_text
)
from guardrails import InputGuardrail, OutputGuardrail, RateLimiter
from cache import CacheManager
from models.schemas import (
    QueryRequest, QueryResponse,
    PDFUploadResponse, CacheStats,
    HealthResponse, SourceInfo
)

# ============================================================
# Logging
# ============================================================
logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("rag-api")

# ============================================================
# Singletons — created once at startup
# ============================================================
input_guard  = InputGuardrail(max_length=2000, strict_mode=True)
output_guard = OutputGuardrail(scrub_pii=True, block_hallucinations=True)
rate_limiter = RateLimiter(global_rpm=60, pdf_rpm=20, upload_per_min=5)
cache_mgr    = CacheManager(
    embed_fn             = embed_text,
    max_entries          = 500,
    similarity_threshold = 0.97,
    ttl_seconds          = 3600,
)

# ============================================================
# App Lifespan
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Multimodal PDF RAG API v2.0 starting...")
    log.info("   ✅ Guardrails  : input + output + rate limiting")
    log.info("   ✅ Cache       : semantic (0.97 threshold) + exact match")
    log.info("   ✅ CLIP model  : loaded")
    yield
    log.info("🛑 Shutting down API...")

# ============================================================
# FastAPI App
# ============================================================
app = FastAPI(
    title       = "Multimodal PDF RAG API",
    description = "PDF Q&A with Guardrails & Semantic Cache",
    version     = "2.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ============================================================
# Utility: Extract Client IP
# ============================================================
def get_client_ip(request: Request) -> str:
    """Extract real client IP from headers or connection."""
    # Support proxies / load balancers
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"

# ============================================================
# Middleware — Request Timing
# ============================================================
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time-Ms"] = f"{duration:.2f}"
    return response

# ============================================================
# ROUTE: Health Check
# ============================================================
@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check(request: Request):
    """API health + cache stats + rate limit info."""
    client_ip   = get_client_ip(request)
    cache_stats = cache_mgr.get_stats()
    rl_stats    = rate_limiter.get_stats(client_ip)

    return HealthResponse(
        status       = "ok",
        api          = "Multimodal PDF RAG v2.0",
        cache_stats  = cache_stats,
        rate_limiter = str(rl_stats),
        guardrails   = "input + output + rate_limiting"
    )

# ============================================================
# ROUTE: Upload PDF
# ============================================================
@app.post(
    "/api/pdfs/upload",
    response_model = PDFUploadResponse,
    tags           = ["PDF Management"]
)
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    """
    Upload and process a PDF file.
    Returns pdf_id used for all subsequent queries.
    """
    client_ip = get_client_ip(request)
    log.info(f"📤 Upload request from {client_ip}: {file.filename}")

    # ── Rate Limit ────────────────────────────────────────
    rl_result = rate_limiter.check_upload(client_ip)
    if not rl_result.allowed:
        log.warning(f"⛔ Upload rate limit hit: {client_ip}")
        raise HTTPException(
            status_code = 429,
            detail      = rl_result.message,
            headers     = {
                "Retry-After":           str(int(rl_result.retry_after or 60)),
                "X-RateLimit-Limit":     str(rl_result.limit),
                "X-RateLimit-Remaining": "0",
            }
        )

    # ── File Type Validation ──────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code = 400,
            detail      = "Only PDF files (.pdf) are supported."
        )

    # ── Read File ─────────────────────────────────────────
    try:
        pdf_bytes = await file.read()
    except Exception as e:
        log.error(f"File read error: {e}")
        raise HTTPException(500, "Failed to read uploaded file.")

    # ── Size Validation ───────────────────────────────────
    if len(pdf_bytes) == 0:
        raise HTTPException(400, "Uploaded file is empty.")

    max_size = 50 * 1024 * 1024  # 50MB
    if len(pdf_bytes) > max_size:
        raise HTTPException(
            400,
            f"File too large ({len(pdf_bytes) // 1024 // 1024}MB). Maximum is 50MB."
        )

    # ── Process PDF ───────────────────────────────────────
    try:
        result = process_pdf(pdf_bytes, file.filename)

        log.info(
            f"✅ PDF processed: '{file.filename}' | "
            f"id={result['pdf_id'][:8]} | "
            f"pages={result['page_count']} | "
            f"docs={result['doc_count']} | "
            f"images={result['image_count']}"
        )

        return PDFUploadResponse(
            success     = True,
            message     = f"'{file.filename}' processed successfully.",
            pdf_id      = result["pdf_id"],
            filename    = result["filename"],
            page_count  = result["page_count"],
            doc_count   = result["doc_count"],
            image_count = result["image_count"],
        )

    except ValueError as e:
        log.warning(f"PDF validation error: {e}")
        raise HTTPException(422, str(e))
    except Exception as e:
        log.error(f"PDF processing error: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to process PDF: {str(e)}")

# ============================================================
# ROUTE: List PDFs
# ============================================================
@app.get("/api/pdfs", tags=["PDF Management"])
def list_all_pdfs():
    """List all uploaded and processed PDFs."""
    pdfs = list_pdfs()
    return {"pdfs": pdfs, "count": len(pdfs)}

# ============================================================
# ROUTE: Get PDF Info
# ============================================================
@app.get("/api/pdfs/{pdf_id}", tags=["PDF Management"])
def get_pdf_details(pdf_id: str):
    """Get metadata for a specific PDF."""
    info = get_pdf_info(pdf_id)
    if not info:
        raise HTTPException(404, f"PDF '{pdf_id}' not found.")
    return info

# ============================================================
# ROUTE: Delete PDF
# ============================================================
@app.delete("/api/pdfs/{pdf_id}", tags=["PDF Management"])
def remove_pdf(pdf_id: str):
    """Delete a PDF and clear its cache."""
    success = delete_pdf(pdf_id)
    if not success:
        raise HTTPException(404, f"PDF '{pdf_id}' not found.")

    # Always clear cache when PDF is deleted
    cache_mgr.on_pdf_deleted(pdf_id)
    log.info(f"🗑️  PDF deleted: {pdf_id}")

    return {
        "success": True,
        "message": f"PDF '{pdf_id}' and its cache deleted."
    }

# ============================================================
# ROUTE: Query PDF  ← Core endpoint
# ============================================================
@app.post(
    "/api/pdfs/{pdf_id}/query",
    response_model = QueryResponse,
    tags           = ["Query"]
)
async def query_pdf(
    pdf_id:       str,
    request_data: QueryRequest,
    request:      Request,
):
    """
    Ask a question about a specific PDF.

    Pipeline:
    1. Rate limiting
    2. PDF existence check
    3. Input guardrails (injection, PII, harmful, enrichment)
    4. Semantic cache lookup
    5. RAG pipeline (on cache miss)
    6. Output guardrails (hallucination, PII scrub, toxicity)
    7. Cache storage
    8. Return response
    """
    start_time = time.perf_counter()
    client_ip  = get_client_ip(request)
    raw_query  = request_data.query.strip()

    log.info(
        f"📥 Query | ip={client_ip} | "
        f"pdf={pdf_id[:8]}... | "
        f"q='{raw_query[:60]}'"
    )

    # ──────────────────────────────────────────────────────
    # STEP 1: Rate Limiting
    # ──────────────────────────────────────────────────────
    rl_result = rate_limiter.check_query(client_ip, pdf_id)
    if not rl_result.allowed:
        log.warning(f"⛔ Rate limit | ip={client_ip} | {rl_result.message}")
        raise HTTPException(
            status_code = 429,
            detail      = rl_result.message,
            headers     = {
                "Retry-After":           str(int(rl_result.retry_after or 60)),
                "X-RateLimit-Limit":     str(rl_result.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset":     str(int(rl_result.reset_in)),
            }
        )

    # ──────────────────────────────────────────────────────
    # STEP 2: PDF Existence Check
    # ──────────────────────────────────────────────────────
    pdf_info = get_pdf_info(pdf_id)
    if not pdf_info:
        raise HTTPException(
            404,
            f"PDF '{pdf_id}' not found. Please upload it first."
        )

    # ──────────────────────────────────────────────────────
    # STEP 3: Input Guardrails
    # ──────────────────────────────────────────────────────
    guard_result = input_guard.validate_and_enrich(raw_query, pdf_id)

    # Block unsafe queries IMMEDIATELY
    if not guard_result.is_safe:
        log.warning(
            f"🛡️  Input BLOCKED | ip={client_ip} | "
            f"risk={guard_result.risk_level} | "
            f"violations={guard_result.violations}"
        )
        raise HTTPException(
            status_code = 400,
            detail      = {
                "error":      "Query blocked by safety guardrails.",
                "violations": guard_result.violations,
                "risk_level": guard_result.risk_level,
                "hint":       "Please rephrase your question."
            }
        )

    # Use enriched + sanitized query from this point forward
    safe_query = guard_result.sanitized or raw_query

    # Log enrichment if query was changed
    if safe_query != raw_query:
        log.info(f"✏️  Query enriched: '{raw_query}' → '{safe_query}'")

    # ──────────────────────────────────────────────────────
    # STEP 4: Semantic Cache Lookup
    # ──────────────────────────────────────────────────────
    cache_result = cache_mgr.lookup(pdf_id, safe_query)

    if cache_result.hit:
        latency_ms = (time.perf_counter() - start_time) * 1000
        log.info(
            f"⚡ Cache HIT | "
            f"exact={cache_result.from_exact} | "
            f"sim={cache_result.similarity:.4f} | "
            f"hits={cache_result.hit_count} | "
            f"latency={latency_ms:.1f}ms"
        )

        return QueryResponse(
            pdf_id            = pdf_id,
            query             = safe_query,
            answer            = cache_result.answer,
            sources           = [
                SourceInfo(**s) for s in cache_result.sources
            ],
            from_cache        = True,
            cache_similarity  = round(cache_result.similarity, 4),
            warnings          = guard_result.warnings,
            latency_ms        = round(latency_ms, 2),
        )

    # ──────────────────────────────────────────────────────
    # STEP 5: RAG Pipeline (cache miss)
    # ──────────────────────────────────────────────────────
    log.info(f"🔍 Cache MISS → RAG pipeline | q='{safe_query[:60]}'")

    try:
        rag_result = run_rag_pipeline(pdf_id, safe_query)
    except Exception as e:
        log.error(f"RAG pipeline error: {e}", exc_info=True)
        raise HTTPException(
            500,
            f"Query processing failed. Please try again. ({type(e).__name__})"
        )

    # Check for RAG errors
    if rag_result.get("error") and not rag_result.get("answer"):
        log.error(f"RAG returned error: {rag_result['error']}")
        raise HTTPException(500, rag_result["error"])

    raw_answer = rag_result.get("answer", "")
    sources    = rag_result.get("sources", [])

    if not raw_answer:
        log.warning("RAG returned empty answer")
        raw_answer = "I could not find relevant information in the document."

    # ──────────────────────────────────────────────────────
    # STEP 6: Output Guardrails
    # ──────────────────────────────────────────────────────
    out_result = output_guard.validate(
        answer       = raw_answer,
        query        = safe_query,
        sources      = sources,
    )

    # Hard block unsafe outputs
    if not out_result.is_safe:
        log.warning(f"🛡️  Output BLOCKED | violations={out_result.violations}")
        raise HTTPException(
            status_code = 500,
            detail      = {
                "error":      "Response blocked by output safety guardrails.",
                "violations": out_result.violations,
            }
        )

    final_answer = out_result.answer

    if out_result.was_modified:
        log.info(
            f"✏️  Output modified by guardrails | "
            f"warnings={out_result.warnings}"
        )

    # ──────────────────────────────────────────────────────
    # STEP 7: Store in Cache
    # ──────────────────────────────────────────────────────
    try:
        cache_key = cache_mgr.store(
            pdf_id  = pdf_id,
            query   = safe_query,
            answer  = final_answer,
            sources = sources,
        )
        log.info(f"💾 Cached | key={cache_key[:8]}...")
    except Exception as e:
        # Cache failure should never break the response
        log.warning(f"Cache store failed (non-fatal): {e}")

    # ──────────────────────────────────────────────────────
    # STEP 8: Build & Return Response
    # ──────────────────────────────────────────────────────
    all_warnings = guard_result.warnings + out_result.warnings
    latency_ms   = (time.perf_counter() - start_time) * 1000

    log.info(
        f"✅ Query done | "
        f"latency={latency_ms:.1f}ms | "
        f"sources={len(sources)} | "
        f"warnings={len(all_warnings)} | "
        f"modified={out_result.was_modified}"
    )

    return QueryResponse(
        pdf_id      = pdf_id,
        query       = safe_query,
        answer      = final_answer,
        sources     = [SourceInfo(**s) for s in sources],
        from_cache  = False,
        warnings    = all_warnings,
        latency_ms  = round(latency_ms, 2),
    )

# ============================================================
# ROUTES: Cache Management
# ============================================================
@app.get("/api/cache/stats", tags=["Cache"])
def get_cache_stats():
    """Global cache statistics."""
    return cache_mgr.get_stats()

@app.get("/api/cache/stats/{pdf_id}", tags=["Cache"])
def get_pdf_cache_stats(pdf_id: str):
    """Cache statistics for a specific PDF."""
    if not get_pdf_info(pdf_id):
        raise HTTPException(404, f"PDF '{pdf_id}' not found.")
    return cache_mgr.get_stats(pdf_id)

@app.delete("/api/cache", tags=["Cache"])
def clear_all_cache():
    """Clear entire cache for all PDFs."""
    cache_mgr.clear()
    log.info("🧹 Full cache cleared")
    return {"success": True, "message": "All cache cleared."}

@app.delete("/api/cache/{pdf_id}", tags=["Cache"])
def clear_pdf_cache(pdf_id: str):
    """Clear cache for a specific PDF only."""
    if not get_pdf_info(pdf_id):
        raise HTTPException(404, f"PDF '{pdf_id}' not found.")
    cache_mgr.clear(pdf_id)
    log.info(f"🧹 Cache cleared for PDF: {pdf_id}")
    return {"success": True, "message": f"Cache cleared for '{pdf_id}'."}

# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host    = "0.0.0.0",
        port    = 8000,
        reload  = True,
        log_level = "info",
    )