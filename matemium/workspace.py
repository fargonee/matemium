"""Per-job workspace paths for the desktop sidecar."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from .paths import OUTPUTS_ROOT, output_exports_dir, output_media_dir


def resolve_job_workspace(params: dict[str, Any]) -> Path:
    """Resolve an isolated output directory for one sidecar job.

    Priority:
    1. ``output_dir`` in request params (Tauri-managed path)
    2. ``MATEMIUM_WORKSPACE`` environment variable
    3. ``outputs/desktop/<job_id>/`` under the workspace root
    """
    if raw := params.get("output_dir"):
        path = Path(str(raw)).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    if env := os.environ.get("MATEMIUM_WORKSPACE"):
        path = Path(env).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    job_id = str(params.get("job_id") or uuid.uuid4().hex[:12])
    base = OUTPUTS_ROOT / "desktop" / job_id
    base.mkdir(parents=True, exist_ok=True)
    return base


def media_dir_for_workspace(workspace: Path) -> Path:
    path = workspace / "media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_media_cache_dir(workspace: Path) -> Path:
    """Stable Manim cache root for a project workspace.

    Prefers an existing ``renders/media`` tree (legacy desktop layout) when it
    already holds partial movies, otherwise uses ``<workspace>/media`` so cache
    survives preview clears under ``renders/``.
    """
    workspace = workspace.resolve()
    legacy = workspace / "renders" / "media"
    preferred = workspace / "media"
    if legacy.is_dir() and any(legacy.rglob("partial_movie_files")):
        return legacy
    preferred.mkdir(parents=True, exist_ok=True)
    return preferred


def exports_dir_for_workspace(workspace: Path) -> Path:
    path = workspace / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_desktop_media_dir(job_id: str = "desktop") -> Path:
    """Legacy helper — prefer resolve_job_workspace for new IPC commands."""
    return output_media_dir(job_id)


def default_desktop_exports_dir(job_id: str = "desktop") -> Path:
    return output_exports_dir(job_id)