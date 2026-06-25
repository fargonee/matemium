"""Canvas coordinate conventions — XY sheet plane with Z for depth.

The infinite tape is the **XY plane at z = 0**. Scroll moves the camera along Y.
Z separates layers (overlays, lifted 3D content, future camera dolly), not a
separate "2D mode" pretending the scene is not 3D.
"""

from __future__ import annotations

from .dsl import CanvasElement
from .solids import solid_lift

SHEET_PLANE_Z = 0.0
"""Default plane for text, math, plots, and anchored 3D graphs."""

OVERLAY_Z_EPSILON = 0.001
"""Tiny lift so marks/overlays draw above their parent on the sheet."""

SHEET_TYPES = frozenset({
    "Text",
    "MathTex",
    "GridBoard",
    "GridMark",
    "QuadraticPlot",
    "QuadraticPlotPair",
    "Axes",
    "NumberPlane",
    "ParametricFunction",
    "VGroup",
    "Dot",
    "Arrow",
    "Image",
    "SVG",
})

TILT_VIEW_TYPES = frozenset({"ThreeDGraph", "Surface"})
"""Surface graphs that tilt the camera on reveal when ``pitch`` is set."""

SOLID_3D_TYPES = frozenset({"Solid3D"})
"""Volumetric primitives — center on the tape, straddle z = 0 by default."""

INSPECT_VIEW_TYPES = frozenset({"Solid3D"})
"""Elements that support orbit / inspect camera actions."""


def z_for_element(elem: CanvasElement) -> float:
    """Resolve anchor Z for an element on the sheet."""
    if elem.type in SOLID_3D_TYPES:
        return solid_lift(elem.content)
    if len(elem.canvas_position) > 2:
        explicit = float(elem.canvas_position[2])
        if abs(explicit) > 1e-9:
            return explicit
    if elem.type == "GridMark":
        return SHEET_PLANE_Z + OVERLAY_Z_EPSILON
    return SHEET_PLANE_Z


def frame_center_for_scroll(x: float, y: float) -> tuple[float, float, float]:
    """Camera frame center locked to the sheet plane."""
    return (float(x), float(y), SHEET_PLANE_Z)


def frame_center_for_inspect(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Camera frame center on a volumetric target in 3D space."""
    return (float(x), float(y), float(z))


def is_volumetric_element(elem: CanvasElement) -> bool:
    return elem.type in SOLID_3D_TYPES


def inspect_target_from_mob(mob, elem: CanvasElement) -> tuple[float, float, float]:
    """World-space point the camera should look at during inspect/orbit."""
    center = mob.get_center()
    return (float(center[0]), float(center[1]), float(center[2]))