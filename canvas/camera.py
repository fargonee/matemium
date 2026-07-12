"""Camera controller supporting both legacy tape and the unified 3D world model.

Coordinate model
----------------
* Objects (including TapeObject) live in world space via WorldTransform.
* Default observation for any target (including TapeObjects): cinematic 3D.
* TapeScroll target: activates tape-scroll-mode using the tape's internal local coords + full world transform.
* Legacy sheet behavior fully preserved for default (identity) root tape.
"""

from __future__ import annotations

import numpy as np
from manim import (
    Animation,
    DEGREES,
    Dot,
    ThreeDCamera,
    ValueTracker,
    smooth,
)
from manim.utils.rate_functions import RateFunction

from typing import Literal, Optional, Union, TYPE_CHECKING

from .coords import (
    frame_center_for_inspect,
    frame_center_for_scroll,
    WorldTransform,
    Vector3,
    SHEET_PLANE_Z,
    local_to_world_point,
    get_rotation_matrix,
)
from .inspect_path import CameraPose

if TYPE_CHECKING:
    from .dsl import ObservationTarget, WorldPoint, ObjectAnchor, TapeObject

# For runtime in observe_target (avoid full circular at module load)
from .dsl import WorldPoint, TapeObject, ObjectAnchor

ViewMode = Literal["sheet", "tilt", "inspect"]

# Sheet view: orthographic, looking at the z=0 plane (theta=-90, phi=0).
SHEET_PHI_DEG = 0.0
SHEET_THETA_DEG = -90.0

import numpy as np  # ensure

def _rot_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def _rot_x(b):
    c, s = np.cos(b), np.sin(b)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

def _camera_rotation_from_angles(phi_deg: float, theta_deg: float, gamma_deg: float):
    alpha = np.deg2rad(-theta_deg - 90)
    beta = np.deg2rad(-phi_deg)
    gamma = np.deg2rad(gamma_deg)
    # Match Manim ThreeDCamera.generate_rotation_matrix order:
    # rotz(gamma) @ rotx(-phi) @ rotz(-theta-90)
    return _rot_z(gamma) @ _rot_x(beta) @ _rot_z(alpha)

