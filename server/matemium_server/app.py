"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import settings
import logging

from .middleware import (
    LoggingMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    setup_logging,
)
from .openapi import configure_openapi
from .routes import admin, audio, auth, billing, chat, health, me, settings as settings_router, webhooks


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="Matemium Cloud",
        version=__version__,
        description=(
            "Cloud bridge for Matemium — Supabase auth, Lemon Squeezy billing, "
            "entitlements, and chat LLM proxy for the desktop client and website."
        ),
    )

    # Order: outermost (first to execute on request) first
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/v1")
    app.include_router(me.router, prefix="/v1")
    app.include_router(billing.router, prefix="/v1")
    app.include_router(admin.router, prefix="/v1")
    app.include_router(webhooks.router, prefix="/v1")
    app.include_router(chat.router, prefix="/v1")
    app.include_router(audio.router, prefix="/v1")
    app.include_router(settings_router.router, prefix="/v1")

    # Global error handling for consistent production responses
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        headers = getattr(exc, "headers", None) or {}
        if request_id:
            headers = {**headers, "X-Request-ID": request_id}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "detail": exc.detail,
                "request_id": request_id,
            },
            headers=headers or None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "detail": exc.errors(),
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger = logging.getLogger("matemium.server")
        logger.exception("unhandled error", extra={"request_id": request_id or "-"})
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "detail": "An unexpected error occurred",
                "request_id": request_id,
            },
        )

    configure_openapi(app)
    return app


app = create_app()