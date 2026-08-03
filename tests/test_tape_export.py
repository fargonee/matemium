from __future__ import annotations

import numpy as np
from PIL import Image
from manim import BLUE, RED, Dot, Rectangle

from canvas.builder import CanvasBuilder
from canvas.scene import CanvasScene
from canvas.tape_export import (
    TapeExportLayout,
    export_tape_document,
    plan_tape_export,
    render_tape_tiles,
    resolve_tape,
)


def _color_centroid(image: Image.Image, channel: str) -> tuple[float, float]:
    pixels = np.asarray(image.convert("RGB"))
    if channel == "red":
        mask = (pixels[:, :, 0] > 150) & (pixels[:, :, 0] > pixels[:, :, 2] * 1.5)
    else:
        mask = (pixels[:, :, 2] > 150) & (pixels[:, :, 2] > pixels[:, :, 0] * 1.5)
    ys, xs = np.where(mask)
    assert len(xs) > 10
    return float(xs.mean()), float(ys.mean())


def test_resolve_tape_supports_current_dsl_tapes_and_skips_empty_root():
    builder = CanvasBuilder(title="Multiple tapes")
    main = builder.add_tape("main")
    main.add_text("content")

    assert resolve_tape(builder.build()).id == "main"
    assert resolve_tape(builder.build(), "main").id == "main"


def test_natural_export_layout_preserves_geometry_aspect():
    rectangle = Rectangle(width=4.0, height=1.0).move_to((1.5, -2.0, 0.0))
    builder = CanvasBuilder()
    layout = plan_tape_export(
        [rectangle],
        settings=builder.settings,
        margin=0.0,
        high_res_height=200,
        natural_aspect=True,
    )

    assert layout.pixel_height == 200
    assert abs(layout.pixel_width / layout.pixel_height - 4.0) < 0.01
    assert layout.min_x == -0.5
    assert layout.max_x == 3.5
    assert layout.min_y == -2.5
    assert layout.max_y == -1.5


def test_tiled_renderer_keeps_tape_axes_and_does_not_stretch():
    red = Dot((-1.0, 2.0, 0.0), radius=0.28, color=RED)
    blue = Dot((1.0, -2.0, 0.0), radius=0.28, color=BLUE)
    layout = TapeExportLayout(
        min_x=-3.0,
        max_x=3.0,
        min_y=-3.0,
        max_y=3.0,
        pixels_per_unit=64.0,
        pixel_width=384,
        pixel_height=384,
    )

    image = render_tape_tiles(
        [red, blue],
        layout,
        background_color="#111111",
        tile_pixels=96,
    )
    red_x, red_y = _color_centroid(image, "red")
    blue_x, blue_y = _color_centroid(image, "blue")

    assert red_x < blue_x
    assert red_y < blue_y  # positive tape Y is the top of the document
    assert abs((blue_x - red_x) - 2 * 64) < 3.0
    assert abs((blue_y - red_y) - 4 * 64) < 3.0


def test_scene_export_is_repeatable_and_does_not_touch_live_camera_or_mobjects(tmp_path):
    builder = CanvasBuilder(title="Isolated export")
    builder.add_heading("UPRIGHT")
    builder.add_text("camera independent")
    scene = CanvasScene(builder.build())
    scene.populate_from_dsl(play_entries=False)

    live = next(iter(scene.registry._store.values())).mobject
    points_before = live.get_all_points().copy()
    camera_before = (
        scene.camera.frame_center.copy(),
        scene.camera.frame_width,
        scene.camera.frame_height,
        scene.camera.get_phi(),
        scene.camera.get_theta(),
        scene.camera.get_gamma(),
    )

    first = scene.export_full_sheet(
        tmp_path / "first",
        full_tape=True,
        high_res_height=420,
    )
    second = scene.export_full_sheet(
        tmp_path / "second",
        full_tape=True,
        high_res_height=420,
    )

    assert first.read_bytes() == second.read_bytes()
    assert np.array_equal(points_before, live.get_all_points())
    assert np.array_equal(camera_before[0], scene.camera.frame_center)
    assert camera_before[1:] == (
        scene.camera.frame_width,
        scene.camera.frame_height,
        scene.camera.get_phi(),
        scene.camera.get_theta(),
        scene.camera.get_gamma(),
    )


def test_export_tape_document_outputs_requested_natural_dimensions(tmp_path):
    builder = CanvasBuilder(title="Document")
    builder.add_text("wide wide wide")
    builder.add_text("bottom")

    output = export_tape_document(
        builder.build(),
        tmp_path / "tape",
        high_res_height=360,
        margin=0.5,
    )
    image = Image.open(output)

    assert output.suffix == ".png"
    assert image.height == 360
    assert image.width > 100
    assert image.getbbox() == (0, 0, image.width, image.height)