def get_tape_straight_above_angles(wt: "WorldTransform") -> tuple[float, float, float]:
    import numpy as np
    if wt is None: return 0.0, -90.0, 0.0
    R_tape = get_rotation_matrix(wt)
    phi, theta, gamma = mat_to_manim_euler(R_tape.T)
    return np.degrees(phi), np.degrees(theta), np.degrees(gamma)

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
        self._gamma = ValueTracker(0.0)
        self._zoom = ValueTracker(1.0)

        # Default horizontal center for the tape view in tape-scroll mode.
        # Content layout places centered items at local x=0, so the sheet "center" is 0.
        # Per-element focus (and flex groups) drive exact x from each elem.canvas_position[0].
        self.tape_center_x = 0.0

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
        else:
            self.camera.frame_center = np.array(frame_center_for_scroll(x, y))

        if self._view_mode == "inspect":
            # Preserve ortho=True for TAPE_SCROLL (straight-above tape view uses inspect trackers + ortho);
            # normal 3D observe sets perspective (False).
            obs_mode = getattr(self.scene, "_observation_mode", None)
            if str(obs_mode).endswith("TAPE_SCROLL") or getattr(obs_mode, "name", "") == "TAPE_SCROLL":
                self.camera.use_orthographic_projection = True
            else:
                self.camera.use_orthographic_projection = False
        else:
            self.camera.use_orthographic_projection = self._view_mode == "sheet"

        self.camera.set_phi(self._phi.get_value() * DEGREES)
        self.camera.set_theta(self._theta.get_value() * DEGREES)
        self.camera.set_gamma(self._gamma.get_value() * DEGREES)

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
        self._gamma.set_value(0.0)
        self._zoom.set_value(1.0)
        self._view_mode = "sheet"
        self._apply_sheet_camera_settings()

    # === Phase 3 additions: generalized 3D observation (per clarified model) ===
    # Default for any target (WorldPoint, ObjectAnchor on tape or other) is normal cinematic 3D.
    # Only explicit TapeScroll activates tape-scroll-mode (internal tape logic + local measurements).

    def _compute_tape_scroll_world_pos(self, tape: "TapeObject", local_y: float) -> tuple[float, float, float]:
        """Compute the world-space point on the tape corresponding to local_y.
        Uses tape_center_x (0 by default) + per-reveal focus using each element's
        canvas_position[0] (which is 0 for centered content) to keep camera centered.
        """
        if not tape or not getattr(tape, "world_transform", None):
            return (0.0, float(local_y), 0.0)
        local_x = self.tape_center_x
        local_point = (local_x, float(local_y), 0.0)
        return local_to_world_point(local_point, tape.world_transform)

    def observe_target(
        self,
        target: Union["ObservationTarget", dict],
        run_time: float = 2.0,
        rate_func: RateFunction = smooth,
        tape: Optional["TapeObject"] = None,
        target_transform: Optional["WorldTransform"] = None,
        target_pos_world: Optional[tuple[float, float, float]] = None,
    ) -> None:
        """Observe a target using the clarified 3D world model.

        - Normal 3D observation (WorldPoint, ObjectAnchor on anything including tapes):
          Cinematic 3D look/follow using world coordinates. No internal tape sheet logic.
        - TapeScroll: explicitly activates tape-scroll-mode.
          Uses tape's *local* measurement at local_y, transforms to world via the tape's
          full world_transform (pos+rot+scale), and activates scoped internal tape
          behaviors (the caller in scene decides when to drive reveal/focus from it).

        Legacy CameraMove on default tape maps to tape-scroll for exact old behavior.
        """
        # Normalize dict targets from serialization
        if isinstance(target, dict):
            kind = target.get("kind", "world_point")
            if kind == "tape_scroll":
                target = type("T", (), {
                    "local_y": float(target.get("local_y", 0)),
                    "framing_mode": target.get("framing_mode", "sheet")
                })()
            else:
                target = WorldPoint(position=tuple(target.get("position", (0., 0., 0.))))

        is_tape_scroll = hasattr(target, "local_y")

        if is_tape_scroll:
            # === TAPE-SCROLL-MODE (only explicit path that activates internal tape mechanisms) ===
            local_y = float(getattr(target, "local_y", 0.0))
            world_pos = self._compute_tape_scroll_world_pos(tape, local_y)

            # For identity/default tape (no rotation/offset), fall back to exact old behavior
            tw = getattr(tape, "world_transform", None) if tape else None
            is_default_tape = (
                tw is None or
                (abs(float(tw.position.x)) < 1e-9 and abs(float(tw.position.y)) < 1e-9 and abs(float(tw.position.z)) < 1e-9 and
                 abs(float(tw.rotation.x)) < 1e-9 and abs(float(tw.rotation.y)) < 1e-9 and abs(float(tw.rotation.z)) < 1e-9 and
                 abs(float(tw.scale) - 1.0) < 1e-9)
            )

            if is_default_tape:
                # For default (identity) tape: horizontal center is 0 (matches layout's
                # align=center positions at x=0). Per-element _focus will fine-tune using
                # each elem's actual canvas_position[0]. scroll_tape just activates + y.
                target_x = self.tape_center_x  # 0.0 by default

                self._x.set_value(target_x)

                x, y, z = world_pos
                self.scene.play(
                    self._inspect_x.animate(rate_func=rate_func, run_time=run_time).set_value(x),
                    self._inspect_y.animate(rate_func=rate_func, run_time=run_time).set_value(y),
                    self._inspect_z.animate(rate_func=rate_func, run_time=run_time).set_value(z),
                    self._x.animate(rate_func=rate_func, run_time=run_time).set_value(target_x),
                    self._y.animate(rate_func=rate_func, run_time=run_time).set_value(local_y),
                    run_time=run_time,
                )
                self.camera.frame_center = np.array([x, y, z])
            else:
                # Rotated/positioned tape in scroll mode: lock camera to exact tape orientation
                # so it looks straight from above (face-on to the tape plane in its local coords).
                # This fixes the 3D world <-> tape internal coord transition. Content appears
                # "flat" as in classic sheet, while positioned in world via the transform.
                x, y, z = world_pos
                self._view_mode = "inspect"
                self.camera.use_orthographic_projection = True

                phi, theta, gamma = self._phi.get_value(), self._theta.get_value(), self._gamma.get_value()
                if tape and getattr(tape, "world_transform", None):
                    phi, theta, gamma = get_tape_straight_above_angles(tape.world_transform)
                    phi = _closest_angle(self._phi.get_value(), phi)
                    theta = _closest_angle(self._theta.get_value(), theta)
                    gamma = _closest_angle(self._gamma.get_value(), gamma)

                local_x = self.tape_center_x  # 0 for content center; focus drives per-elem x

                # Animate the look point in world; the phi/theta/gamma are set to the
                # values that make the camera orientation equivalent to "straight sheet view"
                # in the tape's local coordinate system (via the math transform of the tape R).
                self.scene.play(
                    self._inspect_x.animate(rate_func=rate_func, run_time=run_time).set_value(x),
                    self._inspect_y.animate(rate_func=rate_func, run_time=run_time).set_value(y),
                    self._inspect_z.animate(rate_func=rate_func, run_time=run_time).set_value(z),
                    self._x.animate(rate_func=rate_func, run_time=run_time).set_value(local_x),
                    self._y.animate(rate_func=rate_func, run_time=run_time).set_value(local_y),  # use *local* y for internal tape scroll tracking
                    self._phi.animate(rate_func=rate_func, run_time=run_time).set_value(phi),
                    self._theta.animate(rate_func=rate_func, run_time=run_time).set_value(theta),
                    self._gamma.animate(rate_func=rate_func, run_time=run_time).set_value(gamma),
                    run_time=run_time,
                )
                self.camera.frame_center = np.array([x, y, z])

            # Note: Actual internal reveal/focus driven by local_y is handled by caller (scene)
            # when it detects a TapeScroll keyframe. We just positioned the camera.

        else:
            # === NORMAL 3D OBSERVATION (default for WorldPoint + ObjectAnchor on tapes or free 3D objects) ===
            # Treat the tape (if targeted) exactly like any other 3D object. No internal tape logic.
            is_face_on = False
            if target_pos_world is not None:
                pos = target_pos_world
                if isinstance(target, ObjectAnchor) and getattr(target, "framing", "cinematic") == "face_on":
                    is_face_on = True
            elif hasattr(target, "position"):
                pos = target.position
            elif isinstance(target, ObjectAnchor):
                # Phase 1 basic resolution: if targeting the passed tape, use its anchor + world transform
                if tape and getattr(target, "object_id", None) in (getattr(tape, "id", None), "root_tape"):
                    try:
                        local_anchor = tape.get_anchor(getattr(target, "anchor", "center"))
                        # For normal 3D obs of tape, treat anchor as local point on tape plane
                        pos = local_to_world_point(
                            (local_anchor.x, local_anchor.y, local_anchor.z),
                            tape.world_transform
                        )
                        if target_transform is None:
                            target_transform = tape.world_transform
                    except Exception:
                        pos = (0., 0., 0.)
                else:
                    # Generic or unknown object anchor: center at origin for now (full registry resolution later)
                    pos = (0., 0., 0.)
                if getattr(target, "framing", "cinematic") == "face_on":
                    is_face_on = True
            else:
                pos = (0., 0., 0.)

            x = float(pos[0])
            y = float(pos[1])
            z = float(pos[2]) if len(pos) > 2 else 0.0

            # Animate into inspect/3D view
            self._view_mode = "inspect"
            
            if is_face_on and target_transform:
                self.camera.use_orthographic_projection = True
                phi, theta, gamma = get_tape_straight_above_angles(target_transform)
                phi = _closest_angle(self._phi.get_value(), phi)
                theta = _closest_angle(self._theta.get_value(), theta)
                gamma = _closest_angle(self._gamma.get_value(), gamma)
                self.scene.play(
                    self._x.animate(rate_func=rate_func, run_time=run_time).set_value(x),
                    self._y.animate(rate_func=rate_func, run_time=run_time).set_value(y),
                    self._inspect_x.animate(rate_func=rate_func, run_time=run_time).set_value(x),
                    self._inspect_y.animate(rate_func=rate_func, run_time=run_time).set_value(y),
                    self._inspect_z.animate(rate_func=rate_func, run_time=run_time).set_value(z),
                    self._phi.animate(rate_func=rate_func, run_time=run_time).set_value(phi),
                    self._theta.animate(rate_func=rate_func, run_time=run_time).set_value(theta),
                    self._gamma.animate(rate_func=rate_func, run_time=run_time).set_value(gamma),
                    run_time=run_time,
                )
            else:
                self.camera.use_orthographic_projection = False
                self.scene.play(
                    self._x.animate(rate_func=rate_func, run_time=run_time).set_value(x),
                    self._y.animate(rate_func=rate_func, run_time=run_time).set_value(y),
                    self._inspect_x.animate(rate_func=rate_func, run_time=run_time).set_value(x),
                    self._inspect_y.animate(rate_func=rate_func, run_time=run_time).set_value(y),
                    self._inspect_z.animate(rate_func=rate_func, run_time=run_time).set_value(z),
                    self._phi.animate(rate_func=rate_func, run_time=run_time).set_value(60),
                    self._theta.animate(rate_func=rate_func, run_time=run_time).set_value(-45),
                    run_time=run_time,
                )
            self.camera.frame_center = np.array([x, y, z or SHEET_PLANE_Z])

