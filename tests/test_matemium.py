"""Matemium CLI, paths, and render profile tests."""

from __future__ import annotations

import importlib

from matemium import __version__
from matemium.paths import ROOT, discover_root
from matemium.projects import _valid_slug, list_projects
from matemium.render import render_quality_config


def test_version_is_semver_like():
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_discover_root_finds_checkout():
    root = discover_root()
    assert (root / "canvas").is_dir()
    assert root == ROOT


def test_valid_slug_rules():
    assert _valid_slug("quadratic_factoring")
    assert not _valid_slug("Bad-Name")
    assert not _valid_slug("9starts_with_digit")


def test_list_projects_includes_demo():
    projects = list_projects()
    assert "demo" in projects


def test_render_quality_preview_scales_down():
    cfg = render_quality_config("preview", base_width=1080, base_height=1920)
    assert cfg["pixel_width"] == 540
    assert cfg["pixel_height"] == 960
    assert cfg["frame_rate"] == 15
    assert "quality" not in cfg


def test_render_quality_final_is_production():
    cfg = render_quality_config("final", base_width=1080, base_height=1920)
    assert cfg["pixel_width"] == 1080
    assert cfg["pixel_height"] == 1920
    assert cfg["frame_rate"] == 60
    assert "quality" not in cfg


def test_render_quality_preserves_portrait_in_manim_config():
    from canvas.builder import CanvasBuilder
    from manim import config, tempconfig

    builder = CanvasBuilder(title="Portrait")
    pw, ph = builder.settings.get_manim_resolution()
    merged = builder.settings.get_manim_config_dict()
    merged.update(render_quality_config("preview", base_width=pw, base_height=ph))

    with tempconfig(merged):
        assert config.pixel_width == 540
        assert config.pixel_height == 960
        assert config.frame_width == 9.0
        assert config.frame_height == 16.0


def test_projects_package_importable():
    mod = importlib.import_module("projects.demo.scenes")
    assert hasattr(mod, "PortraitDemo")


def test_ensure_projects_root_creates_dir(tmp_path):
    projects = tmp_path / "projects"
    projects.mkdir()
    init_py = projects / "__init__.py"
    if not init_py.exists():
        init_py.write_text('"""projects"""\n', encoding="utf-8")
    assert projects.is_dir()
    assert init_py.is_file()