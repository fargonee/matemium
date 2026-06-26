from __future__ import annotations

import os

from fastapi import APIRouter

from .. import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    supabase_url = os.environ.get("MATEMIUM_SUPABASE_URL", "")
    has_service_key = bool(os.environ.get("MATEMIUM_SUPABASE_SERVICE_ROLE_KEY"))
    return {
        "status": "ok",
        "service": "matemium-server",
        "version": __version__,
        "commit": os.environ.get("COMMIT_SHA") or os.environ.get("GITHUB_SHA") or "unknown",
        "supabase_url": supabase_url[:50] + "..." if supabase_url else "",
        "has_service_role_key": has_service_key,
    }