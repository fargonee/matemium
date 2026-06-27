"""Production-grade middleware: request IDs, structured logging, security headers.

Lightweight, stdlib + Starlette/FastAPI only.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("matemium.server")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects X-Request-ID (or uses incoming) and stores on request.state."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with timing, status, and user context when available."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", "unknown")

        # Try to extract user early (best-effort, may be None for public routes)
        user_id = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            # We don't verify here; just log a hash or the presence. Full user resolved in deps.
            # For better logs we could parse but keep simple and privacy-friendly.
            user_id = "authed"

        try:
            response = await call_next(request)
        except Exception:
            duration = (time.perf_counter() - start) * 1000
            logger.exception(
                "request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": round(duration, 1),
                    "user": user_id,
                },
            )
            raise

        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration, 1),
                "user": user_id,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds basic security headers suitable for API + SPA consumption."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        # Note: Full CSP is usually best handled at CDN/PaaS level for SPAs.
        # Keep minimal here to avoid breaking inline styles / RTK / Vite.
        return response


def setup_logging() -> None:
    """Configure basic structured-ish logging (works well with uvicorn + PaaS)."""
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s | %(request_id)s | %(method)s %(path)s %(status)s %(duration_ms)sms"
    )
    # Use a filter to inject defaults for non-request logs
    class DefaultExtraFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.__dict__.setdefault("request_id", "-")
            record.__dict__.setdefault("method", "-")
            record.__dict__.setdefault("path", "-")
            record.__dict__.setdefault("status", "-")
            record.__dict__.setdefault("duration_ms", "-")
            return True

    handler.addFilter(DefaultExtraFilter())
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # Avoid double logging from uvicorn
    logger.propagate = False
