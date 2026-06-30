"""Canvas coordinate conventions.

Phase 1 foundation for 3D world model:
- World space is a full 3D coordinate system.
- Objects (including the legacy "tape") live in world space via WorldTransform.
- Legacy sheet assumes the tape at z=0 for backward compatibility.

The infinite tape is the **XY plane at z = 0** (in the tape object's local space).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from .dsl import CanvasElement  # for type hints only, avoid circular

from .solids import solid_lift

# --- Legacy sheet constants (still used for backward compat in sheet mode) ---
SHEET_PLANE_Z = 0.0
"""Default plane for text, math, plots, and anchored 3D graphs (local to tape)."""

OVERLAY_Z_EPSILON = 0.001
"""Tiny lift so marks/overlays draw above their parent on the sheet."""

# --- New world coordinate primitives (Phase 1) ---

@dataclass
class Vector3:
    """Simple 3D vector for positions, rotations, etc."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float]) -> "Vector3":
        if t is None:
            return cls()
        return cls(float(t[0]), float(t[1]), float(t[2]) if len(t) > 2 else 0.0)


@dataclass
class WorldTransform:
    """Transform of an object in world 3D space.

    position: world coordinates (x, y, z)
    rotation: in degrees (rx, ry, rz) — matches existing pitch/yaw convention
    scale: uniform scale (can be extended later)
    """
    position: Vector3 = field(default_factory=Vector3)
    rotation: Vector3 = field(default_factory=Vector3)
    scale: float = 1.0

    def to_dict(self) -> dict:
        return {
            "position": self.position.as_tuple(),
            "rotation": self.rotation.as_tuple(),
            "scale": self.scale,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorldTransform":
        if not d:
            return cls()
        return cls(
            position=Vector3.from_tuple(d.get("position")),
            rotation=Vector3.from_tuple(d.get("rotation")),
            scale=float(d.get("scale", 1.0)),
        )

    def copy(self) -> "WorldTransform":
        return WorldTransform(
            position=Vector3(self.position.x, self.position.y, self.position.z),
            rotation=Vector3(self.rotation.x, self.rotation.y, self.rotation.z),
            scale=self.scale,
        )


def resolve_world_position(
    position: Tuple[float, float, float] | Vector3 | None = None,
    *,
    transform: WorldTransform | None = None,
    relative_to: WorldTransform | None = None,
    anchor: str | None = None,
    anchor_obj: Any | None = None,
) -> Vector3:
    """Resolve a position, optionally relative to another transform or object's anchor.

    Supports:
    - absolute world
    - relative to transform
    - named anchors via anchor_obj.get_anchor(anchor)
    - local offsets on anchors

    Used for relative placement in 3D world + tape objects.
    """
    if position is None:
        pos = Vector3()
    elif isinstance(position, (list, tuple)):
        pos = Vector3.from_tuple(tuple(position))
    else:
        pos = position

    if anchor_obj is not None and anchor:
        try:
            anchor_pos = anchor_obj.get_anchor(anchor)
            pos = Vector3(
                pos.x + anchor_pos.x,
                pos.y + anchor_pos.y,
                pos.z + anchor_pos.z,
            )
        except Exception:
            pass  # fall back

    if transform:
        # Apply this object's local offset
        pos = Vector3(
            pos.x + transform.position.x,
            pos.y + transform.position.y,
            pos.z + transform.position.z,
        )

    if relative_to:
        pos = Vector3(
            pos.x + relative_to.position.x,
            pos.y + relative_to.position.y,
            pos.z + relative_to.position.z,
        )

    return pos

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


def z_for_element(elem: "CanvasElement") -> float:
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


def is_volumetric_element(elem: "CanvasElement") -> bool:
    return elem.type in SOLID_3D_TYPES


def inspect_target_from_mob(mob, elem: CanvasElement) -> tuple[float, float, float]:
    """World-space point the camera should look at during inspect/orbit."""
    center = mob.get_center()
    return (float(center[0]), float(center[1]), float(center[2]))