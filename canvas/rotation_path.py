"""Keyframe rotation paths for Solid3D — turn in place with timed holds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence

import numpy as np
from manim import OUT, RIGHT, UP, Mobject

SpaceMode = Literal["local", "world"]
AxisName = Literal["x", "y", "z"]


@dataclass(frozen=True)
class RotateKeyframe:
    """One rotation step: axis, angle (degrees), hold at the new pose."""

    axis: str = "y"
    angle: float = 90.0
    space: SpaceMode = "local"
    run_time: float = 1.2
    hold: float = 0.0
    rate_func: str = "smooth"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "axis": self.axis,
            "angle": self.angle,
            "space": self.space,
            "run_time": self.run_time,
            "hold": self.hold,
            "rate_func": self.rate_func,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RotateKeyframe":
        return cls(
            axis=str(data.get("axis", "y")).lower(),
            angle=float(data.get("angle", 90.0)),
            space=data.get("space", "local"),  # type: ignore[arg-type]
            run_time=float(data.get("run_time", 1.2)),
            hold=float(data.get("hold", data.get("hold_time", 0.0))),
            rate_func=str(data.get("rate_func", "smooth")),
        )


@dataclass(frozen=True)
class RotateSegment:
    keyframe: RotateKeyframe


_WORLD_AXES = {
    "x": RIGHT,
    "y": UP,
    "z": OUT,
}


def axis_vector(mob: Mobject, axis: str, space: SpaceMode) -> np.ndarray:
    """Resolve a rotation axis in world or local (intrinsic) coordinates."""
    name = str(axis).lower().strip()
    if name not in _WORLD_AXES:
        name = "y"
    if space == "world":
        return np.array(_WORLD_AXES[name], dtype=float)

    center = mob.get_center()
    right = np.array(mob.get_right() - center, dtype=float)
    top = np.array(mob.get_top() - center, dtype=float)
    if name == "x":
        vec = right
    elif name == "y":
        vec = top
    else:
        vec = np.cross(right, top)

    norm = float(np.linalg.norm(vec))
    if norm < 1e-9:
        return np.array(_WORLD_AXES[name], dtype=float)
    return vec / norm


def _normalize_keyframes(
    raw: Sequence[RotateKeyframe | Dict[str, Any]],
) -> List[RotateKeyframe]:
    out: List[RotateKeyframe] = []
    for item in raw:
        if isinstance(item, RotateKeyframe):
            out.append(item)
        elif isinstance(item, dict):
            out.append(RotateKeyframe.from_dict(item))
    return out


def preset_rotation_keyframes(preset: str, **kwargs: Any) -> List[RotateKeyframe]:
    """Named rotation tours — expand to keyframe lists."""
    name = preset.lower().replace("-", "_")
    rt = float(kwargs.get("run_time", 1.2))
    hold = float(kwargs.get("hold", 0.0))

    if name == "show_right":
        return [RotateKeyframe(axis="y", angle=90.0, run_time=rt, hold=hold or 1.2)]
    if name == "show_left":
        return [RotateKeyframe(axis="y", angle=-90.0, run_time=rt, hold=hold or 1.2)]
    if name == "show_back":
        return [RotateKeyframe(axis="y", angle=180.0, run_time=rt, hold=hold or 1.5)]
    if name in ("flip_up", "show_top"):
        return [RotateKeyframe(axis="x", angle=-90.0, run_time=rt, hold=hold or 1.2)]
    if name in ("peek_bottom", "show_bottom"):
        return [RotateKeyframe(axis="x", angle=90.0, run_time=rt, hold=hold or 1.2)]

    if name == "tumble":
        h = hold if hold > 0 else 0.9
        return [
            RotateKeyframe(axis="y", angle=90.0, run_time=rt, hold=h),
            RotateKeyframe(axis="x", angle=35.0, run_time=rt * 0.9, hold=h),
            RotateKeyframe(axis="y", angle=90.0, run_time=rt, hold=h),
            RotateKeyframe(axis="x", angle=-35.0, run_time=rt * 0.9, hold=h * 0.6),
        ]

    if name == "inspect_faces":
        h = hold if hold > 0 else 1.0
        return [
            RotateKeyframe(axis="y", angle=0.0, run_time=0.01, hold=h * 0.5),
            RotateKeyframe(axis="y", angle=90.0, run_time=rt, hold=h),
            RotateKeyframe(axis="y", angle=90.0, run_time=rt, hold=h),
            RotateKeyframe(axis="x", angle=40.0, run_time=rt, hold=h),
            RotateKeyframe(axis="y", angle=90.0, run_time=rt, hold=h * 0.7),
        ]

    return [RotateKeyframe(run_time=rt, hold=hold or 1.0)]


def resolve_rotation_keyframes(
    *,
    path: Optional[Sequence[RotateKeyframe | Dict[str, Any]]] = None,
    preset: Optional[str] = None,
    preset_kwargs: Optional[Dict[str, Any]] = None,
    axis: str = "y",
    angle: float = 90.0,
    space: SpaceMode = "local",
    run_time: float = 1.2,
    hold: float = 0.0,
) -> List[RotateKeyframe]:
    if path:
        return _normalize_keyframes(path)
    if preset:
        return preset_rotation_keyframes(preset, **(preset_kwargs or {}))
    return [
        RotateKeyframe(
            axis=axis,
            angle=angle,
            space=space,
            run_time=run_time,
            hold=hold,
        )
    ]


def compile_rotation_segments(
    keyframes: Sequence[RotateKeyframe],
) -> List[RotateSegment]:
    return [RotateSegment(keyframe=kf) for kf in keyframes]