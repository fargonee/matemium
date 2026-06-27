"""OpenAPI schema customization — Bearer auth for RTK Query codegen."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

WEBSITE_PATHS = {
    "/v1/me",
    "/v1/billing/checkout",
    "/v1/billing/portal",
    "/v1/admin/stats",
    "/v1/admin/users",
    "/v1/admin/subscriptions",
    "/v1/admin/users/{user_id}",
    "/v1/admin/subscriptions/{subscription_id}",
    "/v1/admin/llm",
}


def configure_openapi(app: FastAPI) -> None:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        schema.setdefault("components", {})
        schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Supabase access token or dev stub token",
            }
        }

        for path, methods in schema.get("paths", {}).items():
            if path not in WEBSITE_PATHS:
                continue
            for operation in methods.values():
                if isinstance(operation, dict):
                    operation["security"] = [{"BearerAuth": []}]

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]