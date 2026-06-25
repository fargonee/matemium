"""RotationEngine — plays keyframe rotation paths on Solid3D elements."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from manim import DEGREES, Rotate

from .dsl import SolidRotate
from .rotation_path import (
    axis_vector,
    compile_rotation_segments,
    resolve_rotation_keyframes,
)

if TYPE_CHECKING:
    from manim import Mobject

    from .scene import CanvasScene

from manim.utils.rate_functions import smooth

_RATE_MAP = {
    "smooth": smooth,
    "linear": lambda t: t,
}


def _rate_func(name: str) -> Callable:
    return _RATE_MAP.get((name or "smooth").lower(), smooth)


class RotationEngine:
    """Executes ``SolidRotate`` timeline entries — rotation only, center fixed."""

    def __init__(self, scene: "CanvasScene"):
        self.scene = scene

    def apply(self, action: SolidRotate, mob: "Mobject") -> None:
        keyframes = resolve_rotation_keyframes(
            path=action.path,
            preset=action.preset,
            preset_kwargs=action.preset_kwargs,
            axis=action.axis,
            angle=action.angle,
            space=action.space,  # type: ignore[arg-type]
            run_time=action.run_time,
            hold=action.hold,
        )
        segments = compile_rotation_segments(keyframes)

        for segment in segments:
            kf = segment.keyframe
            if abs(kf.angle) < 1e-6 and kf.hold <= 0:
                continue

            rate = _rate_func(kf.rate_func)
            about = mob.get_center()
            ax = axis_vector(mob, kf.axis, kf.space)

            if abs(kf.angle) >= 1e-6:
                self.scene.play(
                    Rotate(
                        mob,
                        angle=float(kf.angle) * DEGREES,
                        axis=ax,
                        about_point=about,
                        rate_func=rate,
                        run_time=max(kf.run_time, 0.05),
                    ),
                    run_time=max(kf.run_time, 0.05),
                )
            if kf.hold > 0:
                self.scene.wait(kf.hold)