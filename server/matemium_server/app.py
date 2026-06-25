"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .openapi import configure_openapi
from .routes import admin, auth, billing, chat, health, me, webhooks


def create_app() -> FastAPI:
    app = FastAPI(
        title="Matemium Cloud",
        version=__version__,
        description=(
            "Cloud bridge for Matemium — Supabase auth, Lemon Squeezy billing, "
            "entitlements, and chat LLM proxy for the desktop client and website."
        ),
    )

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

    configure_openapi(app)
    return app


app = create_app()