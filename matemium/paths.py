"""Path helpers — keeps engine code separate from per-project outputs."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def discover_root() -> Path:
    """Workspace root: env override, cwd with projects/, dev checkout, else cwd."""
    if env := os.environ.get("MATEMIUM_ROOT"):
        return Path(env).resolve()

    cwd = Path.cwd()
    if (cwd / "projects").is_dir():
        return cwd

    checkout = Path(__file__).resolve().parent.parent
    if (checkout / "projects").is_dir():
        return checkout

    return cwd


ROOT = discover_root()

# User-authored video modules live here (one folder per video/project).
PROJECTS_ROOT = ROOT / "projects"

# Rendered media is isolated per project: outputs/<project>/media/
OUTPUTS_ROOT = ROOT / "outputs"


def ensure_on_path() -> None:
    """Make workspace root importable (canvas, projects.*)."""
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def ensure_projects_root() -> Path:
    """Create projects/ in the workspace when missing (pip-installed usage)."""
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    init_py = PROJECTS_ROOT / "__init__.py"
    if not init_py.is_file():
        init_py.write_text(
            '"""User-authored video projects. Each subfolder is one video/series."""\n',
            encoding="utf-8",
        )
    return PROJECTS_ROOT


def project_dir(slug: str) -> Path:
    return PROJECTS_ROOT / slug


def output_media_dir(slug: str) -> Path:
    """Manim media root for a project (videos, Tex cache, etc.)."""
    path = OUTPUTS_ROOT / slug / "media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_exports_dir(slug: str) -> Path:
    """Static exports (PNG/PDF full tape) for a project."""
    path = OUTPUTS_ROOT / slug / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path