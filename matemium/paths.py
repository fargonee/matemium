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


# --- TinyTeX support (PAD Phase 2) ---
# TinyTeX is a stripped LaTeX distribution (~80-120MB) unpacked to user app data
# on first run. We inject its bin dir into PATH before any Manim/LaTeX work.
# Location examples (see also desktop workspace.rs AppPaths and PRODUCT-ARCHITECTURE-DECISIONS.md):
#   Linux:   ~/.local/share/Matemium/bin/tinytex/...
#   macOS:   ~/Library/Application Support/Matemium/bin/tinytex/...
#   Windows: %LOCALAPPDATA%\Matemium\bin\tinytex\...

def get_tinytex_bin_dir(base_dir: str | Path | None = None) -> Path | None:
    """Return the platform-specific TinyTeX bin directory if it can be located.

    If base_dir is provided (e.g. from Rust: the Matemium app data root), use it.
    Otherwise fall back to common locations or MATEMIUM_TINYTEX_DIR env.
    Returns None if no plausible location exists (caller should not crash).
    """
    if env := os.environ.get("MATEMIUM_TINYTEX_DIR"):
        candidate = Path(env).expanduser().resolve()
        if candidate.exists():
            return candidate

    if base_dir:
        root = Path(base_dir).expanduser().resolve()
    else:
        # Try to use the same convention as desktop AppPaths (data_local_dir / appname)
        # Support both "Matemium" (product spec) and "matemium" (current Rust) for transition.
        candidates = []
        if sys.platform.startswith("win"):
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            if base:
                candidates = [Path(base) / "Matemium", Path(base) / "matemium"]
        elif sys.platform == "darwin":
            candidates = [
                Path.home() / "Library" / "Application Support" / "Matemium",
                Path.home() / "Library" / "Application Support" / "matemium",
            ]
        else:
            xdg = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
            candidates = [xdg / "Matemium", xdg / "matemium"]

        root = None
        for c in candidates:
            if c.exists():
                root = c
                break
        if root is None and candidates:
            root = candidates[0]  # prefer capital, will be created by desktop later

    if not root:
        return None

    tinytex_root = root / "bin" / "tinytex"
    if not tinytex_root.exists():
        return None

    # Platform specific bin subdir (matches the sketch in ai-agent-architecture.md)
    if sys.platform == "win32":
        bin_dir = tinytex_root / "bin" / "windows"
    elif sys.platform == "darwin":
        bin_dir = tinytex_root / "bin" / "universal-darwin"
    else:
        bin_dir = tinytex_root / "bin" / "x86_64-linux"

    if bin_dir.exists():
        return bin_dir.resolve()
    return None


def inject_local_latex_env(base_dir: str | Path | None = None) -> bool:
    """Prepend TinyTeX binaries to PATH before Manim LaTeX operations.

    Safe to call multiple times. Returns True if injection happened.
    Call this lazily right before first use of Manim (see lazy.py).
    """
    tex_bin = get_tinytex_bin_dir(base_dir)
    if tex_bin and tex_bin.exists():
        current = os.environ.get("PATH", "")
        if str(tex_bin) not in current:
            os.environ["PATH"] = str(tex_bin) + os.pathsep + current
        return True
    return False