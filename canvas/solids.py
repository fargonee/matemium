"""Generic 3D solid primitives — center-anchored on the XY tape at z = 0.

Volumetric shapes straddle the sheet plane by default (half above, half below).
Optional ``lift`` in the content spec raises the whole object for orbit inspection.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from manim import Cube, Mobject, Sphere, VGroup

_DEFAULT_COLOR = "#5eb3ff"
_DEFAULT_OPACITY = 0.82


def parse_solid_content(content: Any) -> Dict[str, Any]:
    """Normalize a solid element payload."""
    if content is None:
        return {}
    if isinstance(content, str):
        return {"shape": content}
    if isinstance(content, dict):
        return dict(content)
    return {"shape": str(content)}


def solid_footprint_size(content: Any) -> float:
    """XY tape occupation for layout (world units)."""
    c = parse_solid_content(content)
    size = float(c.get("size", c.get("side", c.get("diameter", 2.0))))
    return max(size, 0.5)


def solid_lift(content: Any) -> float:
    c = parse_solid_content(content)
    return float(c.get("lift", 0.0))


def make_solid(
    content: Any,
    *,
    target_size: Optional[float] = None,
    target_width: Optional[float] = None,
) -> Mobject:
    """Build a centered volumetric mobject (geometric center at origin)."""
    c = parse_solid_content(content)
    shape = str(c.get("shape", "cube")).lower()
    size = float(c.get("size", c.get("side", c.get("diameter", 2.0))))
    effective = target_width if target_width is not None else target_size
    if effective is not None:
        size = float(effective)

    color = str(c.get("color", _DEFAULT_COLOR))
    opacity = float(c.get("opacity", _DEFAULT_OPACITY))
    stroke_color = c.get("stroke_color")
    stroke_width = float(c.get("stroke_width", 1.0))

    if shape == "sphere":
        radius = size / 2.0
        if "radius" in c:
            radius = float(c["radius"])
        mob: Mobject = Sphere(
            radius=radius,
            color=color,
            fill_opacity=opacity,
        )
    elif shape in ("cube", "box"):
        side = float(c.get("side", size))
        mob = Cube(
            side_length=side,
            fill_color=color,
            fill_opacity=opacity,
            stroke_color=stroke_color or color,
            stroke_width=stroke_width,
        )
    else:
        mob = Cube(
            side_length=size,
            fill_color=color,
            fill_opacity=opacity,
            stroke_color=stroke_color or color,
            stroke_width=stroke_width,
        )

    if effective and mob.get_width() > 0:
        mob.set_width(float(effective))

    return mob


def place_solid_on_tape(
    mob: Mobject,
    canvas_position: tuple[float, float, float],
    content: Any,
) -> Mobject:
    """Anchor solid center on the sheet; apply optional lift along +Z."""
    x, y, _ = canvas_position
    lift = solid_lift(content)
    mob.move_to((float(x), float(y), float(lift)))
    return mob


def make_solid_group(
    solids: list[Dict[str, Any]],
    *,
    target_size: Optional[float] = None,
    target_width: Optional[float] = None,
) -> Mobject:
    """Compose multiple solids sharing one anchor (e.g. sphere inside cube)."""
    size = target_width if target_width is not None else target_size
    parts = [make_solid(spec, target_size=size) for spec in solids]
    group = VGroup(*parts)
    if size and group.get_width() > 0:
        group.set_width(float(size))
    return group