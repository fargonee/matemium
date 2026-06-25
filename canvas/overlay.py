"""Viewport overlay layer — magnify canvas elements without moving the camera."""

from __future__ import annotations

from dataclasses import dataclass

from manim import Mobject, ORIGIN, Rectangle, VGroup


@dataclass
class FocusOverlay:
    """Temporary fixed-in-frame magnifier for one canvas element."""

    group: VGroup
    backdrop: Mobject
    clone: Mobject


def create_focus_overlay(
    source: Mobject,
    *,
    frame_width: float,
    frame_height: float,
    scale: float = 1.35,
    max_width_fraction: float = 0.86,
    max_height_fraction: float = 0.42,
    backdrop_opacity: float = 0.62,
) -> FocusOverlay:
    """Build a screen-fixed overlay: dim backdrop + scaled clone centered on viewport.

    The infinite canvas underneath is unchanged; only this layer is added/removed.
    ``scale`` multiplies the auto-fit size (1.0 = fit to safe box, 1.5 = 50% larger).
    """
    clone = source.copy()
    max_w = frame_width * max_width_fraction
    max_h = frame_height * max_height_fraction
    fit = min(
        max_w / max(clone.width, 0.01),
        max_h / max(clone.height, 0.01),
    )
    clone.scale(fit * max(scale, 0.25))
    clone.move_to(ORIGIN)
    if clone.width > max_w:
        clone.scale(max_w / clone.width)
    if clone.height > max_h:
        clone.scale(max_h / clone.height)

    backdrop = Rectangle(
        width=frame_width,
        height=frame_height,
        fill_color="#000000",
        fill_opacity=backdrop_opacity,
        stroke_width=0,
    )
    backdrop.move_to(ORIGIN)

    group = VGroup(backdrop, clone)
    return FocusOverlay(group=group, backdrop=backdrop, clone=clone)