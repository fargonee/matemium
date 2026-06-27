from __future__ import annotations

import os

from fastapi import APIRouter

from .. import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "matemium-server",
        "version": __version__,
        "commit": os.environ.get("COMMIT_SHA") or os.environ.get("GITHUB_SHA") or "unknown",
    }