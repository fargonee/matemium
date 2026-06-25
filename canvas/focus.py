"""Focus effects for the infinite canvas — isolate-zoom (default) and overlay magnifier.

Tool abstraction: scenes call ``add_camera_focus()``; this module implements the effect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Literal

from manim import Animation, FadeIn, FadeOut, Flash, GrowFromCenter, Mobject

from .animations import FLASH_AND_SCALE
from .camera import CameraController
from .viewport_fit import compute_viewport_fit
from .coords import INSPECT_VIEW_TYPES, TILT_VIEW_TYPES
from .dsl import CameraFocus, CanvasElement
from .overlay import create_focus_overlay

if TYPE_CHECKING:
    from .registry import MobjectRegistry
    from .scene import CanvasScene


FocusMode = Literal["isolate", "overlay"]


@dataclass
class OpacitySnapshot:
    """Stored opacities so isolate-focus can restore the canvas."""

    values: Dict[str, float] = field(default_factory=dict)


def snapshot_opacities(registry: "MobjectRegistry", exclude_id: str) -> OpacitySnapshot:
    snap = OpacitySnapshot()
    for uid, entry in registry._store.items():
        if uid == exclude_id:
            continue
        mob = entry.mobject
        if mob is None:
            continue
        try:
            snap.values[uid] = float(mob.get_opacity())
        except Exception:
            snap.values[uid] = 1.0
    return snap


def dim_anims(
    registry: "MobjectRegistry",
    exclude_id: str,
    dim_opacity: float,
) -> List[Animation]:
    anims: List[Animation] = []
    for uid, entry in registry._store.items():
        if uid == exclude_id:
            continue
        mob = entry.mobject
        if mob is not None:
            anims.append(mob.animate.set_opacity(dim_opacity))
    return anims


def restore_opacities(registry: "MobjectRegistry", snap: OpacitySnapshot) -> List[Animation]:
    anims: List[Animation] = []
    for uid, opacity in snap.values.items():
        mob = registry.get(uid)
        if mob is not None:
            anims.append(mob.animate.set_opacity(opacity))
    return anims


class FocusEngine:
    """Applies ``CameraFocus`` timeline entries — the zoom/focus tool abstraction."""

    def __init__(
        self,
        scene: "CanvasScene",
        *,
        camera_ctl: CameraController | None,
        registry: "MobjectRegistry",
        frame_width: float,
        frame_height: float,
    ):
        self.scene = scene
        self.camera_ctl = camera_ctl
        self.registry = registry
        self.frame_width = frame_width
        self.frame_height = frame_height

    def apply(
        self,
        focus: CameraFocus,
        mob: Mobject,
        spec: CanvasElement,
    ) -> None:
        mode = (focus.mode or "isolate").lower()
        if mode == "overlay":
            self._apply_overlay(focus, mob)
        else:
            self._apply_isolate(focus, mob, spec)

    def _apply_isolate(
        self,
        focus: CameraFocus,
        mob: Mobject,
        spec: CanvasElement,
    ) -> None:
        """Dim the tape, pan + frame-zoom to the target, then restore."""
        if self.camera_ctl is None:
            return

        fit = compute_viewport_fit(
            mob,
            spec,
            self.camera_ctl.camera,
            frame_width=self.frame_width,
            frame_height=self.frame_height,
            requested_zoom=float(focus.zoom),
            scroll_x=self.camera_ctl.current_x,
            scroll_y=self.camera_ctl.current_y,
        )
        target_x = fit.center_x
        target_y = fit.center_y
        zoom = fit.zoom

        if self.camera_ctl.is_tilted and spec.type not in (TILT_VIEW_TYPES | INSPECT_VIEW_TYPES):
            self.camera_ctl.return_to_sheet(run_time=min(0.55, focus.run_time))

        snap = snapshot_opacities(self.registry, focus.element_id)
        dim = dim_anims(self.registry, focus.element_id, focus.dim_opacity)

        self.registry.pause_far_updaters(self.camera_ctl.current_y, buffer=5.0)
        self.scene.play(
            *self.camera_ctl.focus_anims(target_x, target_y, zoom, focus.run_time),
            *dim,
            run_time=focus.run_time,
        )
        self.registry.pause_far_updaters(target_y, buffer=3.5)

        if focus.highlight:
            self.scene.play(FLASH_AND_SCALE(mob, scale_factor=1.1, run_time=0.75))

        if focus.hold_time > 0:
            self.scene.wait(focus.hold_time)

        restore = restore_opacities(self.registry, snap)
        if focus.reset_zoom:
            self.scene.play(
                *self.camera_ctl.reset_zoom_anim(focus.reset_run_time),
                *restore,
                run_time=focus.reset_run_time,
            )
        else:
            self.camera_ctl._zoom.set_value(1.0)  # sync updater applies on next frame
            for uid, opacity in snap.values.items():
                m = self.registry.get(uid)
                if m is not None:
                    m.set_opacity(opacity)

    def _apply_overlay(self, focus: CameraFocus, mob: Mobject) -> None:
        """Fixed-screen magnifier — canvas scroll position unchanged."""
        overlay = create_focus_overlay(
            mob,
            frame_width=self.frame_width,
            frame_height=self.frame_height,
            scale=focus.zoom,
        )

        self.scene.add_fixed_in_frame_mobjects(overlay.group)
        self.scene.add(overlay.group)
        self.scene.play(
            FadeIn(overlay.backdrop),
            GrowFromCenter(overlay.clone),
            run_time=focus.run_time,
        )

        if focus.highlight:
            self.scene.play(
                Flash(
                    overlay.clone,
                    line_length=0.28,
                    flash_radius=overlay.clone.width / 2 + 0.15,
                    run_time=0.55,
                ),
            )

        if focus.hold_time > 0:
            self.scene.wait(focus.hold_time)

        if focus.reset_zoom:
            self.scene.play(FadeOut(overlay.group), run_time=focus.reset_run_time)
            self.scene.remove_fixed_in_frame_mobjects(overlay.group)
            self.scene.remove(overlay.group)