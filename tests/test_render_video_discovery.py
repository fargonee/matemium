from pathlib import Path

import pytest

from matemium.render import find_rendered_video, publish_preview_video


def test_find_rendered_video_ignores_partial_segments(tmp_path: Path):
    media = tmp_path / "media"
    final_dir = media / "videos" / "480p15"
    partial_dir = final_dir / "partial_movie_files" / "CanvasScene"
    partial_dir.mkdir(parents=True)
    final_path = final_dir / "MyScene.mp4"
    partial_path = partial_dir / "segment.mp4"

    final_path.write_bytes(b"final")
    partial_path.write_bytes(b"partial" * 1000)

    found = find_rendered_video(media, scene_name="MyScene", output_name="MyScene", timeout_s=1.0)
    assert found == final_path


def test_publish_preview_video_copies_to_top_level(tmp_path: Path):
    source = tmp_path / "media" / "videos" / "480p15" / "MyScene.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"mp4-data")

    preview = publish_preview_video(source, tmp_path / "renders", "MyScene")
    assert preview == tmp_path / "renders" / "MyScene.mp4"
    assert preview.is_file()
    assert preview.read_bytes() == b"mp4-data"


def test_find_rendered_video_raises_when_missing(tmp_path: Path):
    media = tmp_path / "media"
    media.mkdir()
    with pytest.raises(FileNotFoundError):
        find_rendered_video(media, scene_name="Missing", timeout_s=0.5)