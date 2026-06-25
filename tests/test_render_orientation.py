from canvas.builder import CanvasBuilder
from canvas.dsl import CanvasSettings

from matemium.render import apply_render_orientation, normalize_orientation


def test_normalize_orientation_aliases():
    assert normalize_orientation("portrait") == "portrait"
    assert normalize_orientation("9:16") == "portrait"
    assert normalize_orientation("landscape") == "landscape"
    assert normalize_orientation("youtube") == "landscape"


def test_apply_render_orientation_to_landscape():
    builder = CanvasBuilder(
        title="Lesson",
        canvas_settings=CanvasSettings.for_reels(title="Lesson"),
    )
    builder.add_heading("Hello")
    dsl = apply_render_orientation(builder.build(), "landscape")

    assert dsl.canvas_settings.orientation == "landscape"
    assert dsl.canvas_settings.aspect_ratio == "16:9"
    assert dsl.canvas_settings.pixel_width == 1920
    assert dsl.canvas_settings.pixel_height == 1080


def test_apply_render_orientation_keeps_portrait_default():
    builder = CanvasBuilder(title="Lesson")
    original = builder.build()
    dsl = apply_render_orientation(original, "portrait")

    assert dsl is original
    assert dsl.canvas_settings.aspect_ratio == "9:16"