"""Tests for exact Manim segment counting."""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from matemium.ipc.duration import estimate_animation_count
from matemium.play_count import count_scene_plays, resolve_animation_count
from matemium.workspace_project import instantiate_scene


def _demo_dsl(scene_name: str):
    workspace = Path(tempfile.mkdtemp())
    shutil.copy(
        Path(__file__).resolve().parents[1] / "projects/demo/scenes.py",
        workspace / "scenes.py",
    )
    return instantiate_scene(workspace, scene_name).dsl


def test_count_scene_plays_matches_construct_dry_run():
    dsl = _demo_dsl("PortraitDemo")
    assert count_scene_plays(dsl) == 13
    assert estimate_animation_count(dsl) < 13


def test_resolve_animation_count_returns_exact_total():
    dsl = _demo_dsl("BuilderDemo")
    assert resolve_animation_count(dsl) == 13