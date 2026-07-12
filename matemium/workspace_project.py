"""Load and validate desktop project workspaces (arbitrary paths with scenes.py)."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import os
import py_compile
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

from .paths import ensure_on_path


@dataclass(frozen=True)
class Diagnostic:
    line: int
    column: int
    message: str
    severity: str  # "error" | "warning"
    code: str
    source: str  # "syntax" | "ruff"

    def to_dict(self) -> dict[str, str | int]:
        return {
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "severity": self.severity,
            "code": self.code,
            "source": self.source,
        }


def resolve_workspace(params: dict) -> Path:
    raw = params.get("workspace")
    if not raw:
        raise ValueError("workspace is required")
    path = Path(str(raw)).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Workspace not found: {path}")
    return path


def scenes_file(workspace: Path, *, path: str | None = None) -> Path:
    file_path = workspace / (path or "scenes.py")
    if not file_path.is_file():
        raise FileNotFoundError(f"scenes file not found: {file_path}")
    return file_path


def _module_name_for(workspace: Path) -> str:
    digest = hashlib.sha256(str(workspace.resolve()).encode()).hexdigest()[:12]
    return f"matemium_ws_{digest}"


@contextmanager
def workspace_context(workspace: Path) -> Iterator[Path]:
    """Set MATEMIUM_ROOT and sys.path for loading a standalone workspace."""
    workspace = workspace.resolve()
    prev_root = os.environ.get("MATEMIUM_ROOT")
    os.environ["MATEMIUM_ROOT"] = str(workspace)
    ensure_on_path()
    root = str(workspace)
    added = root not in sys.path
    if added:
        sys.path.insert(0, root)
    try:
        yield workspace
    finally:
        if added and root in sys.path:
            sys.path.remove(root)
        if prev_root is None:
            os.environ.pop("MATEMIUM_ROOT", None)
        else:
            os.environ["MATEMIUM_ROOT"] = prev_root


def load_scenes_module(workspace: Path, *, path: str | None = None) -> ModuleType:
    """Import scenes.py from an arbitrary workspace directory.

    A synthetic package is created for the workspace directory so that
    relative imports (e.g. ``from .assets import ...`` or ``from .helpers import ...``)
    work inside scenes.py when loaded from the desktop app. Bare-name imports
    (``from assets import``) continue to work via sys.path as before.
    """
    file_path = scenes_file(workspace, path=path)
    module_name = _module_name_for(workspace)

    with workspace_context(workspace):
        # Use the directory containing the target scenes file as the "package root"
        # for relative imports. This supports both flat workspaces and cases where
        # an alternate `path` puts scenes.py alongside its own assets.py/helpers.py.
        scene_dir = file_path.parent.resolve()
        sd_str = str(scene_dir)

        # Ensure bare imports of siblings work even if scenes.py is not at workspace root.
        added_sd = sd_str not in sys.path
        if added_sd:
            sys.path.insert(0, sd_str)

        try:
            # Clean any previous synthetic package for this workspace hash.
            pkg_name = f"{module_name}_pkg"
            for key in list(sys.modules):
                if key == pkg_name or key.startswith(pkg_name + "."):
                    del sys.modules[key]
            if module_name in sys.modules:
                del sys.modules[module_name]

            # Synthetic package rooted at the scenes file's directory.
            pkg_spec = importlib.util.spec_from_loader(pkg_name, loader=None, is_package=True)
            pkg = importlib.util.module_from_spec(pkg_spec)
            pkg.__path__ = [sd_str]
            sys.modules[pkg_name] = pkg

            # Preload any sibling .py files next to scenes.py (assets.py, helpers.py, ...)
            # under the synthetic package. Bare names are also bound to the same module.
            scene_filename = file_path.name
            for sibling in sorted(scene_dir.glob("*.py")):
                if sibling.name in ("__init__.py", scene_filename):
                    continue
                base = sibling.stem
                qual = f"{pkg_name}.{base}"
                if qual not in sys.modules:
                    sspec = importlib.util.spec_from_file_location(qual, sibling)
                    if sspec and sspec.loader:
                        smod = importlib.util.module_from_spec(sspec)
                        smod.__package__ = pkg_name
                        sys.modules[qual] = smod
                        sspec.loader.exec_module(smod)
                        sys.modules[base] = smod

            # Load scenes.py under the package so __package__ is set and relatives work.
            qual_name = f"{pkg_name}.scenes"
            spec = importlib.util.spec_from_file_location(qual_name, file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load module from {file_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[qual_name] = module
            sys.modules[module_name] = module  # flat alias for back-compat
            module.__name__ = qual_name
            module.__package__ = pkg_name
            spec.loader.exec_module(module)
            return module
        finally:
            if added_sd and sd_str in sys.path:
                sys.path.remove(sd_str)



def list_scenes_in_workspace(workspace: Path, *, path: str | None = None) -> list[str]:
    # Lazy import: do not pull canvas at module load time
    from canvas import CanvasScene

    module = load_scenes_module(workspace, path=path)
    scenes: list[str] = []
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj is CanvasScene:
            continue
        try:
            if issubclass(obj, CanvasScene) and obj.__module__ == module.__name__:
                scenes.append(name)
        except TypeError:
            continue
    return sorted(scenes)


def load_scene_class(
    workspace: Path,
    scene_name: str,
    *,
    path: str | None = None,
) -> Any:
    # Lazy import: do not pull canvas at module load time
    from canvas import CanvasScene

    if not isinstance(scene_name, str):
        raise TypeError(
            f"scene_name must be str, got {type(scene_name).__name__} ({scene_name!r})"
        )
    module = load_scenes_module(workspace, path=path)
    try:
        cls = getattr(module, scene_name)
    except AttributeError as exc:
        available = ", ".join(list_scenes_in_workspace(workspace, path=path)) or "(none)"
        raise AttributeError(
            f"Scene {scene_name!r} not found in {scenes_file(workspace, path=path)}. "
            f"Available: {available}"
        ) from exc
    except TypeError as exc:
        # e.g. if scene_name was None or non-string
        if "attribute name must be string" in str(exc):
            raise TypeError(
                f"scene_name must be str, got {type(scene_name).__name__} ({scene_name!r}) "
                f"when loading from {scenes_file(workspace, path=path)}"
            ) from exc
        raise
    if not inspect.isclass(cls) or not issubclass(cls, CanvasScene):
        raise TypeError(f"{scene_name} is not a CanvasScene subclass")
    return cls


def resolve_scene_name(
    workspace: Path,
    scene: str | None = None,
    *,
    path: str | None = None,
) -> str:
    scenes = list_scenes_in_workspace(workspace, path=path)
    if not scenes:
        raise RuntimeError(f"No CanvasScene classes in {scenes_file(workspace, path=path)}")
    if scene:
        if scene not in scenes:
            raise ValueError(f"Scene {scene!r} not in workspace. Available: {', '.join(scenes)}")
        return scene
    for preferred in ("PortraitDemo", "MyVideo", "Demo", "Main"):
        if preferred in scenes:
            return preferred
    return scenes[0]


def instantiate_scene(
    workspace: Path,
    scene_name: str,
    *,
    path: str | None = None,
) -> Any:
    # Lazy import happens inside load_scene_class
    cls = load_scene_class(workspace, scene_name, path=path)
    with workspace_context(workspace):
        return cls()


def lint_scenes_file(workspace: Path, *, path: str | None = None) -> list[Diagnostic]:
    """Syntax check + optional ruff diagnostics."""
    file_path = scenes_file(workspace, path=path)
    diagnostics: list[Diagnostic] = []

    try:
        py_compile.compile(str(file_path), doraise=True)
    except py_compile.PyCompileError as exc:
        diagnostics.append(_syntax_diagnostic(exc))

    diagnostics.extend(_ruff_diagnostics(file_path))
    return diagnostics


def _syntax_diagnostic(exc: py_compile.PyCompileError) -> Diagnostic:
    line = 1
    column = 0
    msg = str(exc)
    if "line" in msg:
        import re

        match = re.search(r"line (\d+)", msg)
        if match:
            line = int(match.group(1))
    return Diagnostic(
        line=line,
        column=column,
        message=msg,
        severity="error",
        code="syntax-error",
        source="syntax",
    )


def _ruff_diagnostics(file_path: Path) -> list[Diagnostic]:
    try:
        proc = subprocess.run(
            ["ruff", "check", "--output-format", "json", str(file_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return []

    if not proc.stdout.strip():
        return []

    try:
        import json

        rows = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []

    out: list[Diagnostic] = []
    for row in rows:
        loc = row.get("location", {})
        code = str(row.get("code", "ruff"))
        severity = "error" if code.startswith(("F", "E9", "Syntax")) else "warning"
        out.append(
            Diagnostic(
                line=int(loc.get("row") or 1),
                column=int(loc.get("column") or 0),
                message=str(row.get("message", "lint issue")),
                severity=severity,
                code=code,
                source="ruff",
            )
        )
    return out


def check_project(
    workspace: Path,
    *,
    scene: str | None = None,
    path: str | None = None,
) -> dict:
    """Import scene and build DSL without rendering."""
    diagnostics = lint_scenes_file(workspace, path=path)
    errors = [d for d in diagnostics if d.severity == "error"]
    if errors:
        return {
            "ok": False,
            "scene": scene,
            "errors": [d.to_dict() for d in errors],
            "warnings": [d.to_dict() for d in diagnostics if d.severity == "warning"],
        }

    try:
        scene_name = resolve_scene_name(workspace, scene, path=path)
        instance = instantiate_scene(workspace, scene_name, path=path)
        dsl = instance.dsl
        timeline_len = len(dsl.timeline) if dsl else 0
    except (ValueError, RuntimeError) as exc:
        return {
            "ok": False,
            "scene": scene,
            "errors": [
                {
                    "line": 0,
                    "column": 0,
                    "message": str(exc),
                    "severity": "error",
                    "code": "scene-error",
                    "source": "import",
                }
            ],
            "warnings": [],
        }
    except Exception as exc:
        return {
            "ok": False,
            "scene": scene or "",
            "errors": [
                {
                    "line": 0,
                    "column": 0,
                    "message": str(exc),
                    "severity": "error",
                    "code": "import-error",
                    "source": "import",
                }
            ],
            "warnings": [],
        }

    return {
        "ok": True,
        "scene": scene_name,
        "errors": [],
        "warnings": [d.to_dict() for d in diagnostics if d.severity == "warning"],
        "timeline_length": timeline_len,
        "title": dsl.canvas_settings.title if dsl else "",
    }