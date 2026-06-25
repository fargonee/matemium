"""Viewport-safe zoom — cap focus so target bounds never overflow the frame.

Sheet view uses orthographic ``ThreeDCamera`` on the z=0 plane. Containment is
computed in **world coordinates** (frame_center + zoom), not pixel projection —
top-down 3D projection maps Y pixels outside the frame even when the render is
correct.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

from manim import Mobject

from .dsl import CanvasElement

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class OccupationBox:
    """Axis-aligned bounds on the sheet (world units)."""

    width: float
    height: float
    center_x: float
    center_y: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float


@dataclass(frozen=True)
class ViewportFit:
    """Safe focus parameters — zoom capped so borders stay inside the viewport."""

    zoom: float
    center_x: float
    center_y: float
    max_zoom: float
    box: OccupationBox


def _box_from_extents(
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> OccupationBox:
    w = max(float(x_max - x_min), 0.25)
    h = max(float(y_max - y_min), 0.25)
    cx = (x_min + x_max) / 2.0
    cy = (y_min + y_max) / 2.0
    return OccupationBox(w, h, cx, cy, x_min, x_max, y_min, y_max)


def occupation_box(mob: Optional[Mobject], spec: CanvasElement) -> OccupationBox:
    """Occupied width/height and corners on the sheet."""
    if mob is not None:
        try:
            left = float(mob.get_left()[0])
            right = float(mob.get_right()[0])
            bottom = float(mob.get_bottom()[1])
            top = float(mob.get_top()[1])
            return _box_from_extents(left, right, bottom, top)
        except Exception:
            pass

    cx = float(spec.canvas_position[0])
    cy = float(spec.canvas_position[1])
    if spec.layout is not None:
        w = max(float(spec.layout.width), 0.25)
        h = max(float(spec.layout.height), 0.25)
        return _box_from_extents(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)

    return _box_from_extents(cx - 1.0, cx + 1.0, cy - 1.0, cy + 1.0)


def _inset_fractions(
    *,
    pixel_width: float,
    pixel_height: float,
    inset_px: float,
) -> Tuple[float, float]:
    """Shrink usable frame per axis (0–1) from a pixel inset."""
    inset = max(0.0, float(inset_px))
    pw = max(float(pixel_width), 1.0)
    ph = max(float(pixel_height), 1.0)
    fx = max(1.0 - (2.0 * inset) / pw, 0.5)
    fy = max(1.0 - (2.0 * inset) / ph, 0.5)
    return fx, fy


def _visible_half_extents(
    frame_width: float,
    frame_height: float,
    zoom: float,
    *,
    inset_frac_x: float = 1.0,
    inset_frac_y: float = 1.0,
) -> Tuple[float, float]:
    z = max(float(zoom), 1e-6)
    half_w = (float(frame_width) / (2.0 * z)) * inset_frac_x
    half_h = (float(frame_height) / (2.0 * z)) * inset_frac_y
    return half_w, half_h


def _fits_in_sheet_viewport(
    box: OccupationBox,
    frame_center_x: float,
    frame_center_y: float,
    zoom: float,
    *,
    frame_width: float,
    frame_height: float,
    inset_frac_x: float = 1.0,
    inset_frac_y: float = 1.0,
) -> bool:
    """True when the occupation box lies fully inside the visible sheet window."""
    half_w, half_h = _visible_half_extents(
        frame_width,
        frame_height,
        zoom,
        inset_frac_x=inset_frac_x,
        inset_frac_y=inset_frac_y,
    )
    dx = abs(box.center_x - float(frame_center_x))
    dy = abs(box.center_y - float(frame_center_y))
    return dx + box.width / 2.0 <= half_w and dy + box.height / 2.0 <= half_h


def max_zoom_containing_box(
    box: OccupationBox,
    *,
    frame_width: float,
    frame_height: float,
    frame_center_x: float,
    frame_center_y: float,
    pixel_width: float = 1920.0,
    pixel_height: float = 1080.0,
    inset_px: float = 12.0,
    zoom_hi: float = 12.0,
) -> float:
    """Largest zoom where the occupation box stays inside the viewport."""
    inset_frac_x, inset_frac_y = _inset_fractions(
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        inset_px=inset_px,
    )
    usable_w = float(frame_width) * inset_frac_x
    usable_h = float(frame_height) * inset_frac_y

    dx = abs(box.center_x - float(frame_center_x))
    dy = abs(box.center_y - float(frame_center_y))
    half_w_margin = dx + box.width / 2.0
    half_h_margin = dy + box.height / 2.0

    if half_w_margin <= 1e-9 or half_h_margin <= 1e-9:
        return 1.0

    zx = usable_w / (2.0 * half_w_margin)
    zy = usable_h / (2.0 * half_h_margin)
    analytic = min(zx, zy, float(zoom_hi))

    lo, hi = 1.0, max(analytic, 1.0)
    for _ in range(20):
        mid = (lo + hi) / 2.0
        if _fits_in_sheet_viewport(
            box,
            frame_center_x,
            frame_center_y,
            mid,
            frame_width=frame_width,
            frame_height=frame_height,
            inset_frac_x=inset_frac_x,
            inset_frac_y=inset_frac_y,
        ):
            lo = mid
        else:
            hi = mid

    return max(1.0, lo * 0.99)


def compute_viewport_fit(
    mob: Optional[Mobject],
    spec: CanvasElement,
    camera,
    *,
    frame_width: float,
    frame_height: float,
    requested_zoom: float = 2.0,
    inset_px: float = 12.0,
    pan_x: bool = True,
    pan_y: bool = True,
    scroll_x: float = 0.0,
    scroll_y: Optional[float] = None,
) -> ViewportFit:
    """Pan toward occupation center; zoom = min(requested, max safe zoom)."""
    box = occupation_box(mob, spec)

    target_x = box.center_x if pan_x else float(scroll_x)
    target_y = box.center_y if pan_y else (
        float(scroll_y) if scroll_y is not None else box.center_y
    )

    pw = float(getattr(camera, "pixel_width", 1920.0))
    ph = float(getattr(camera, "pixel_height", 1080.0))

    max_z = max_zoom_containing_box(
        box,
        frame_width=frame_width,
        frame_height=frame_height,
        frame_center_x=target_x,
        frame_center_y=target_y,
        pixel_width=pw,
        pixel_height=ph,
        inset_px=inset_px,
    )
    req = max(float(requested_zoom), 1.0)
    safe = min(req, max_z)
    return ViewportFit(
        zoom=max(1.0, safe),
        center_x=target_x,
        center_y=target_y,
        max_zoom=max_z,
        box=box,
    )


def clamp_focus_zoom(requested: float, max_zoom: float) -> float:
    """Never exceed viewport-safe zoom."""
    return min(max(float(requested), 1.0), max(float(max_zoom), 1.0))