"""Regression tests for inline styled text layout."""

import pytest

from manim import Text

from canvas.rich_text import TextRun, build_rich_text_mobject


def test_rich_runs_preserve_spaces_at_style_boundaries():
    runs = [
        TextRun("FROM ", color="#55aaff"),
        TextRun("DNA", color="#55aaff"),
        TextRun(" TO ", color="#ffffff"),
        TextRun("PROTEIN", color="#ff77aa"),
    ]

    rich = build_rich_text_mobject(runs)
    plain = Text("FROM DNA TO PROTEIN", font_size=36)

    # Separate styled Text objects have slightly different kerning at run
    # boundaries, but their total width should retain the plain text spacing.
    assert rich.width == pytest.approx(plain.width, rel=0.02)
    assert rich.width > build_rich_text_mobject(
        [TextRun("FROM"), TextRun("DNA"), TextRun("TO"), TextRun("PROTEIN")]
    ).width
