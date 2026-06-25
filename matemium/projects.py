"""Discover and scaffold user video projects under projects/."""

from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path
from typing import Type

from canvas import CanvasScene

from importlib import resources

from .paths import PROJECTS_ROOT, ensure_projects_root, project_dir


def _template_dir() -> Path:
    workspace = project_dir("_template")
    if workspace.is_dir():
        return workspace
    bundled = resources.files("matemium.templates") / "_template"
    return Path(bundled)


def _valid_slug(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", slug))


def list_projects() -> list[str]:
    if not PROJECTS_ROOT.exists():
        return []
    return sorted(
        p.name
        for p in PROJECTS_ROOT.iterdir()
        if p.is_dir()
        and not p.name.startswith("_")
        and (p / "scenes.py").is_file()
    )


def list_scenes(project_slug: str) -> list[str]:
    module = importlib.import_module(f"projects.{project_slug}.scenes")
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


def load_scene_class(project_slug: str, scene_name: str) -> Type[CanvasScene]:
    if not _valid_slug(project_slug):
        raise ValueError(f"Invalid project slug: {project_slug!r}")
    if not project_dir(project_slug).is_dir():
        raise FileNotFoundError(f"Project not found: {project_slug} (expected projects/{project_slug}/)")
    module = importlib.import_module(f"projects.{project_slug}.scenes")
    try:
        cls = getattr(module, scene_name)
    except AttributeError as exc:
        available = ", ".join(list_scenes(project_slug)) or "(none)"
        raise AttributeError(
            f"Scene {scene_name!r} not found in projects/{project_slug}/scenes.py. "
            f"Available: {available}"
        ) from exc
    if not inspect.isclass(cls) or not issubclass(cls, CanvasScene):
        raise TypeError(f"{scene_name} is not a CanvasScene subclass")
    return cls


def default_scene(project_slug: str) -> str:
    scenes = list_scenes(project_slug)
    if not scenes:
        raise RuntimeError(f"No CanvasScene classes in projects/{project_slug}/scenes.py")
    for preferred in ("PortraitDemo", "Demo", "Main"):
        if preferred in scenes:
            return preferred
    return scenes[0]


def scaffold_project(slug: str) -> Path:
    if not _valid_slug(slug):
        raise ValueError(
            "Project slug must be lowercase letters, digits, underscores; start with a letter."
        )
    ensure_projects_root()
    target = project_dir(slug)
    if target.exists():
        raise FileExistsError(f"Project already exists: projects/{slug}/")

    template = _template_dir()
    if not template.is_dir():
        raise FileNotFoundError("Missing project scaffold template")

    target.mkdir(parents=True)
    (target / "__init__.py").write_text("", encoding="utf-8")
    scenes_src = (template / "scenes.py").read_text(encoding="utf-8")
    scenes_src = scenes_src.replace("PROJECT_SLUG", slug)
    scenes_src = scenes_src.replace("MyVideo", _title_case(slug))
    (target / "scenes.py").write_text(scenes_src, encoding="utf-8")
    return target


def _title_case(slug: str) -> str:
    return "".join(part.capitalize() for part in slug.split("_"))