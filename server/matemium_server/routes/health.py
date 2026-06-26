from __future__ import annotations

import os

from fastapi import APIRouter

from .. import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    supabase_url = os.environ.get("MATEMIUM_SUPABASE_URL", "")
    service_key = os.environ.get("MATEMIUM_SUPABASE_SERVICE_ROLE_KEY", "")
    has_service_key = bool(service_key)
    service_key_prefix = service_key[:20] + "..." if service_key else ""
    return {
        "status": "ok",
        "service": "matemium-server",
        "version": __version__,
        "commit": os.environ.get("COMMIT_SHA") or os.environ.get("GITHUB_SHA") or "unknown",
        "supabase_url": supabase_url[:50] + "..." if supabase_url else "",
        "has_service_role_key": has_service_key,
        "service_key_prefix": service_key_prefix,
    }