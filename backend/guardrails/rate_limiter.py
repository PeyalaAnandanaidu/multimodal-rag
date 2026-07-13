import time
import os
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Optional

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


@dataclass
class RateLimitResult:
    allowed:        bool
    limit:          int
    remaining:      int
    reset_in:       float          # seconds until window resets
    retry_after:    Optional[float] = None
    message:        str            = ""


class RateLimiter:
    """
    Sliding window rate limiter.
    Tracks requests per client IP + per PDF.
    """

    def __init__(
        self,
        # Global limits
        global_rpm:     int = 60,    # requests per minute per IP
        global_rph:     int = 300,   # requests per hour per IP

        # Per-PDF limits
        pdf_rpm:        int = 20,    # requests per minute per PDF

        # Upload limits
        upload_per_min: int = 5,     # uploads per minute per IP
        upload_per_day: int = 50,    # uploads per day per IP
    ):
        self.global_rpm     = global_rpm
        self.global_rph     = global_rph
        self.pdf_rpm        = pdf_rpm
        self.upload_per_min = upload_per_min
        self.upload_per_day = upload_per_day

        # Sliding window queues: {key: deque of timestamps}
        self._windows: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    # ──────────────────────────────────────────────────────
    def _clean_window(self, key: str, window_seconds: int) -> deque:
        """Remove expired timestamps from window."""
        now = time.time()
        dq  = self._windows[key]
        while dq and (now - dq[0]) > window_seconds:
            dq.popleft()
        return dq

    def _check_limit(
        self,
        key:            str,
        limit:          int,
        window_seconds: int
    ) -> RateLimitResult:
        with self._lock:
            dq        = self._clean_window(key, window_seconds)
            now       = time.time()
            count     = len(dq)
            remaining = max(0, limit - count)

            if count >= limit:
                reset_in    = window_seconds - (now - dq[0]) if dq else 0
                retry_after = reset_in
                return RateLimitResult(
                    allowed     = False,
                    limit       = limit,
                    remaining   = 0,
                    reset_in    = reset_in,
                    retry_after = retry_after,
                    message     = (
                        f"Rate limit exceeded. "
                        f"Try again in {int(retry_after)}s."
                    )
                )

            dq.append(now)
            reset_in = window_seconds - (now - dq[0]) if len(dq) > 1 else window_seconds

            return RateLimitResult(
                allowed   = True,
                limit     = limit,
                remaining = remaining - 1,
                reset_in  = reset_in,
                message   = "OK"
            )

    # ──────────────────────────────────────────────────────
    def check_query(self, client_ip: str, pdf_id: str) -> RateLimitResult:
        """Check rate limits for a query request."""

        # 1. Global per-minute limit
        result = self._check_limit(
            key=f"global_rpm:{client_ip}",
            limit=self.global_rpm,
            window_seconds=60
        )
        if not result.allowed:
            return result

        # 2. Global per-hour limit
        result = self._check_limit(
            key=f"global_rph:{client_ip}",
            limit=self.global_rph,
            window_seconds=3600
        )
        if not result.allowed:
            return result

        # 3. Per-PDF per-minute limit
        result = self._check_limit(
            key=f"pdf_rpm:{client_ip}:{pdf_id}",
            limit=self.pdf_rpm,
            window_seconds=60
        )
        return result

    def check_upload(self, client_ip: str) -> RateLimitResult:
        """Check rate limits for PDF upload."""

        # Per-minute upload limit
        result = self._check_limit(
            key=f"upload_rpm:{client_ip}",
            limit=self.upload_per_min,
            window_seconds=60
        )
        if not result.allowed:
            return result

        # Per-day upload limit
        result = self._check_limit(
            key=f"upload_rpd:{client_ip}",
            limit=self.upload_per_day,
            window_seconds=86400
        )
        return result

    def get_stats(self, client_ip: str) -> dict:
        """Get current rate limit stats for a client."""
        now = time.time()
        stats = {}

        for key_suffix, window in [
            (f"global_rpm:{client_ip}", 60),
            (f"global_rph:{client_ip}", 3600),
            (f"upload_rpm:{client_ip}", 60),
        ]:
            dq = self._clean_window(key_suffix, window)
            stats[key_suffix] = {
                "count": len(dq),
                "window_seconds": window
            }

        return stats