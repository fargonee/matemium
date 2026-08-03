"""Keyframe inspect paths — universal 3D camera inspection for volumetric elements.

Authors describe *shots* (pose + hold + duration). The engine interpolates between
them (linear or Catmull–Rom). Presets expand to keyframe lists for common moves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

CurveMode = Literal["linear", "smooth"]


@dataclass(frozen=True)
class InspectKeyframe:
    """One camera shot relative to a look-at target."""

    phi: float = 65.0
    theta: float = -50.0
    zoom: float = 1.0
    hold: float = 0.0
    run_time: float = 1.5
    target_offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rate_func: str = "smooth"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phi": self.phi,
            "theta": self.theta,
            "zoom": self.zoom,
            "hold": self.hold,
            "run_time": self.run_time,
            "target_offset": list(self.target_offset),
            "rate_func": self.rate_func,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InspectKeyframe":
        offset = data.get("target_offset", (0.0, 0.0, 0.0))
        if isinstance(offset, list):
            offset = tuple(float(v) for v in offset)
        return cls(
            phi=float(data.get("phi", data.get("pitch", 65.0))),
            theta=float(data.get("theta", data.get("yaw", -50.0))),
            zoom=float(data.get("zoom", 1.0)),
            hold=float(data.get("hold", data.get("hold_time", 0.0))),
            run_time=float(data.get("run_time", 1.5)),
            target_offset=tuple(offset),  # type: ignore[arg-type]
            rate_func=str(data.get("rate_func", "smooth")),
        )


@dataclass(frozen=True)
class CameraPose:
    """Resolved inspect camera state."""

    target_x: float
    target_y: float
    target_z: float
    phi: float
    theta: float
    zoom: float


def _catmull_rom(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2.0 * p1)
        + (-p0 + p2) * t
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _interp_angle(a: float, b: float, t: float) -> float:
    """Shortest-path interpolation for degrees."""
    delta = ((b - a + 180.0) % 360.0) - 180.0
    return a + delta * t


def keyframe_pose(
    keyframe: InspectKeyframe,
    base_target: Tuple[float, float, float],
) -> CameraPose:
    ox, oy, oz = keyframe.target_offset
    bx, by, bz = base_target
    return CameraPose(
        target_x=bx + ox,
        target_y=by + oy,
        target_z=bz + oz,
        phi=keyframe.phi,
        theta=keyframe.theta,
        zoom=max(float(keyframe.zoom), 0.05),
    )


def interpolate_poses(
    a: CameraPose,
    b: CameraPose,
    t: float,
    *,
    curve: CurveMode = "linear",
    prev: Optional[CameraPose] = None,
    next_: Optional[CameraPose] = None,
) -> CameraPose:
    if curve == "smooth" and prev is not None and next_ is not None:
        return CameraPose(
            target_x=_catmull_rom(prev.target_x, a.target_x, b.target_x, next_.target_x, t),
            target_y=_catmull_rom(prev.target_y, a.target_y, b.target_y, next_.target_y, t),
            target_z=_catmull_rom(prev.target_z, a.target_z, b.target_z, next_.target_z, t),
            phi=_catmull_rom(prev.phi, a.phi, b.phi, next_.phi, t),
            theta=_interp_angle(a.theta, b.theta, t)
            if abs(b.theta - a.theta) < 180
            else _catmull_rom(prev.theta, a.theta, b.theta, next_.theta, t),
            zoom=_catmull_rom(prev.zoom, a.zoom, b.zoom, next_.zoom, t),
        )
    return CameraPose(
        target_x=_lerp(a.target_x, b.target_x, t),
        target_y=_lerp(a.target_y, b.target_y, t),
        target_z=_lerp(a.target_z, b.target_z, t),
        phi=_lerp(a.phi, b.phi, t),
        theta=_interp_angle(a.theta, b.theta, t),
        zoom=_lerp(a.zoom, b.zoom, t),
    )


@dataclass
class InspectSegment:
    """One playable transition ending at ``to_pose`` with optional dwell."""

    to_pose: CameraPose
    run_time: float
    hold: float
    rate_func: str


def _normalize_keyframes(
    raw: Sequence[InspectKeyframe | Dict[str, Any]],
) -> List[InspectKeyframe]:
    out: List[InspectKeyframe] = []
    for item in raw:
        if isinstance(item, InspectKeyframe):
            out.append(item)
        elif isinstance(item, dict):
            out.append(InspectKeyframe.from_dict(item))
    return out


def preset_keyframes(
    preset: str,
    *,
    phi: float = 65.0,
    theta: float = -50.0,
    orbit_degrees: float = 360.0,
    orbit_run_time: float = 5.0,
    holds: bool = False,
    steps: Optional[int] = None,
) -> List[InspectKeyframe]:
    """Expand a named preset into an inspect keyframe path."""
    name = preset.lower().replace("-", "_")

    if name in ("orbit", "orbit_slow"):
        n = steps or (16 if name == "orbit_slow" else 12)
        n = max(4, int(n))
        per_rt = float(orbit_run_time) / n
        kfs: List[InspectKeyframe] = []
        for i in range(1, n + 1):
            frac = i / n
            hold = 0.0
            if holds and n >= 4 and i in (n // 4, n // 2, 3 * n // 4, n):
                hold = 0.8 if name == "orbit_slow" else 0.45
            kfs.append(
                InspectKeyframe(
                    phi=phi,
                    theta=theta + orbit_degrees * frac,
                    run_time=per_rt,
                    hold=hold,
                )
            )
        return kfs

    if name == "approach":
        return [
            InspectKeyframe(phi=82.0, theta=theta - 25.0, zoom=0.85, run_time=1.4, hold=0.6),
            InspectKeyframe(phi=phi, theta=theta, zoom=1.0, run_time=1.8, hold=1.0),
            InspectKeyframe(phi=max(phi - 12.0, 35.0), theta=theta + 35.0, zoom=1.05, run_time=1.6, hold=0.8),
        ]

    if name == "peel_back":
        return [
            InspectKeyframe(phi=phi, theta=theta, run_time=1.2, hold=0.5),
            InspectKeyframe(phi=phi + 18.0, theta=theta + 55.0, run_time=1.8, hold=1.0),
            InspectKeyframe(phi=phi + 32.0, theta=theta + 130.0, run_time=2.0, hold=1.2),
            InspectKeyframe(phi=phi + 20.0, theta=theta + 210.0, run_time=1.8, hold=0.8),
        ]

    if name == "cardinals":
        return [
            InspectKeyframe(phi=phi, theta=theta, run_time=1.4, hold=1.2),
            InspectKeyframe(phi=phi, theta=theta + 90.0, run_time=1.5, hold=1.2),
            InspectKeyframe(phi=phi + 8.0, theta=theta + 180.0, run_time=1.5, hold=1.2),
            InspectKeyframe(phi=phi, theta=theta + 270.0, run_time=1.5, hold=1.2),
            InspectKeyframe(phi=phi, theta=theta + 360.0, run_time=1.4, hold=0.6),
        ]

    if name == "sweep":
        return [
            InspectKeyframe(phi=phi + 20.0, theta=theta - 40.0, run_time=1.6, hold=0.7),
            InspectKeyframe(phi=phi, theta=theta + 40.0, run_time=2.0, hold=1.0),
            InspectKeyframe(phi=max(phi - 15.0, 30.0), theta=theta + 120.0, run_time=2.2, hold=1.0),
            InspectKeyframe(phi=phi + 10.0, theta=theta + 220.0, run_time=2.0, hold=0.8),
        ]

    return [InspectKeyframe(phi=phi, theta=theta, run_time=1.6, hold=1.0)]


def legacy_keyframes(
    *,
    phi: float,
    theta: float,
    run_time: float,
    hold_time: float,
    orbit: bool,
    orbit_degrees: float,
    orbit_run_time: float,
) -> List[InspectKeyframe]:
    """Map the original ``CameraInspect`` flags to a keyframe path."""
    kfs = [
        InspectKeyframe(phi=phi, theta=theta, run_time=run_time, hold=hold_time),
    ]
    if orbit:
        kfs.extend(
            preset_keyframes(
                "orbit",
                phi=phi,
                theta=theta,
                orbit_degrees=orbit_degrees,
                orbit_run_time=orbit_run_time,
            )
        )
    return kfs


def resolve_inspect_keyframes(
    *,
    path: Optional[Sequence[InspectKeyframe | Dict[str, Any]]] = None,
    preset: Optional[str] = None,
    preset_kwargs: Optional[Dict[str, Any]] = None,
    phi: float = 65.0,
    theta: float = -50.0,
    run_time: float = 1.6,
    hold_time: float = 0.0,
    orbit: bool = False,
    orbit_degrees: float = 360.0,
    orbit_run_time: float = 4.0,
) -> List[InspectKeyframe]:
    if path:
        return _normalize_keyframes(path)
    if preset:
        kw = dict(preset_kwargs or {})
        kw.setdefault("phi", phi)
        kw.setdefault("theta", theta)
        kw.setdefault("orbit_degrees", orbit_degrees)
        kw.setdefault("orbit_run_time", orbit_run_time)
        return preset_keyframes(preset, **kw)
    return legacy_keyframes(
        phi=phi,
        theta=theta,
        run_time=run_time,
        hold_time=hold_time,
        orbit=orbit,
        orbit_degrees=orbit_degrees,
        orbit_run_time=orbit_run_time,
    )


def densify_path(
    keyframes: Sequence[InspectKeyframe],
    base_target: Tuple[float, float, float],
    *,
    curve: CurveMode = "smooth",
    samples_per_segment: int = 6,
) -> List[InspectKeyframe]:
    """Subdivide a path for smoother motion (preset / AI paths stay sparse)."""
    if len(keyframes) < 2 or curve == "linear":
        return list(keyframes)

    poses = [keyframe_pose(kf, base_target) for kf in keyframes]
    # Preserve the first authored shot. It is a real composition target, and
    # tape-to-world transitions use it as the cut pose before the world fades in.
    dense: List[InspectKeyframe] = [keyframes[0]]
    n = max(2, int(samples_per_segment))
    for i in range(len(keyframes) - 1):
        a = poses[i]
        b = poses[i + 1]
        prev = poses[i - 1] if i > 0 else a
        nxt = poses[i + 2] if i + 2 < len(poses) else b
        src = keyframes[i + 1]
        for step in range(1, n + 1):
            t = step / n
            p = interpolate_poses(a, b, t, curve="smooth", prev=prev, next_=nxt)
            dense.append(
                InspectKeyframe(
                    phi=p.phi,
                    theta=p.theta,
                    zoom=p.zoom,
                    target_offset=(
                        p.target_x - base_target[0],
                        p.target_y - base_target[1],
                        p.target_z - base_target[2],
                    ),
                    run_time=src.run_time / n,
                    hold=src.hold if step == n else 0.0,
                    # The spline already supplies the easing geometry. Reapplying
                    # an ease-in/out to every generated subsegment creates visible
                    # starts and stops along an otherwise smooth camera path.
                    rate_func="linear",
                )
            )
    return dense


def compile_inspect_segments(
    keyframes: Sequence[InspectKeyframe],
    base_target: Tuple[float, float, float],
    *,
    curve: CurveMode = "smooth",
) -> List[InspectSegment]:
    """One segment per keyframe — clear holds, predictable motion.

    When ``curve='smooth'`` and there are multiple keyframes, the path is
    densified first so motion follows a Catmull–Rom spline without author math.
    """
    kfs = list(keyframes)
    # Sparse paths (presets / few shots) get spline densification; long author
    # keyframe lists are already dense enough — interpolating would 6× segments.
    if curve == "smooth" and 2 <= len(kfs) <= 4:
        kfs = densify_path(kfs, base_target, curve=curve)
    segments: List[InspectSegment] = []
    for kf in kfs:
        segments.append(
            InspectSegment(
                to_pose=keyframe_pose(kf, base_target),
                run_time=max(float(kf.run_time), 0.05),
                hold=max(float(kf.hold), 0.0),
                rate_func=kf.rate_func,
            )
        )
    return segments
