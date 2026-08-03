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
        
        def _parse_vec(v):
            if isinstance(v, dict):
                return Vector3(float(v.get('x', 0)), float(v.get('y', 0)), float(v.get('z', 0)))
            if isinstance(v, (list, tuple)):
                return Vector3.from_tuple(v)
            return Vector3()

        return cls(
            position=_parse_vec(d.get("position")),
            rotation=_parse_vec(d.get("rotation")),
            scale=d.get("scale", 1.0),
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
        # Full transform: treat the accumulated 'pos' as a local offset on the relative_to's plane
        # (applies its rotation + scale + translation). This makes rotated tapes work for in_object_space content.
        full = local_to_world_point((pos.x, pos.y, pos.z), relative_to)
        pos = Vector3.from_tuple(full)

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


# --- 3D world helpers (added for clarified observation model, phase 1) ---

def _rotation_matrix_from_euler_deg(rx: float, ry: float, rz: float) -> "np.ndarray":
    """Basic Euler rotation matrix (degrees, xyz order). Used for local -> world on rotated TapeObjects etc."""
    import numpy as np
    rx, ry, rz = np.deg2rad([rx, ry, rz])
    cx, cy, cz = np.cos([rx, ry, rz])
    sx, sy, sz = np.sin([rx, ry, rz])
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def local_to_world_point(local_pos: tuple[float, float, float], wt: "WorldTransform") -> tuple[float, float, float]:
    """Transform a local-space point through a WorldTransform (scale + rotation + translation).

    Useful for TapeObject anchors in normal 3D observation and for tape-scroll positioning.
    """
    import numpy as np
    x, y, z = local_pos
    s = float(getattr(wt, "scale", 1.0) or 1.0)
    vec = np.array([x * s, y * s, z * s])
    rot = getattr(wt, "rotation", Vector3())
    R = _rotation_matrix_from_euler_deg(float(rot.x), float(rot.y), float(rot.z))
    rotated = R @ vec
    pos = getattr(wt, "position", Vector3())
    return (
        rotated[0] + float(pos.x),
        rotated[1] + float(pos.y),
        rotated[2] + float(pos.z),
    )


def get_tape_scroll_camera_pose(wt: "WorldTransform") -> tuple[float, float]:
    """Return (phi, theta) so that in TAPE_SCROLL mode the camera looks straight down
    onto the tape surface (angle 0 relative to the tape), i.e. from directly "above" the tape
    along its local normal.

    This replicates the classic sheet behavior (phi=0, theta=-90 for identity) but in the
    tape's local coordinate system. The tape's world_transform is respected for positioning
    the center point, but the viewing direction is always perpendicular to the tape's XY plane
    (from above, Z positive towards the viewer per the tape model).

    Only when observing pulled-up 3D objects (via observe_object / non-tape keyframes, or
    after lifting solids) do we switch to full cinematic angled/perspective views.
    """
    if wt is None:
        return 0.0, -90.0
    rot = getattr(wt, "rotation", Vector3())
    rx = float(getattr(rot, "x", 0.0))
    ry = float(getattr(rot, "y", 0.0))
    # "Angle 0" in tape space: use the classic sheet angles compensated by the tape's rotation.
    # This makes camera look straight from above the (possibly rotated) tape plane.
    # phi matches -rx (or rx with sign), theta = -ry + sheet base.
    phi = -rx
    theta = -ry - 90.0
    # Allow full range but clamp extremes to avoid gimbal oddities
    phi = max(-85.0, min(85.0, phi))
    theta = max(-180.0, min(180.0, theta))
    return phi, theta


def get_rotation_matrix(wt: "WorldTransform") -> "np.ndarray":
    """The 3x3 rotation matrix corresponding to the WorldTransform (Rz @ Ry @ Rx order).
    Used to lock camera orientation for straight-above tape scroll view.
    """
    rot = getattr(wt, "rotation", Vector3())
    return _rotation_matrix_from_euler_deg(
        float(getattr(rot, "x", 0.0)),
        float(getattr(rot, "y", 0.0)),
        float(getattr(rot, "z", 0.0)),
    )
