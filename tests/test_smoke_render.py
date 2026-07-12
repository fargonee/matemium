"""Optional full Manim render smoke test — skipped in default CI."""

from __future__ import annotations

import pytest

from canvas.builder import CanvasBuilder


@pytest.mark.slow
def test_minimal_scene_renders(tmp_path, monkeypatch):
    """Render a tiny scene when Manim + system deps are available."""
    monkeypatch.setenv("MATEMIUM_ROOT", str(tmp_path.parent.parent))
    from matemium.render import render_sheet

    builder = CanvasBuilder(title="Smoke")
    builder.add_text("ok")
    dsl = builder.build()
    out = render_sheet(
        dsl,
        project="_smoke",
        scene_name="Smoke",
        quality="preview",
        media_dir=tmp_path / "media",
    )
    assert out.suffix == ".mp4"
    assert out.is_file()
    assert out.stat().st_size > 0