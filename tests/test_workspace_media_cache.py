"""Tests for stable project media cache directory resolution."""

from __future__ import annotations

from pathlib import Path

from matemium.workspace import project_media_cache_dir


def test_project_media_cache_dir_prefers_legacy_renders_media(tmp_path: Path) -> None:
    workspace = tmp_path / "proj"
    legacy = workspace / "renders" / "media"
    partial = legacy / "videos" / "960p15" / "partial_movie_files" / "Scene"
    partial.mkdir(parents=True)
    (partial / "abc.mp4").write_bytes(b"x")

    assert project_media_cache_dir(workspace) == legacy.resolve()


def test_project_media_cache_dir_uses_workspace_media_when_no_legacy(tmp_path: Path) -> None:
    workspace = tmp_path / "proj"
    workspace.mkdir()

    resolved = project_media_cache_dir(workspace)

    assert resolved == (workspace / "media").resolve()
    assert resolved.is_dir()