"""CanvasBuilder DSL smoke tests."""

from __future__ import annotations

from canvas.builder import CanvasBuilder
from canvas.dsl import CameraInspect, CanvasElement, SolidLift, SolidRotate


def test_builder_produces_timeline_elements():
    builder = CanvasBuilder(title="Test")
    builder.add_heading("Intro")
    builder.add_math(r"x^2 = 4")
    builder.add_text("Done")
    dsl = builder.build()
    assert dsl.canvas_settings.title == "Test"
    elements = [item for item in dsl.timeline if isinstance(item, CanvasElement)]
    assert len(elements) == 3
    assert elements[0].type == "Text"
    assert elements[1].type == "MathTex"


def test_builder_applies_default_row_spacing():
    from canvas.layout import DEFAULT_ROW_MARGIN_BOTTOM

    builder = CanvasBuilder(title="Spacing")
    builder.add_body("Line one")
    builder.add_math(r"a+b")
    dsl = builder.build()
    elements = [item for item in dsl.timeline if isinstance(item, CanvasElement)]
    assert elements[0].layout.margin_bottom == DEFAULT_ROW_MARGIN_BOTTOM
    assert elements[1].layout.margin_bottom == DEFAULT_ROW_MARGIN_BOTTOM


def test_add_3d_does_not_tilt_camera_by_default():
    builder = CanvasBuilder(title="3D default")
    builder.add_3d("z = x^2 - y^2")
    dsl = builder.build()
    elements = [item for item in dsl.timeline if isinstance(item, CanvasElement)]
    assert len(elements) == 1
    assert elements[0].type == "ThreeDGraph"
    assert elements[0].pitch is None


def test_add_3d_pitch_opts_into_camera_tilt():
    builder = CanvasBuilder(title="3D tilt")
    builder.add_3d("z = x^2 - y^2", pitch=45)
    dsl = builder.build()
    elements = [item for item in dsl.timeline if isinstance(item, CanvasElement)]
    assert elements[0].pitch == 45


def test_builder_solid_and_inspect_timeline():
    builder = CanvasBuilder(title="3D")
    builder.add_solid(
        shape="cube",
        size=2.0,
        id="cube_1",
        style={"margin-bottom": 1.0},
    )
    builder.add_solid_lift("cube_1", lift=1.5)
    builder.add_camera_inspect("cube_1", preset="orbit", orbit_run_time=2.0)
    builder.add_solid_rotation("cube_1", preset="show_right")
    dsl = builder.build()

    assert any(isinstance(item, SolidLift) for item in dsl.timeline)
    assert any(isinstance(item, CameraInspect) for item in dsl.timeline)
    assert any(isinstance(item, SolidRotate) for item in dsl.timeline)