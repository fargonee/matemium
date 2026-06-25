"""InspectEngine — plays keyframe inspect paths on the canvas camera."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from manim.utils.rate_functions import smooth

from .coords import inspect_target_from_mob
from .dsl import CameraInspect
from .inspect_path import compile_inspect_segments, resolve_inspect_keyframes

if TYPE_CHECKING:
    from manim import Mobject

    from .camera import CameraController
    from .dsl import CanvasElement
    from .scene import CanvasScene


_RATE_MAP = {
    "smooth": smooth,
    "linear": lambda t: t,
}


def _rate_func(name: str) -> Callable:
    return _RATE_MAP.get((name or "smooth").lower(), smooth)


class InspectEngine:
    """Executes ``CameraInspect`` timeline entries via keyframe paths."""

    def __init__(
        self,
        scene: "CanvasScene",
        *,
        camera_ctl: "CameraController",
    ):
        self.scene = scene
        self.camera_ctl = camera_ctl

    def apply(
        self,
        inspect: CameraInspect,
        mob: "Mobject",
        spec: "CanvasElement",
    ) -> None:
        tx, ty, tz = inspect_target_from_mob(mob, spec)
        base_target = (tx, ty, tz)

        keyframes = resolve_inspect_keyframes(
            path=inspect.path,
            preset=inspect.preset,
            preset_kwargs=inspect.preset_kwargs,
            phi=inspect.phi,
            theta=inspect.theta,
            run_time=inspect.run_time,
            hold_time=inspect.hold_time,
            orbit=inspect.orbit,
            orbit_degrees=inspect.orbit_degrees,
            orbit_run_time=inspect.orbit_run_time,
        )
        curve = getattr(inspect, "curve", "smooth") or "smooth"
        segments = compile_inspect_segments(keyframes, base_target, curve=curve)  # type: ignore[arg-type]

        self.scene.registry.pause_far_updaters(self.camera_ctl.current_y, buffer=5.0)

        for segment in segments:
            rate = _rate_func(segment.rate_func)
            anims = self.camera_ctl.pose_anims(
                segment.to_pose,
                segment.run_time,
                rate,
            )
            self.scene.play(*anims, run_time=segment.run_time)
            if segment.hold > 0:
                self.scene.wait(segment.hold)

        if inspect.return_to_sheet:
            self.camera_ctl.return_to_sheet(
                run_time=inspect.return_run_time,
                rate_func=_rate_func(inspect.rate_func),
            )