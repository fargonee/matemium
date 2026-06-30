"""Camera controller for the infinite XY sheet (z = 0) inside ThreeDScene.

Coordinate model
----------------
* **Sheet plane:** XY at ``z = 0`` — the learning tape.
* **Scroll:** camera ``frame_center`` pans in ``(x, y, 0)``.
* **Zoom (sheet view):** ``ThreeDCamera.set_zoom`` (``zoom_tracker``) — frame crop alone barely magnifies in 3D projection.
* **Tilt view:** optional perspective tilt for 3D surfaces; not toggled on every text block.
* **Inspect view:** orbit around a volumetric solid after optional lift off the tape.

We stay on ``ThreeDScene`` but default to **sheet view**, not a separate fake-2D stack.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DEGREES,
    Dot,
    ThreeDCamera,
    ValueTracker,
    smooth,
)
from manim.utils.rate_functions import RateFunction

from typing import Literal, Optional, Union, TYPE_CHECKING

from .coords import frame_center_for_inspect, frame_center_for_scroll, WorldTransform, Vector3, SHEET_PLANE_Z
from .inspect_path import CameraPose

if TYPE_CHECKING:
    from .dsl import ObservationTarget, TapeScroll, WorldPoint, ObjectAnchor, TapeObject

# For runtime in observe_target (avoid full circular at module load)
from .dsl import WorldPoint, TapeScroll, TapeObject, ObjectAnchor

ViewMode = Literal["sheet", "tilt", "inspect"]

# Sheet view: orthographic, looking at the z=0 plane (theta=-90, phi=0).
SHEET_PHI_DEG = 0.0
SHEET_THETA_DEG = -90.0


class CameraController:
    """Pan, zoom, and optional tilt over the XY sheet at z = 0."""

    def __init__(
        self,
        scene,
        frame_width: float = 9.0,
        frame_height: float = 16.0,
        existing_camera: ThreeDCamera | None = None,
    ):
        self.scene = scene

        if existing_camera is not None:
            self.camera = existing_camera
        else:
            self.camera = ThreeDCamera(
                frame_width=frame_width,
                frame_height=frame_height,
            )

        self._base_frame_width = float(frame_width)
        self._base_frame_height = float(frame_height)

        self._view_mode: ViewMode = "sheet"
        self._apply_sheet_camera_settings()

        self._x = ValueTracker(0.0)
        self._y = ValueTracker(0.0)
        self._inspect_x = ValueTracker(0.0)
        self._inspect_y = ValueTracker(0.0)
        self._inspect_z = ValueTracker(0.0)
        self._phi = ValueTracker(SHEET_PHI_DEG)
        self._theta = ValueTracker(SHEET_THETA_DEG)
        self._zoom = ValueTracker(1.0)

        self._dummy = Dot(radius=0.0001, color="#000000").set_opacity(0)
        scene.add(self._dummy)
        self._dummy.add_updater(self._sync_camera)
        self._sync_camera(self._dummy, 0)

    def _apply_sheet_camera_settings(self) -> None:
        self.camera.use_orthographic_projection = True
        self.camera.set_focal_distance(10.0)
        self.camera.set_phi(SHEET_PHI_DEG * DEGREES)
        self.camera.set_theta(SHEET_THETA_DEG * DEGREES)
        self.camera.set_zoom(1.0)
        self.camera.frame_center = np.array(frame_center_for_scroll(0.0, 0.0))

    def _sync_camera(self, dummy, dt: float) -> None:
        x = self._x.get_value()
        y = self._y.get_value()
        zoom = max(self._zoom.get_value(), 0.05)

        if self._view_mode == "inspect":
            ix = self._inspect_x.get_value()
            iy = self._inspect_y.get_value()
            iz = self._inspect_z.get_value()
            self.camera.frame_center = np.array(frame_center_for_inspect(ix, iy, iz))
            self.camera.use_orthographic_projection = False
        else:
            self.camera.frame_center = np.array(frame_center_for_scroll(x, y))
            self.camera.use_orthographic_projection = self._view_mode == "sheet"

        self.camera.set_phi(self._phi.get_value() * DEGREES)
        self.camera.set_theta(self._theta.get_value() * DEGREES)

        self.camera.frame_width = self._base_frame_width
        self.camera.frame_height = self._base_frame_height
        self.camera.set_zoom(zoom)

        if self._view_mode == "tilt":
            self.camera.use_orthographic_projection = False

    @property
    def view_mode(self) -> ViewMode:
        return self._view_mode

    @property
    def is_tilted(self) -> bool:
        return self._view_mode in ("tilt", "inspect")

    @property
    def is_inspecting(self) -> bool:
        return self._view_mode == "inspect"

    @property
    def current_x(self) -> float:
        return self._x.get_value()

    @property
    def current_y(self) -> float:
        return self._y.get_value()

    @property
    def current_zoom(self) -> float:
        return self._zoom.get_value()

    def pan_to(
        self,
        target_y: float,
        run_time: float = 2.0,
        rate_func: RateFunction = smooth,
    ) -> None:
        """Scroll the viewport along the sheet (Y axis)."""
        self.scene.play(
            self._y.animate(rate_func=rate_func, run_time=run_time).set_value(target_y),
            run_time=run_time,
        )

    def return_to_sheet(
        self,
        run_time: float = 1.2,
        rate_func: RateFunction = smooth,
    ) -> None:
        """Restore orthographic sheet view (after tilt or volumetric inspect)."""
        self._view_mode = "sheet"
        self.scene.play(
            self._phi.animate(rate_func=rate_func, run_time=run_time).set_value(SHEET_PHI_DEG),
            self._theta.animate(rate_func=rate_func, run_time=run_time).set_value(SHEET_THETA_DEG),
            run_time=run_time,
        )

    def read_pose(self) -> CameraPose:
        return CameraPose(
            target_x=self._inspect_x.get_value(),
            target_y=self._inspect_y.get_value(),
            target_z=self._inspect_z.get_value(),
            phi=self._phi.get_value(),
            theta=self._theta.get_value(),
            zoom=max(self._zoom.get_value(), 0.05),
        )

    def pose_anims(
        self,
        pose: CameraPose,
        run_time: float,
        rate_func: RateFunction = smooth,
    ):
        """Animate to an inspect ``CameraPose`` (scroll + look-at + angles)."""
        self._view_mode = "inspect"
        self.camera.use_orthographic_projection = False
        return [
            self._x.animate(rate_func=rate_func, run_time=run_time).set_value(pose.target_x),
            self._y.animate(rate_func=rate_func, run_time=run_time).set_value(pose.target_y),
            self._inspect_x.animate(rate_func=rate_func, run_time=run_time).set_value(pose.target_x),
            self._inspect_y.animate(rate_func=rate_func, run_time=run_time).set_value(pose.target_y),
            self._inspect_z.animate(rate_func=rate_func, run_time=run_time).set_value(pose.target_z),
            self._phi.animate(rate_func=rate_func, run_time=run_time).set_value(pose.phi),
            self._theta.animate(rate_func=rate_func, run_time=run_time).set_value(pose.theta),
            self._zoom.animate(rate_func=rate_func, run_time=run_time).set_value(pose.zoom),
        ]

    def inspect_anims(
        self,
        target_x: float,
        target_y: float,
        target_z: float,
        phi: float,
        theta: float,
        run_time: float,
        rate_func: RateFunction = smooth,
    ):
        """Legacy single-pose inspect (prefer ``pose_anims``)."""
        return self.pose_anims(
            CameraPose(target_x, target_y, target_z, phi, theta, 1.0),
            run_time,
            rate_func,
        )

    def orbit_anims(
        self,
        degrees: float,
        run_time: float,
        rate_func: RateFunction = smooth,
    ):
        """Legacy theta spin (prefer keyframe ``preset='orbit'``)."""
        target_theta = self._theta.get_value() + float(degrees)
        return [
            self._theta.animate(rate_func=rate_func, run_time=run_time).set_value(target_theta),
        ]

    def tilt_for_3d(
        self,
        phi: float = 45.0,
        theta: float = -90.0,
        run_time: float = 1.6,
        rate_func: RateFunction = smooth,
    ) -> None:
        """Optional perspective tilt to view a 3D surface on the sheet."""
        self._view_mode = "tilt"
        self.camera.use_orthographic_projection = False
        self.scene.play(
            self._phi.animate(rate_func=rate_func, run_time=run_time).set_value(phi),
            self._theta.animate(rate_func=rate_func, run_time=run_time).set_value(theta),
            run_time=run_time,
        )

    # Legacy names — same behavior, kept for older call sites.
    def transition_to_2d(self, run_time: float = 1.2, rate_func: RateFunction = smooth) -> None:
        self.return_to_sheet(run_time=run_time, rate_func=rate_func)

    def transition_to_3d(
        self,
        phi: float = 45.0,
        theta: float = -90.0,
        run_time: float = 1.6,
        rate_func: RateFunction = smooth,
    ) -> None:
        self.tilt_for_3d(phi=phi, theta=theta, run_time=run_time, rate_func=rate_func)

    def set_zoom(self, zoom: float, run_time: float = 1.0) -> None:
        self.scene.play(
            self._zoom.animate(run_time=run_time).set_value(zoom),
            run_time=run_time,
        )

    def focus_anims(
        self,
        target_x: float,
        target_y: float,
        zoom: float,
        run_time: float,
        rate_func: RateFunction = smooth,
    ):
        """Pan on the sheet + zoom (clamped to viewport-safe max by FocusEngine)."""
        return [
            self._x.animate(rate_func=rate_func, run_time=run_time).set_value(target_x),
            self._y.animate(rate_func=rate_func, run_time=run_time).set_value(target_y),
            self._zoom.animate(rate_func=rate_func, run_time=run_time).set_value(zoom),
        ]

    def reset_zoom_anim(
        self,
        run_time: float,
        rate_func: RateFunction = smooth,
        *,
        reset_x: bool = True,
    ):
        anims = [self._zoom.animate(rate_func=rate_func, run_time=run_time).set_value(1.0)]
        if reset_x:
            anims.append(self._x.animate(rate_func=rate_func, run_time=run_time).set_value(0.0))
        return anims

    def focus_at(
        self,
        target_y: float,
        zoom: float = 2.2,
        run_time: float = 1.4,
        rate_func: RateFunction = smooth,
        target_x: float = 0.0,
    ) -> None:
        self.scene.play(
            *self.focus_anims(target_x, target_y, zoom, run_time, rate_func),
            run_time=run_time,
        )

    def reset_frame_zoom(
        self,
        run_time: float = 0.9,
        rate_func: RateFunction = smooth,
    ) -> None:
        self.scene.play(
            self._zoom.animate(rate_func=rate_func, run_time=run_time).set_value(1.0),
            run_time=run_time,
        )

    def zoom_out(
        self,
        run_time: float = 1.0,
        rate_func: RateFunction = smooth,
        *,
        reset_x: bool = True,
    ) -> None:
        anims = [self._zoom.animate(rate_func=rate_func, run_time=run_time).set_value(1.0)]
        if reset_x:
            anims.append(self._x.animate(rate_func=rate_func, run_time=run_time).set_value(0.0))
        self.scene.play(*anims, run_time=run_time)

    def reset(self) -> None:
        self._x.set_value(0.0)
        self._y.set_value(0.0)
        self._phi.set_value(SHEET_PHI_DEG)
        self._theta.set_value(SHEET_THETA_DEG)
        self._zoom.set_value(1.0)
        self._view_mode = "sheet"
        self._apply_sheet_camera_settings()

    # === Phase 3 additions: generalized 3D observation (per world model docs) ===
    def observe_target(
        self,
        target: Union["ObservationTarget", dict],
        run_time: float = 2.0,
        rate_func: RateFunction = smooth,
        tape: Optional["TapeObject"] = None,
    ) -> None:
        """Observe a target (world point, object, or tape scroll).

        For TapeScroll targets: reuse local sheet pan_to + reveal logic in the
        tape's *local* coordinate system, while the outer camera frame is offset
        by the tape's world_transform (so tilted/moved tapes work correctly).

        This replaces pure sheet-centric panning with object-aware observation.
        """
        if isinstance(target, dict):
            kind = target.get("kind", "world_point")
            if kind == "tape_scroll":
                target = type("T", (), {
                    "local_y": float(target.get("local_y", 0)),
                    "framing_mode": target.get("framing_mode", "sheet")
                })()
            else:
                target = WorldPoint(position=tuple(target.get("position", (0., 0., 0.))))

        if hasattr(target, "local_y"):  # looks like TapeScroll
            local_y = float(getattr(target, "local_y", 0.0))
            if tape is not None and getattr(tape, "world_transform", None):
                tw = tape.world_transform
                # outer camera sees tape's world position + local scroll on its plane
                # for simplicity in phase 3: adjust the y tracker with tape offset
                effective_y = local_y + getattr(tw.position, "y", 0)
                # TODO in later: apply full rotation of tape to camera
                self.pan_to(effective_y, run_time=run_time, rate_func=rate_func)
            else:
                self.pan_to(local_y, run_time=run_time, rate_func=rate_func)
        else:
            # world point or anchor - basic 3D support
            if hasattr(target, "position"):
                pos = target.position
            elif isinstance(target, ObjectAnchor):
                # Phase 4: resolve anchor using placed or tape
                # simplistic: use 0 for now, full would lookup
                pos = (0., 0., 0.)
            else:
                pos = (0., 0., 0.)
            x = float(pos[0])
            y = float(pos[1])
            z = float(pos[2]) if len(pos) > 2 else 0.0
            self._x.set_value(x)
            self._y.set_value(y)
            if abs(z) > 1e-6:
                self._inspect_z.set_value(z)
                self._view_mode = "inspect"
            self.camera.frame_center = np.array([x, y, z or SHEET_PLANE_Z])


