"""Lightweight in-process rate limiter.

Suitable for single-instance or small horizontal scale (PaaS). For high scale, replace
with Redis-backed limiter (e.g. slowapi + limits[redis]).

Buckets are per (key, window). Keys are "user:<id>" when authenticated, else "ip:<addr>".
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple

from fastapi import HTTPException, Request, status

from .config import settings  # noqa: E402  (after __future__)


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    def __init__(
        self,
        requests_per_minute: int,
        burst: int | None = None,
    ) -> None:
        self.rpm = max(1, requests_per_minute)
        self.burst = burst or max(2, self.rpm // 3)
        self._buckets: Dict[str, _Bucket] = {}
        self._window = 60.0  # seconds

    def _key(self, request: Request, user_id: str | None) -> str:
        if user_id:
            return f"user:{user_id}"
        # Fallback to IP (note: behind proxy this may need X-Forwarded-For handling)
        client = request.client
        ip = client.host if client else "unknown"
        return f"ip:{ip}"

    def check(self, request: Request, user_id: str | None = None) -> Tuple[bool, dict]:
        """Returns (allowed, headers_dict)."""
        key = self._key(request, user_id)
        now = time.monotonic()

        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(tokens=float(self.burst), last_refill=now)
            self._buckets[key] = bucket

        # Refill
        elapsed = now - bucket.last_refill
        refill = (elapsed / self._window) * self.rpm
        bucket.tokens = min(self.burst, bucket.tokens + refill)
        bucket.last_refill = now

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            remaining = int(bucket.tokens)
            return True, {
                "X-RateLimit-Limit": str(self.rpm),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(now + self._window)),
            }

        # Not allowed
        retry_after = max(1, int(self._window - (now - bucket.last_refill)))
        return False, {
            "X-RateLimit-Limit": str(self.rpm),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(now + retry_after)),
            "Retry-After": str(retry_after),
        }


# Per-plan instances (tunable via settings; read at import)
_free_limiter = RateLimiter(settings.rate_limit_free_rpm)
_pro_limiter = RateLimiter(settings.rate_limit_pro_rpm)


def get_limiter_for_plan(plan: str) -> RateLimiter:
    if plan in ("pro", "teams"):
        return _pro_limiter
    return _free_limiter


async def enforce_rate_limit(request: Request, user_id: str | None, plan: str = "free") -> None:
    """FastAPI dependency-friendly rate limit check.

    Raises 429 on limit.
    """
    limiter = get_limiter_for_plan(plan)
    allowed, headers = limiter.check(request, user_id)
    # We attach headers even on success via response middleware or in route.
    # For simplicity, the route/dependency caller can merge headers.
    request.state.rate_limit_headers = headers
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Upgrade for higher limits.",
            headers=headers,
        )
