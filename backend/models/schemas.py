from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class RiskLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    BLOCK  = "block"


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)
    k:     int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def strip_query(cls, v):
        return v.strip()


class SourceInfo(BaseModel):
    page:     int
    type:     str
    preview:  Optional[str]   = None
    image_id: Optional[str]   = None


class QueryResponse(BaseModel):
    pdf_id:       str
    query:        str
    answer:       str
    sources:      list[SourceInfo]  = []
    from_cache:   bool              = False
    cache_similarity: Optional[float] = None
    warnings:     list[str]         = []
    latency_ms:   Optional[float]   = None


class PDFInfo(BaseModel):
    pdf_id:      str
    filename:    str
    page_count:  int
    doc_count:   int
    image_count: int
    created_at:  str


class PDFUploadResponse(BaseModel):
    success:     bool
    message:     str
    pdf_id:      str
    filename:    str
    page_count:  int
    doc_count:   int
    image_count: int


class CacheStats(BaseModel):
    total_hits:     int
    total_misses:   int
    hit_rate_pct:   float
    cached_entries: int
    total_pdfs:     int
    threshold:      float
    ttl_seconds:    int


class GuardViolation(BaseModel):
    risk_level:  RiskLevel
    violations:  list[str]
    warnings:    list[str]


class HealthResponse(BaseModel):
    status:       str
    api:          str
    cache_stats:  dict
    rate_limiter: str
    guardrails:   str