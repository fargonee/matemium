"""Viewport-safe zoom containment tests."""

from __future__ import annotations

import pytest

from canvas.dsl import CanvasElement, LayoutBox
from canvas.viewport_fit import (
    OccupationBox,
    _box_from_extents,
    clamp_focus_zoom,
    max_zoom_containing_box,
)


def test_box_from_extents_minimum_size():
    box = _box_from_extents(0.0, 0.1, 0.0, 0.1)
    assert box.width >= 0.25
    assert box.height >= 0.25
    assert box.center_x == pytest.approx(0.05)
    assert box.center_y == pytest.approx(0.05)


def test_max_zoom_caps_wide_element():
    box = OccupationBox(
        width=6.0,
        height=2.0,
        center_x=0.0,
        center_y=0.0,
        x_min=-3.0,
        x_max=3.0,
        y_min=-1.0,
        y_max=1.0,
    )
    z = max_zoom_containing_box(
        box,
        frame_width=9.0,
        frame_height=16.0,
        frame_center_x=0.0,
        frame_center_y=0.0,
        pixel_width=1080,
        pixel_height=1920,
    )
    assert 1.0 <= z <= 2.0


def test_clamp_focus_zoom_never_exceeds_max():
    assert clamp_focus_zoom(5.0, 2.0) == 2.0
    assert clamp_focus_zoom(0.5, 2.0) == 1.0


def test_occupation_box_from_layout_spec():
    from canvas.viewport_fit import occupation_box

    spec = CanvasElement(
        id="x",
        type="Text",
        content="hello",
        canvas_position=(2.0, 3.0),
        layout=LayoutBox(width=4.0, height=2.0),
    )
    box = occupation_box(None, spec)
    assert box.x_min == pytest.approx(0.0)
    assert box.x_max == pytest.approx(4.0)
    assert box.y_min == pytest.approx(2.0)
    assert box.y_max == pytest.approx(4.0)