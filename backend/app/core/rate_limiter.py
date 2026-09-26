"""
core/rate_limiter.py
In-memory sliding-window rate limiter for public candidate endpoints.

Prevents brute-force access, scraping, and denial-of-service attempts
on public endpoints (/sessions/{token} and /sessions/{token}/responses).

Features:
  - Thread-safe tracking with automatic timestamp eviction
  - RFC 6585 HTTP 429 Too Many Requests response with Retry-After header
  - Client IP resolution with X-Forwarded-For reverse-proxy support
  - Bypassed in test environment by default to ensure test suite isolation
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, List

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window in-memory rate limiter.

    Parameters:
      requests_per_minute: Maximum allowed requests in a rolling 60-second window.
      name: Identifier for the rate-limited route or bucket.
      enable_in_test: If True, executes even when APP_ENV == 'test'.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        name: str = "default",
        enable_in_test: bool = False,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.name = name
        self.enable_in_test = enable_in_test
        self._window_seconds = 60.0
        self._records: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def __call__(self, request: Request) -> None:
        settings = get_settings()
        if settings.app_env.lower() == "test" and not self.enable_in_test:
            return

        client_ip = request.headers.get("X-Forwarded-For")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        now = time.time()
        key = f"{self.name}:{client_ip}"

        with self._lock:
            timestamps = self._records.get(key, [])
            cutoff = now - self._window_seconds
            # Evict timestamps older than the sliding window
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= self.requests_per_minute:
                oldest = valid_timestamps[0]
                retry_after = max(1, int(oldest + self._window_seconds - now))
                logger.warning(
                    "Rate limit exceeded for %s on %s. Retry-After: %ds",
                    client_ip,
                    self.name,
                    retry_after,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Please wait {retry_after} seconds before trying again.",
                    headers={"Retry-After": str(retry_after)},
                )

            valid_timestamps.append(now)
            self._records[key] = valid_timestamps

    def reset(self) -> None:
        """Clear all stored rate limiting records (useful for test fixtures)."""
        with self._lock:
            self._records.clear()


# Pre-configured instances for candidate routes:
# 1. Candidate viewing assessment questions: 60 requests per minute per IP
candidate_view_limiter = RateLimiter(
    requests_per_minute=60,
    name="candidate_view",
)

# 2. Candidate submitting answers: 15 submissions per minute per IP
candidate_submit_limiter = RateLimiter(
    requests_per_minute=15,
    name="candidate_submit",
)
