"""CanvasScene — the heart of Matemium.

Consumes a SheetDSL and renders an infinite vertically scrollable sheet
by driving camera moves and element entry / transform animations.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import Iterator, List, Literal, Tuple, Union

from manim import (
    DEGREES,
    DOWN,
    FadeIn,
    MathTex,
    Mobject,
    OUT,
    RIGHT,
    Scene,
    Text,
    ThreeDScene,
    UP,
    UR,
    VGroup,
    WHITE,
    Write,
    ValueTracker,
    tempconfig,
)
from manim.utils.rate_functions import linear, smooth

# For static export
try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore


from .animations import FLASH_AND_SCALE, get_entry_animation
from .camera import CameraController
from .dsl import (
    CameraFocus,
    CameraInspect,
    CameraMove,
    CameraKeyframe,  # Phase 3
    CanvasElement,
    CanvasSettings,
    ObjectAnchor,  # Phase 5
    ObservationMode,  # Phase 8
    PlotTrace,
    SheetDSL,
    SolidLift,
    SolidRotate,
    TimelineItem,
    TransformElement,
    TapeObject,
    TapeScroll,  # Phase 2
    WorldObject,
    WorldTransform,
)
from .solids import place_solid_on_tape
from .coords import local_to_world_point, _rotation_matrix_from_euler_deg
from .camera import get_tape_straight_above_angles
from .focus import FocusEngine
from .inspect_engine import InspectEngine
from .rotation_engine import RotationEngine
from .solid_labels import apply_billboard_labels
from .plots import get_plot_part
from .measure import build_mobject, make_render_surface, _OBJECT_KINDS
from .registry import MobjectRegistry


class CanvasScene(ThreeDScene):
    """Main driver scene for Matemium's infinite canvas.

    Core design: **lazy element display**.
    Mobjects are only built and added to the scene when their
    CanvasElement entry is reached in the timeline. This prevents
    the "pre-written PDF" feel and enables proper "content appears
    as you scroll/reach it" behavior.

    Usage:
        # Recommended (no JSON):
        # builder = CanvasBuilder(title="...")
        # dsl = builder.build()
        # Advanced only:
        # dsl = SheetDSL.from_file("path/to/your.raw.json")  # raw/legacy only; prefer builder
        scene = CanvasScene(dsl)
        # then manim ... CanvasScene
    """

    def __init__(self, dsl: SheetDSL, **kwargs):
        super().__init__(**kwargs)
        self.dsl = dsl
        self.settings: CanvasSettings = dsl.canvas_settings
        self.registry = MobjectRegistry(viewport_margin=3.0)
        self.camera_ctl: CameraController | None = None
        # Phase 3
        self.root_tape = getattr(dsl, "root_tape", None)
        # Phase 8
        self._world_objects: dict[str, Mobject] = {}
        # Phase 2/8 (clarified model): explicit observation mode
        self._observation_mode: ObservationMode = ObservationMode.NORMAL_3D
        self._active_scroll_tape: Optional["TapeObject"] = None
        self._tape_containers: dict[str, Mobject] = {}  # tape_id -> container VGroup for transformed tape content
        self._tape_content_ids: set[str] = set()
        self._element_tape_map: dict[str, "TapeObject"] = {}  # elem_id -> owning tape (for correct WT even if revealed out of order)
        # Dimming for tape-scroll focus
        self._dimmed_opacities: dict[str, float] = {}
        self._current_dim_tape_id: Optional[str] = None
        self._current_dim_opacity: float = 0.15
        all_tapes = [self.root_tape] if self.root_tape else []
        all_tapes += getattr(self.dsl, 'additional_tapes', []) or []
        for t in all_tapes:
            if t and getattr(t, "local_elements", None):
                for el in t.local_elements:
                    if el and getattr(el, "id", None):
                        self._tape_content_ids.add(el.id)
                        self._element_tape_map[el.id] = t

        # Store specs for all revealed elements (needed for static export with pre-defined static states)
        self._element_specs: dict[str, CanvasElement] = {}

    def construct(self):
        # ThreeDScene (our parent) has already created self.camera (a ThreeDCamera).
        # We take control of the *existing* one instead of replacing the property.
        self.camera_ctl = CameraController(
            self,
            frame_width=self.settings.frame_width,
            frame_height=self.settings.frame_height,
            existing_camera=self.camera,   # critical: reuse the one provided by the scene
        )

        # Phase 2/8: build world object structure (transforms) early for 3D placement.
        # Content is kept lazy (revealed on timeline) to preserve narrative "writing".
        # Tape internal content lazy unless in tape-scroll-mode.
        # Default identity root tape keeps full legacy lazy path.
        has_root_objs = bool(getattr(self.dsl, 'root_objects', None))
        tape = getattr(self, 'root_tape', None)
        tape_non_default = False
        if tape:
            wt = tape.world_transform or WorldTransform()
            tape_non_default = (
                any(abs(float(c)) > 1e-9 for c in wt.position.as_tuple()) or
                any(abs(float(c)) > 1e-9 for c in wt.rotation.as_tuple()) or
                abs(float(wt.scale) - 1.0) > 1e-9
            )

        do_3d_prebuild = has_root_objs or tape_non_default
        if do_3d_prebuild:
            if has_root_objs:
                for wo in self.dsl.root_objects:
                    self._build_world_object(wo)
            # Phase 8: support containers for root + additional non-default tapes
            tapes_for_container = []
            if tape and tape_non_default:
                tapes_for_container.append(tape)
            for atape in getattr(self.dsl, 'additional_tapes', []) or []:
                if atape:
                    wt = atape.world_transform or WorldTransform()
                    at_non_default = (
                        any(abs(float(c)) > 1e-9 for c in wt.position.as_tuple()) or
                        any(abs(float(c)) > 1e-9 for c in wt.rotation.as_tuple()) or
                        abs(float(wt.scale) - 1.0) > 1e-9
                    )
                    if at_non_default:
                        tapes_for_container.append(atape)
            for t in tapes_for_container:
                self._build_tape_container(t)  # container only; children lazy on reveal

            # 3D camera for non-default world content.
            # For tape-scroll content we will override to ortho + straight-above in the seed + focus paths.
            self.camera_ctl._view_mode = "inspect"
            self.camera.use_orthographic_projection = False

            # Always prepare a sensible horizontal center for the root tape view.
            # Layout puts centered content at local x=0 (see _horizontal_center).
            # So the default "center" for tape scroll is 0 (not frame/2).
            if tape and self._tape_content_ids:
                self.camera_ctl.tape_center_x = 0.0

            # Seed the inspect trackers at the (first) posed tape so initial view is on the tape plane
            # rather than default sheet. Subsequent per-element focus will auto "scroll" to center new content.
            init_tape = tape if (tape and tape_non_default) else None
            if not init_tape and tapes_for_container:
                init_tape = tapes_for_container[0]
            if init_tape:
                wt = getattr(init_tape, "world_transform", None) or WorldTransform()
                p = wt.position
                px, py, pz = p.as_tuple() if hasattr(p, "as_tuple") else (getattr(p, "x", 0), getattr(p, "y", 0), getattr(p, "z", 0))
                initial_local_x = self.camera_ctl.tape_center_x
                initial_w = local_to_world_point((initial_local_x, 0.0, 0.0), wt)
                self.camera_ctl._inspect_x.set_value(float(initial_w[0]))
                self.camera_ctl._inspect_y.set_value(float(initial_w[1]))
                self.camera_ctl._inspect_z.set_value(float(initial_w[2]))
                self.camera_ctl._x.set_value(self.camera_ctl.tape_center_x)
                self.camera_ctl._y.set_value(0.0)
                self.camera.frame_center = np.array(initial_w)
                self.camera.use_orthographic_projection = True
                if wt:
                    phi, theta, gamma = get_tape_straight_above_angles(wt)
                    self.camera_ctl._phi.set_value(phi)
                    self.camera_ctl._theta.set_value(theta)
                    self.camera_ctl._gamma.set_value(gamma)
                # Force an immediate sync so scene camera reflects the initial pose before first reveal
                try:
                    dummy = getattr(self.camera_ctl, "_dummy", None)
                    if dummy is not None:
                        self.camera_ctl._sync_camera(dummy, 0)
                except Exception:
                    pass

            # For posed tapes with content, start in TAPE_SCROLL so flex guards + behaviors treat initial
            # authoring reveals as tape context (automatic centering). Explicit observe_* later can switch out.
            if tape and tape_non_default:
                self._active_scroll_tape = tape
                self._observation_mode = ObservationMode.TAPE_SCROLL
        # else: default tape at identity -> full legacy lazy path (play counts, reveals preserved)

        # Default authoring for any tape content: start assuming tape-scroll context for automatic
        # per-element (and group) centering. This fulfills "no manual scroll_tape interleaving".
        # Explicit non-tape CameraKeyframes (observe_object etc) will override to NORMAL_3D as encountered.
        if not getattr(self, "_active_scroll_tape", None) and getattr(self, "_tape_content_ids", None):
            self._active_scroll_tape = self.root_tape
            self._observation_mode = ObservationMode.TAPE_SCROLL
            if self.camera_ctl:
                self.camera_ctl.tape_center_x = 0.0
                self.camera_ctl._x.set_value(0.0)
                # also seed the inspect trackers for initial tape view centering (in case no posed seed)
                # (we keep view_mode as "sheet" for default tape so _x/_y drive + ortho is preserved)
                try:
                    self.camera_ctl._inspect_x.set_value(0.0)
                    self.camera_ctl._inspect_y.set_value(0.0)
                    self.camera_ctl._inspect_z.set_value(0.0)
                    self.camera.frame_center = np.array([0.0, 0.0, 0.0])
                except Exception:
                    pass

        # For 3D model: objects pre-built with transforms.
        # Execute full timeline; element reveals will skip build if pre-added (only for the prebuilt ones)

        # IMPORTANT: No pre-instantiation of elements. (legacy sheet path)
        # Elements are LAZILY created and added only when their entry appears in the timeline.
        # This is a core feature of Matemium:
        #   - Content materializes ("is written") as the narrative/camera reaches it.
        #   - Not a pre-laid-out static sheet that the camera merely scrolls over (like a PDF viewer).
        #   - Better performance for long canvases (heavy 3D objects etc. created on demand).
        #   - The registry only holds elements that have been revealed so far.
        # The timeline explicitly controls the order and timing of reveals.

        # Execute the timeline in order (the "compiler")
        for kind, payload in self._iter_timeline_batches():
            if kind == "flex_group":
                self._handle_flex_group_reveal(payload)
            elif isinstance(payload, CameraMove):
                self._handle_camera_move(payload)
            elif isinstance(payload, CameraKeyframe):
                self._handle_camera_keyframe(payload)
            elif isinstance(payload, CanvasElement):
                self._handle_element_reveal(payload)
            elif isinstance(payload, TransformElement):
                self._handle_transform(payload)
            elif isinstance(payload, PlotTrace):
                self._handle_plot_trace(payload)
            elif isinstance(payload, SolidLift):
                self._handle_solid_lift(payload)
            elif isinstance(payload, SolidRotate):
                self._handle_solid_rotate(payload)
            elif isinstance(payload, CameraInspect):
                self._handle_camera_inspect(payload)
            elif isinstance(payload, CameraFocus):
                self._handle_camera_focus(payload)

        # Hold at the end so the last view is visible
        self.wait(1.5)

    # --------------------------- Timeline handlers ---------------------------

    def _iter_timeline_batches(
        self,
    ) -> Iterator[Tuple[str, Union[List[CanvasElement], TimelineItem]]]:
        """Group consecutive flex-row/column siblings into one reveal batch."""
        tl = self.dsl.timeline
        i = 0
        while i < len(tl):
            item = tl[i]
            if isinstance(item, CanvasElement) and item.flex_group:
                gid = item.flex_group
                group: List[CanvasElement] = [item]
                i += 1
                while (
                    i < len(tl)
                    and isinstance(tl[i], CanvasElement)
                    and tl[i].flex_group == gid
                ):
                    group.append(tl[i])
                    i += 1
                yield ("flex_group", group)
            else:
                yield ("single", item)
                i += 1

    def _focus_on_group(self, elements: List[CanvasElement]) -> None:
        """Pan once to the centroid of a flex group before combined reveal.
        Phase 2/8: support 3D centering for posed tapes in scroll mode.
        """
        if not self.camera_ctl or not elements:
            return
        # Auto for tape content (even without explicit prior TapeScroll keyframe).
        # This makes scrolling automatic during the main tape writing phase.
        if not any(e.id in getattr(self, "_tape_content_ids", set()) for e in elements):
            return

        ys = [float(e.canvas_position[1]) for e in elements]
        target_y = sum(ys) / len(ys)
        current_y = self.camera_ctl.current_y
        distance = abs(target_y - current_y)

        # Compute the visual center of the group as the center of the bounding box
        # of all items (min left to max right). This is more accurate than mean of
        # centers when items have different widths (e.g. the "multiply to / +6 ..." flex).
        def _group_visual_center_x(elems):
            if not elems:
                return 0.0
            lefts = []
            rights = []
            for e in elems:
                cx = float(e.canvas_position[0]) if getattr(e, 'canvas_position', None) else 0.0
                w = 0.0
                lay = getattr(e, 'layout', None)
                if lay and getattr(lay, 'width', None) is not None:
                    w = float(lay.width)
                if w <= 0:
                    w = 1.0
                lefts.append(cx - w / 2)
                rights.append(cx + w / 2)
            return (min(lefts) + max(rights)) / 2.0 if lefts else 0.0

        is_tape_group = any(e.id in getattr(self, "_tape_content_ids", set()) for e in elements)
        group_x = 0.0
        if is_tape_group:
            group_x = _group_visual_center_x(elements)
            self.camera_ctl._x.set_value(group_x)
            self.camera_ctl._inspect_x.set_value(group_x)
        if distance < 0.12:
            return
        run_time = min(2.0, max(0.45, 0.3 + distance * 0.11))

        # For posed tape, use 3D focus on first element's world pos
        first = elements[0]
        active_tape = getattr(self, "_active_scroll_tape", None) or getattr(self, "root_tape", None)
        is_posed = False
        if active_tape and getattr(active_tape, "world_transform", None):
            wt = active_tape.world_transform
            px, py, pz = (wt.position.as_tuple() if hasattr(wt.position, "as_tuple") else (getattr(wt.position, "x", 0), getattr(wt.position, "y", 0), getattr(wt.position, "z", 0)))
            rx, ry, rz = (wt.rotation.as_tuple() if hasattr(wt.rotation, "as_tuple") else (getattr(wt.rotation, "x", 0), getattr(wt.rotation, "y", 0), getattr(wt.rotation, "z", 0)))
            sc = float(getattr(wt, "scale", 1.0))
            is_posed = (abs(float(px)) > 1e-9 or abs(float(py)) > 1e-9 or abs(float(pz)) > 1e-9 or
                        abs(float(rx)) > 1e-9 or abs(float(ry)) > 1e-9 or abs(float(rz)) > 1e-9 or
                        abs(sc - 1.0) > 1e-9)

        if is_posed:
            wt = getattr(first, "world_transform", None)
            if wt and hasattr(wt, "position"):
                p = wt.position
                wpos = p.as_tuple() if hasattr(p, "as_tuple") else (float(getattr(p, "x", 0)), float(getattr(p, "y", 0)), float(getattr(p, "z", 0)))
                # For groups on posed tapes use the visual bounding center (like non-posed)
                group_local_x = _group_visual_center_x(elements)
                self.camera_ctl._view_mode = "inspect"
                self.camera.use_orthographic_projection = True
                if active_tape and getattr(active_tape, "world_transform", None):
                    phi, theta, gamma = get_tape_straight_above_angles(active_tape.world_transform)
                    self.camera_ctl._phi.set_value(phi)
                    self.camera_ctl._theta.set_value(theta)
                    self.camera_ctl._gamma.set_value(gamma)
                self.play(
                    self.camera_ctl._inspect_x.animate(rate_func=smooth, run_time=run_time).set_value(wpos[0]),
                    self.camera_ctl._inspect_y.animate(rate_func=smooth, run_time=run_time).set_value(wpos[1]),
                    self.camera_ctl._inspect_z.animate(rate_func=smooth, run_time=run_time).set_value(wpos[2] if len(wpos) > 2 else 0),
                    self.camera_ctl._x.animate(rate_func=smooth, run_time=run_time).set_value(group_local_x),
                    self.camera_ctl._y.animate(rate_func=smooth, run_time=run_time).set_value(target_y),
                    run_time=run_time,
                )
                self.camera.frame_center = np.array([wpos[0], wpos[1], wpos[2] if len(wpos)>2 else 0])
                return

        self.registry.pause_far_updaters(current_y, buffer=5.0)
        # Re-compute using visual center (in case not set early, or for safety)
        group_x = _group_visual_center_x(elements)
        self.camera_ctl._x.set_value(group_x)
        self.camera_ctl._inspect_x.set_value(group_x)
        self.camera_ctl._inspect_y.set_value(target_y)
        if getattr(self.camera_ctl, "_view_mode", "sheet") == "inspect":
            self.play(
                self.camera_ctl._inspect_x.animate(rate_func=smooth, run_time=run_time).set_value(group_x),
                self.camera_ctl._inspect_y.animate(rate_func=smooth, run_time=run_time).set_value(target_y),
                self.camera_ctl._x.animate(rate_func=smooth, run_time=run_time).set_value(group_x),
                self.camera_ctl._y.animate(rate_func=smooth, run_time=run_time).set_value(target_y),
                run_time=run_time,
            )
        else:
            self.camera_ctl.pan_to(target_y, run_time=run_time)
        self.registry.pause_far_updaters(target_y, buffer=3.5)

    def _handle_flex_group_reveal(
        self,
        elements: List[CanvasElement],
        play_animation: bool = True,
    ) -> None:
        """Reveal each flex item as its own element — one scroll, simultaneous entry.
        Phase 2: only do scroll focus and sheet camera logic when in tape-scroll-mode for tape content.
        """
        if not elements:
            return

        for elem in elements:
            self._element_specs[elem.id] = elem

        if not play_animation:
            for elem in elements:
                self._handle_element_reveal(elem, play_animation=False)
            return

        if any(e.id in getattr(self, "_tape_content_ids", set()) for e in elements):
            self._focus_on_group(elements)

        tilt_pitch = next(
            (
                e.pitch
                for e in elements
                if e.type in ("ThreeDGraph", "Surface") and e.pitch is not None
            ),
            None,
        )
        if self.camera_ctl:
            is_tape_ctx = any(e.id in getattr(self, "_tape_content_ids", set()) for e in elements)
            if is_tape_ctx:
                if tilt_pitch is not None:
                    self.camera_ctl.tilt_for_3d(phi=tilt_pitch, run_time=0.8)
                elif self.camera_ctl.is_tilted:
                    # Return to flat tape view after a 3D in a flex group
                    self.camera_ctl.return_to_sheet(run_time=0.6)
            else:
                if tilt_pitch is not None:
                    self.camera_ctl.tilt_for_3d(phi=tilt_pitch, run_time=0.8)
                elif self.camera_ctl.is_tilted:
                    self.camera_ctl.return_to_sheet(run_time=0.6)

        # Compute container for tape content groups so posed tape's world transform applies to children.
        # Use owning tape per-element when possible so that content of secondary/rotated tapes
        # gets the correct pose even in mixed timeline order.
        container = None
        active_for_flex = None
        has_tape_pose_flex = False
        if any(e.id in getattr(self, "_tape_content_ids", set()) for e in elements):
            # Pick the owning tape of the first tape-content elem in the group
            for e in elements:
                if e.id in self._element_tape_map:
                    active_for_flex = self._element_tape_map[e.id]
                    break
            if not active_for_flex:
                active_for_flex = getattr(self, "_active_scroll_tape", None) or getattr(self, "root_tape", None)
            if active_for_flex:
                container = self._tape_containers.get(getattr(active_for_flex, "id", None))
                has_tape_pose_flex = bool( getattr(active_for_flex, "world_transform", None) )
        else:
            active_for_flex = getattr(self, "_active_scroll_tape", None) or getattr(self, "root_tape", None)

        prepared: List[Tuple[CanvasElement, Mobject, bool]] = []
        for elem in elements:
            mob = self.registry.get(elem.id)
            first_time = mob is None
            if first_time:
                mob = self._build_mobject(elem)
                if mob is None:
                    continue
            if has_tape_pose_flex and active_for_flex:
                local_pt = tuple(elem.canvas_position[:3])
                wpos = local_to_world_point(local_pt, active_for_flex.world_transform)
                pos = np.array(wpos, dtype=float)
                mob.move_to(pos)
                # Orient to the tape plane (same as single element path)
                rx, ry, rz = active_for_flex.world_transform.rotation.as_tuple()
                if abs(rx) > 1e-9:
                    mob.rotate(rx * DEGREES, axis=RIGHT)
                if abs(ry) > 1e-9:
                    mob.rotate(ry * DEGREES, axis=UP)
                if abs(rz) > 1e-9:
                    mob.rotate(rz * DEGREES, axis=OUT)
                if abs(rx) > 1e-9 or abs(ry) > 1e-9 or abs(rz) > 1e-9:
                    R = _rotation_matrix_from_euler_deg(rx, ry, rz)
                    y_axis = R @ np.array([0., 1., 0.])
                    mob.rotate(180 * DEGREES, axis=y_axis)
            else:
                pos = np.array(elem.canvas_position, dtype=float)
                if elem.type == "Solid3D":
                    place_solid_on_tape(mob, tuple(pos), elem.content)
                    pos = mob.get_center()
                else:
                    mob.move_to(pos)
            self.registry.register(elem.id, mob, pos[1], tuple(pos))
            prepared.append((elem, mob, first_time))

        # Add first-time items to container (for transform inheritance on posed tapes) or scene.
        # Add before playing entry anim (matches _handle_element_reveal pattern).
        # For posed tape: use world pos (already set) + add direct to avoid double transform.
        for elem, mob, first_time in prepared:
            if first_time:
                if has_tape_pose_flex:
                    if mob not in getattr(self, "mobjects", []):
                        self.add(mob)
                elif container is not None:
                    container.add(mob)
                elif not (getattr(self, "_world_objects", None) and elem.id in getattr(self, "_world_objects", {})):
                    if mob not in getattr(self, "mobjects", []):
                        self.add(mob)

        anims = []
        run_time = 0.6
        for elem, mob, first_time in prepared:
            if not first_time:
                if mob not in getattr(self, "mobjects", []):
                    self.add(mob)
                continue
            if elem.entry_animation:
                anims.append(get_entry_animation(mob, elem.entry_animation))
                run_time = max(run_time, elem.entry_animation.run_time)
            else:
                anims.append(FadeIn(mob, run_time=0.6))

        if anims:
            self.play(*anims, run_time=run_time)

        for elem, mob, first_time in prepared:
            if first_time:
                self._setup_state_behavior(elem, mob)
                self._apply_billboard_labels(elem, mob)

    def _handle_camera_move(self, move: CameraMove):
        target_y = float(move.target_position[1])
        rate = self._get_rate_func(move.rate_func)

        # Legacy CameraMove treated as tape-scroll for compat (on root tape)
        self._observation_mode = ObservationMode.TAPE_SCROLL
        self._active_scroll_tape = self.root_tape
        if self.camera_ctl:
            self.camera_ctl.tape_center_x = 0.0
            self.camera_ctl._x.set_value(0.0)
            if self.root_tape and getattr(self.root_tape, "world_transform", None):
                try:
                    phi, theta, gamma = get_tape_straight_above_angles(self.root_tape.world_transform)
                    self.camera_ctl._phi.set_value(phi)
                    self.camera_ctl._theta.set_value(theta)
                    self.camera_ctl._gamma.set_value(gamma)
                    self.camera_ctl._view_mode = "inspect"
                    self.camera_ctl.camera.use_orthographic_projection = True
                except Exception:
                    pass

        # Pause far updaters before big camera travel
        if self.camera_ctl:
            self.registry.pause_far_updaters(self.camera_ctl.current_y, buffer=5.0)
            self.camera_ctl.pan_to(target_y, run_time=move.run_time, rate_func=rate)
            # After arrival, resume relevant updaters
            self.registry.pause_far_updaters(target_y, buffer=3.5)

    def _handle_camera_keyframe(self, kf: CameraKeyframe):
        """Phase 2/3: handle generalized CameraKeyframe / observation.
        Set mode flags for tape-scroll vs normal 3D.
        Only TapeScroll (or legacy) activates internal tape mechanisms.
        """
        target = kf.target

        # Restore dimming when leaving tape-scroll mode
        if self._observation_mode == ObservationMode.TAPE_SCROLL:
            self._restore_dimmed_objects()

        self._observation_mode = ObservationMode.NORMAL_3D
        self._active_scroll_tape = None
        if self.camera_ctl:
            # reset to default sheet orientation when leaving tape mode
            self.camera_ctl._phi.set_value(0.0)
            self.camera_ctl._theta.set_value(-90.0)
            self.camera_ctl._gamma.set_value(0.0)
            if hasattr(self.camera_ctl, "camera"):
                self.camera_ctl.camera.use_orthographic_projection = True

        if isinstance(target, TapeScroll):
            tid = getattr(target, "tape_id", None)
            if tid in (None, "root_tape") or (self.root_tape and tid == getattr(self.root_tape, "id", None)):
                self._observation_mode = ObservationMode.TAPE_SCROLL
                self._active_scroll_tape = self.root_tape
                if self.camera_ctl:
                    self.camera_ctl.tape_center_x = 0.0
                    self.camera_ctl._x.set_value(0.0)
            else:
                # Phase 8: support additional top-level tapes
                for at in getattr(self.dsl, 'additional_tapes', []) or []:
                    if at and at.id == tid:
                        self._observation_mode = ObservationMode.TAPE_SCROLL
                        self._active_scroll_tape = at
                        break
            # Apply dimming if requested on the TapeScroll target
            dim_others = getattr(target, 'dim_others', True)
            dim_op = getattr(target, 'dim_opacity', 0.15)
            if self._active_scroll_tape and dim_others:
                self._dim_non_active_for_tape(self._active_scroll_tape, dim_op)
        elif isinstance(target, dict) and target.get("kind") == "tape_scroll":
            tid = target.get("tape_id")
            if tid in (None, "root_tape") or (self.root_tape and tid == getattr(self.root_tape, "id", None)):
                self._observation_mode = ObservationMode.TAPE_SCROLL
                self._active_scroll_tape = self.root_tape
                if self.camera_ctl:
                    self.camera_ctl.tape_center_x = 0.0
                    self.camera_ctl._x.set_value(0.0)
            else:
                for at in getattr(self.dsl, 'additional_tapes', []) or []:
                    if at and at.id == tid:
                        self._observation_mode = ObservationMode.TAPE_SCROLL
                        self._active_scroll_tape = at
                        break
            dim_others = target.get("dim_others", True)
            dim_op = float(target.get("dim_opacity", 0.15))
            if self._active_scroll_tape and dim_others:
                self._dim_non_active_for_tape(self._active_scroll_tape, dim_op)
        # else: normal 3D observation (ObjectAnchor, WorldPoint) -- including on a TapeObject

        tape_for_observe = self._active_scroll_tape or self.root_tape

        # Set straight-above angles (math transform of tape R) so tape internal coords
        # are the natural source for the camera view in tape-scroll mode.
        if self._observation_mode == ObservationMode.TAPE_SCROLL and self.camera_ctl and tape_for_observe:
            wt = getattr(tape_for_observe, "world_transform", None)
            if wt:
                try:
                    phi, theta, gamma = get_tape_straight_above_angles(wt)
                    self.camera_ctl._phi.set_value(phi)
                    self.camera_ctl._theta.set_value(theta)
                    self.camera_ctl._gamma.set_value(gamma)
                    self.camera_ctl._view_mode = "inspect"
                    self.camera_ctl.camera.use_orthographic_projection = True
                except Exception:
                    pass

        # Phase 5: wire observe= hook from register_object_kind for custom kinds
        target_transform = None
        target_pos_world = None
        if isinstance(target, ObjectAnchor):
            obj_id = target.object_id
            # Resolve the element/kind for this anchor
            elem = self._element_specs.get(obj_id)
            if elem:
                target_transform = getattr(elem, 'world_transform', None)
                mob = self.registry.get(obj_id)
                if mob:
                    center = mob.get_center()
                    target_pos_world = (float(center[0]), float(center[1]), float(center[2]))
                else:
                    local_pt = tuple(getattr(elem, 'canvas_position', (0.0, 0.0, 0.0))[:3])
                    if target_transform:
                        target_pos_world = local_to_world_point(local_pt, target_transform)
                    else:
                        target_pos_world = local_pt
                        
            kind = getattr(elem, 'type', None) if elem else None
            if kind and kind in _OBJECT_KINDS:
                obs_fn = _OBJECT_KINDS[kind].get("observe")
                if obs_fn:
                    try:
                        obs_fn(
                            target,
                            self.camera_ctl,
                            run_time=getattr(kf, "duration", getattr(kf, "run_time", 2.0)),
                            rate_func=self._get_rate_func(getattr(kf, "rate_func", "smooth")),
                            tape=tape_for_observe,
                        )
                        return  # hook handled the observation
                    except Exception:
                        pass  # fall through to default

        if self.camera_ctl:
            self.camera_ctl.observe_target(
                target,
                run_time=getattr(kf, "duration", getattr(kf, "run_time", 2.0)),
                rate_func=self._get_rate_func(getattr(kf, "rate_func", "smooth")),
                tape=tape_for_observe,
                target_transform=target_transform,
                target_pos_world=target_pos_world,
            )

    # ------------------- Tape-scroll dimming helpers -------------------

    def _get_active_ids(self, tape: Optional["TapeObject"]) -> set[str]:
        if not tape:
            return set()
        ids: set[str] = set()
        for el in getattr(tape, "local_elements", []) or []:
            if el and getattr(el, "id", None):
                ids.add(el.id)
        if getattr(tape, "id", None) and tape.id != "root_tape":
            ids.add(tape.id)
        return ids

    def _dim_non_active_for_tape(self, tape: "TapeObject", dim_opacity: float = 0.15):
        """Dim all revealed mobjects that do not belong to this tape (and its content).
        Called when entering TAPE_SCROLL for a specific tape (if dim_others=True).
        """
        if not tape or not self.registry:
            return
        active = self._get_active_ids(tape)
        self._current_dim_tape_id = getattr(tape, "id", None)
        self._current_dim_opacity = dim_opacity

        for uid, entry in list(self.registry._store.items()):
            if uid in active:
                continue
            mob = entry.mobject
            if mob is None:
                continue
            try:
                curr = float(getattr(mob, "get_opacity", lambda: 1.0)())
            except Exception:
                curr = 1.0
            if uid not in self._dimmed_opacities:
                self._dimmed_opacities[uid] = curr
            try:
                mob.set_opacity(dim_opacity)
            except Exception:
                pass

        # Dim free world objects too (other 3D solids, etc.)
        for uid, mob in list(getattr(self, "_world_objects", {}).items()):
            if uid in active or uid in self._dimmed_opacities:
                continue
            try:
                curr = float(getattr(mob, "get_opacity", lambda: 1.0)())
            except Exception:
                curr = 1.0
            self._dimmed_opacities[uid] = curr
            try:
                mob.set_opacity(dim_opacity)
            except Exception:
                pass

    def _restore_dimmed_objects(self):
        """Restore opacities when leaving a tape-scroll focus that dimmed others."""
        for uid, orig in list(self._dimmed_opacities.items()):
            mob = self.registry.get(uid) if self.registry else None
            if mob is None:
                mob = getattr(self, "_world_objects", {}).get(uid)
            if mob is not None:
                try:
                    mob.set_opacity(orig)
                except Exception:
                    pass
        self._dimmed_opacities.clear()
        self._current_dim_tape_id = None
        self._current_dim_opacity = 0.15

    def _should_auto_focus(self, elem: CanvasElement) -> bool:
        """Overlays (e.g. grid marks) stay on an already-framed board — no re-pan."""
        return elem.auto_focus and elem.type != "GridMark"

    def _focus_on_element(self, elem: CanvasElement) -> None:
        """Pan the viewport so the element reveals at the center of the frame.
        Phase 2/8: In tape-scroll-mode for tape content, center the view.
        For posed/rotated tapes, directly animate the 3D camera (inspect mode) to the element's world position.
        """
        if not self.camera_ctl or not self._should_auto_focus(elem):
            return
        # Automatic scrolling for tape content: always center the camera on reveal for tape elements
        # (the classic sheet behavior the user wants, without manual scroll_tape between items).
        # Non-tape content with world pos still skips.
        if elem.id not in getattr(self, "_tape_content_ids", set()):
            wt = getattr(elem, 'world_transform', None)
            has_world_pos = wt and getattr(wt, 'position', None) and any(getattr(wt.position, 'x', 0) or getattr(wt.position, 'y', 0) or getattr(wt.position, 'z', 0) for _ in [1])
            if has_world_pos:
                return

        target_y = float(elem.canvas_position[1])
        current_y = self.camera_ctl.current_y
        distance = abs(target_y - current_y)
        run_time = min(2.0, max(0.45, 0.3 + distance * 0.11))
        is_tape = elem.id in getattr(self, "_tape_content_ids", set())
        if distance < 0.12 and not is_tape:
            return

        owning_tape = self._element_tape_map.get(elem.id)
        active_tape = owning_tape or getattr(self, "_active_scroll_tape", None) or getattr(self, "root_tape", None)
        local_x = float(elem.canvas_position[0]) if len(elem.canvas_position) > 0 else 0.0
        is_posed_tape = False
        if active_tape and getattr(active_tape, "world_transform", None):
            wt = active_tape.world_transform
            p = wt.position
            r = wt.rotation
            px, py, pz = p.as_tuple() if hasattr(p, "as_tuple") else (getattr(p, "x", 0), getattr(p, "y", 0), getattr(p, "z", 0))
            rx, ry, rz = r.as_tuple() if hasattr(r, "as_tuple") else (getattr(r, "x", 0), getattr(r, "y", 0), getattr(r, "z", 0))
            sc = float(getattr(wt, "scale", 1.0))
            is_posed_tape = (abs(float(px)) > 1e-9 or abs(float(py)) > 1e-9 or abs(float(pz)) > 1e-9 or
                             abs(float(rx)) > 1e-9 or abs(float(ry)) > 1e-9 or abs(float(rz)) > 1e-9 or
                             abs(sc - 1.0) > 1e-9)

        wt = getattr(elem, "world_transform", None)
        if is_posed_tape and active_tape and getattr(active_tape, "world_transform", None):
            # For posed tape in scroll mode, compute the look point on the tape plane using the element's full local position (x, y)
            # and the (owning) tape transform. This makes the camera "scroll" along the tape to center the element exactly.
            local_x = float(elem.canvas_position[0]) if len(elem.canvas_position) > 0 else 0.0
            local_y = target_y
            local_z = float(elem.canvas_position[2]) if len(elem.canvas_position) > 2 else 0.0
            local_point = tuple(getattr(elem, 'canvas_position', (0.0, target_y, 0.0))[:3])
            wpos = local_to_world_point(local_point, active_tape.world_transform)
            self.registry.pause_far_updaters(current_y, buffer=5.0)
            self.camera_ctl._view_mode = "inspect"
            self.camera.use_orthographic_projection = True
            if active_tape and getattr(active_tape, "world_transform", None):
                phi, theta, gamma = get_tape_straight_above_angles(active_tape.world_transform)
                self.camera_ctl._phi.set_value(phi)
                self.camera_ctl._theta.set_value(theta)
                self.camera_ctl._gamma.set_value(gamma)
            self.play(
                self.camera_ctl._inspect_x.animate(rate_func=smooth, run_time=run_time).set_value(wpos[0]),
                self.camera_ctl._inspect_y.animate(rate_func=smooth, run_time=run_time).set_value(wpos[1]),
                self.camera_ctl._inspect_z.animate(rate_func=smooth, run_time=run_time).set_value(wpos[2]),
                self.camera_ctl._x.animate(rate_func=smooth, run_time=run_time).set_value(local_x),
                self.camera_ctl._y.animate(rate_func=smooth, run_time=run_time).set_value(target_y),
                run_time=run_time,
            )
            self.camera.frame_center = np.array(wpos)
            self.registry.pause_far_updaters(target_y, buffer=3.5)
        else:
            # Classic sheet scroll or non-posed tape.
            # Drive both _x/_y (for sheet mode) and inspect_* (for cases where
            # view_mode=inspect because root 3D objects were added; keeps tape
            # scrolling working even in mixed 3D+tape scenes).
            self.camera_ctl._x.set_value(local_x)
            self.camera_ctl._inspect_x.set_value(local_x)
            self.camera_ctl._inspect_y.set_value(target_y)
            self.registry.pause_far_updaters(current_y, buffer=5.0)
            if getattr(self.camera_ctl, "_view_mode", "sheet") == "inspect":
                self.play(
                    self.camera_ctl._inspect_x.animate(rate_func=smooth, run_time=run_time).set_value(local_x),
                    self.camera_ctl._inspect_y.animate(rate_func=smooth, run_time=run_time).set_value(target_y),
                    self.camera_ctl._x.animate(rate_func=smooth, run_time=run_time).set_value(local_x),
                    self.camera_ctl._y.animate(rate_func=smooth, run_time=run_time).set_value(target_y),
                    run_time=run_time,
                )
            else:
                self.camera_ctl.pan_to(target_y, run_time=run_time)
            self.registry.pause_far_updaters(target_y, buffer=3.5)

    def _handle_element_reveal(self, elem: CanvasElement, play_animation: bool = True):
        """Reveal an element lazily: create + (optionally) play entry animation.

        This is called when the timeline reaches this element's slot.
        Creation happens here (lazy), not upfront.

        play_animation=False is used for static population (e.g. full sheet exports)
        so elements appear in their final state instantly without Write/FadeIn etc.
        In the normal video timeline, play_animation=True ensures the "writing" animation
        plays exactly when we reach the element during scrolling — no premature add.
        """
        self._element_specs[elem.id] = elem

        mob = self.registry.get(elem.id)
        first_time = mob is None
        pos = None
        # Hoist for use in placement and add logic
        is_tape_content = elem.id in getattr(self, "_tape_content_ids", set())
        # Prefer the owning tape for this element (from map), fallback to current active/root.
        # This ensures secondary tapes' content get their own rotation/pose applied, even if
        # revealed before a scroll_tape/observe for that tape.
        owning_tape = self._element_tape_map.get(elem.id)
        active_tape = owning_tape or getattr(self, "_active_scroll_tape", None) or getattr(self, "root_tape", None)
        has_tape_pose = bool(
            is_tape_content and active_tape and getattr(active_tape, "world_transform", None)
        )
        container = None
        if is_tape_content and active_tape:
            container = self._tape_containers.get(getattr(active_tape, "id", None))

        if first_time:
            # Lazy instantiation - the key "not pre-written" behavior
            # Phase 8: in 3D prebuilt path, may already exist
            mob = self._build_mobject(elem)
            if mob is None:
                return
            wt = getattr(elem, 'world_transform', None)

            # Position using world coords for posed tape content so visual position exactly matches
            # the wpos used for camera focus. This fixes the 3D<->tape coord transition that was
            # causing residual edge tilt.
            if has_tape_pose:
                local_pt = tuple(getattr(elem, 'canvas_position', (0.0, 0.0, 0.0))[:3])
                wpos = local_to_world_point(local_pt, active_tape.world_transform)
                pos = np.array(wpos, dtype=float)
                mob.move_to(pos)
                # Orient the mobject to lie on the tape's rotated plane.
                rx, ry, rz = active_tape.world_transform.rotation.as_tuple()
                if abs(rx) > 1e-9:
                    mob.rotate(rx * DEGREES, axis=RIGHT)
                if abs(ry) > 1e-9:
                    mob.rotate(ry * DEGREES, axis=UP)
                if abs(rz) > 1e-9:
                    mob.rotate(rz * DEGREES, axis=OUT)
                # For non-default (rotated) tapes, flip the facing so the front of the content
                # faces the correct side (the side the straight-above camera looks from).
                # This prevents inverted/backface view. Default tape (no rotation) is unaffected.
                if abs(rx) > 1e-9 or abs(ry) > 1e-9 or abs(rz) > 1e-9:
                    R = _rotation_matrix_from_euler_deg(rx, ry, rz)
                    y_axis = R @ np.array([0., 1., 0.])
                    mob.rotate(180 * DEGREES, axis=y_axis)
            elif container is not None:
                local_pos = getattr(elem, 'canvas_position', (0.0, 0.0, 0.0))
                pos = np.array(local_pos, dtype=float)
                mob.move_to(pos)
            else:
                if wt and hasattr(wt, 'position'):
                    p = wt.position
                    pos = np.array(p.as_tuple() if hasattr(p, 'as_tuple') else p, dtype=float)
                else:
                    pos = np.array(elem.canvas_position, dtype=float)
                if elem.type == "Solid3D":
                    place_solid_on_tape(mob, tuple(pos), elem.content)
                    pos = mob.get_center()
                else:
                    mob.move_to(pos)
            # Register early ...
            self.registry.register(elem.id, mob, pos[1] if len(pos)>1 else 0, tuple(pos))

            # If we are currently in a dimmed tape-scroll mode, dim this new element
            # unless it belongs to the active tape.
            if (getattr(self, "_current_dim_tape_id", None)
                    and getattr(self, "_observation_mode", None) == ObservationMode.TAPE_SCROLL
                    and self._active_scroll_tape):
                active = self._get_active_ids(self._active_scroll_tape)
                if elem.id not in active:
                    try:
                        mob.set_opacity(self._current_dim_opacity)
                    except Exception:
                        pass

        # Phase 8: if prebuilt in 3D world graph, skip re-reveal/add/anim
        if getattr(self, '_world_objects', None) and elem.id in self._world_objects:
            if first_time:
                self._setup_state_behavior(elem, mob)
                self._apply_billboard_labels(elem, mob)
            return

        if not play_animation:
            # Static path (exports etc.): add in final rendered state, no entry anims played,
            # no camera transition plays (export will override camera/mobs for snapshot anyway).
            if first_time:
                self.add(mob)
                self._setup_state_behavior(elem, mob)
                self._apply_billboard_labels(elem, mob)
            elif mob not in getattr(self, "mobjects", []):
                self.add(mob)
            return

        # === Animated reveal path (the main video "as it scrolls" case) ===
        # Scroll so new content appears at the viewport center (not drifting to the bottom).
        # Phase 2/8: sheet focus / pan only in tape-scroll-mode for tape content.
        # Always focus tape content when in scroll mode (even if they have composed world_transform from pose).
        # This is what drives the camera to center new elements on the (rotated) tape plane.
        is_tape_content = elem.id in getattr(self, "_tape_content_ids", set())
        # Always auto-focus tape content so the camera automatically scrolls/centers on new elements
        # in tape mode (just like classic sheet). The has_world_pos skip is only for free 3D objects.
        do_focus = first_time and self._should_auto_focus(elem)
        if do_focus:
            if is_tape_content or not (wt and getattr(wt, 'position', None) and any(getattr(wt.position, 'x', 0) or getattr(wt.position, 'y', 0) or getattr(wt.position, 'z', 0) for _ in [1])):
                self._focus_on_element(elem)

        # Camera mode adjustments (tilt/return) only apply in tape-scroll mode for tape content.
        # In normal 3D observation, leave the camera as the keyframe set it.
        # Use tape context for tape_content too so auto-focus on initial posed tape content
        # does not get snapped back by return_to_sheet.
        is_tape_ctx = getattr(self, "_observation_mode", ObservationMode.NORMAL_3D) == ObservationMode.TAPE_SCROLL or is_tape_content
        if self.camera_ctl:
            if is_tape_ctx:
                if elem.type in ("ThreeDGraph", "Surface") and elem.pitch is not None:
                    self.camera_ctl.tilt_for_3d(phi=elem.pitch, run_time=0.8)
                elif self.camera_ctl.is_tilted:
                    # After a 3D break on the tape, return to flat tape view for subsequent content
                    # so the tape stays "straight on" (phi=0, theta=-90) instead of staying tilted.
                    self.camera_ctl.return_to_sheet(run_time=0.6)
            else:
                if elem.type in ("ThreeDGraph", "Surface") and elem.pitch is not None:
                    self.camera_ctl.tilt_for_3d(phi=elem.pitch, run_time=0.8)
                elif elem.type == "Solid3D":
                    if self.camera_ctl.view_mode != "sheet":
                        self.camera_ctl.return_to_sheet(run_time=0.6)
                elif self.camera_ctl.is_tilted:
                    self.camera_ctl.return_to_sheet(run_time=0.6)

        if first_time:
            # Do NOT self.add(mob) before the play! Adding the fully-built mobject
            # first would make it pop in instantly (final state). The entry animation
            # (Write / FadeIn) is what introduces it with effect. This fixes the
            # "appears without animation, then re-animated" symptom.
            # Phase 2/8: for tape content on transformed tape, add to the prebuilt container
            # so it inherits the tape's world transform. Content stays lazy.
            # Add to container (for posed tape content) or to scene
            # For posed tape content we placed at absolute world pos; add directly to scene
            # to avoid the container's transform being applied on top of world pos.
            if container is not None and not has_tape_pose:
                container.add(mob)
            elif not (getattr(self, '_world_objects', None) and elem.id in self._world_objects):
                # avoid double add for prebuilts
                self.add(mob)

            if elem.entry_animation:
                anim = get_entry_animation(mob, elem.entry_animation)
                self.play(anim, run_time=elem.entry_animation.run_time)
            else:
                self.play(FadeIn(mob, run_time=0.6))
            # Attach state behaviors (e.g. 3D slow rotation) *after* the entry animation
            # so the idle animation starts immediately once the element is visible,
            # without being delayed by the FadeIn/Write or running during the introduction.
            self._setup_state_behavior(elem, mob)
            self._apply_billboard_labels(elem, mob)
            # (already registered above)
        else:
            # Already revealed earlier in timeline; just ensure it's present (no re-anim).
            if mob not in getattr(self, "mobjects", []):
                self.add(mob)

    def _apply_billboard_labels(self, elem: CanvasElement, mob: Mobject) -> None:
        """Solid3D point labels always face the camera during inspect."""
        if elem.type == "Solid3D":
            apply_billboard_labels(self, mob)

    def populate_from_dsl(self, dsl: SheetDSL | None = None, play_entries: bool = False):
        """Populate (lazily reveal) all elements from the DSL.

        When play_entries=False (default for exports), elements are added in their
        final static state instantly with no entry animations. This is used for
        full sheet PNG/PDF exports so we get clean "after writing" screenshots
        without the Write/FadeIn sequences playing.
        Phase 8: also populates from root_objects / tape if present.
        """
        if dsl is None:
            dsl = self.dsl
        # Phase 8: 3D world objects
        if getattr(dsl, 'root_objects', None):
            for wo in dsl.root_objects:
                # for export, build with play=False
                if wo.element:
                    self._handle_element_reveal(wo.element, play_animation=play_entries)
                for child in wo.children:
                    if child.element:
                        self._handle_element_reveal(child.element, play_animation=play_entries)
        if getattr(dsl, 'root_tape', None) and getattr(dsl.root_tape, 'local_elements', None):
            for elem in dsl.root_tape.local_elements:
                self._handle_element_reveal(elem, play_animation=play_entries)
        # Phase 8: additional tapes
        for atape in getattr(dsl, 'additional_tapes', []) or []:
            if atape and getattr(atape, 'local_elements', None):
                for elem in atape.local_elements:
                    self._handle_element_reveal(elem, play_animation=play_entries)
        # legacy
        for item in getattr(dsl, 'timeline', []):
            if isinstance(item, CanvasElement):
                self._handle_element_reveal(item, play_animation=play_entries)

    def _handle_plot_trace(self, trace: PlotTrace) -> None:
        """Move the tracing dot along a quadratic curve."""
        mob = self.registry.get(trace.element_id)
        part = get_plot_part(mob, trace.plot_index) if mob is not None else None
        if part is None:
            return

        if mob not in getattr(self, "mobjects", []):
            self.add(mob)

        x_from = float(trace.x_from)
        x_to = float(trace.x_to)
        tracker = ValueTracker(x_from)

        def _update_dot(dot):
            x = tracker.get_value()
            dot.move_to(part.point_at(x))
            if part.readout is not None and trace.show_readout:
                y = part.y_at(x)
                part.readout.become(
                    Text(
                        f"x = {x:.1f},  y = {y:.1f}",
                        font_size=18,
                        color="#ffdd66",
                    ).next_to(dot, UR, buff=0.08)
                )

        part.dot.add_updater(_update_dot)
        self.play(
            tracker.animate(run_time=trace.run_time).set_value(x_to),
            run_time=trace.run_time,
        )
        part.dot.remove_updater(_update_dot)
        _update_dot(part.dot)

    def _handle_solid_lift(self, lift: SolidLift) -> None:
        """Raise a volumetric element off the tape for orbit inspection."""
        spec = self._element_specs.get(lift.element_id)
        mob = self.registry.get(lift.element_id)
        if spec is None or mob is None:
            return

        rate = self._get_rate_func(lift.rate_func)
        center = mob.get_center()
        target = np.array([center[0], center[1], float(lift.lift)], dtype=float)
        self.play(
            mob.animate(rate_func=rate, run_time=lift.run_time).move_to(target),
            run_time=lift.run_time,
        )
        if isinstance(spec.content, dict):
            updated = dict(spec.content)
            updated["lift"] = float(lift.lift)
            spec.content = updated
        self.registry.move_to_canvas(
            lift.element_id,
            float(target[1]),
            (float(target[0]), float(target[1]), float(target[2])),
        )

    def _handle_solid_rotate(self, action: SolidRotate) -> None:
        """Rotate a volumetric element about its center with optional holds."""
        mob = self.registry.get(action.element_id)
        if mob is None:
            return
        if mob not in getattr(self, "mobjects", []):
            self.add(mob)
        RotationEngine(self).apply(action, mob)

    def _handle_camera_inspect(self, inspect: CameraInspect) -> None:
        """Keyframe inspect path around a 3D target."""
        spec = self._element_specs.get(inspect.element_id)
        mob = self.registry.get(inspect.element_id)
        if spec is None or mob is None or self.camera_ctl is None:
            return

        InspectEngine(self, camera_ctl=self.camera_ctl).apply(inspect, mob, spec)

    def _handle_camera_focus(self, focus: CameraFocus) -> None:
        """Delegate to FocusEngine — isolate-zoom or overlay magnifier."""
        spec = self._element_specs.get(focus.element_id)
        mob = self.registry.get(focus.element_id)
        if spec is None or mob is None:
            return

        FocusEngine(
            self,
            camera_ctl=self.camera_ctl,
            registry=self.registry,
            frame_width=self.settings.frame_width,
            frame_height=self.settings.frame_height,
        ).apply(focus, mob, spec)

    def _handle_transform(self, transform: TransformElement):
        source = self.registry.get(transform.source_id)
        if source is None:
            return

        # Update registry first (new canonical position)
        new_pos = np.array(transform.target_position, dtype=float)
        self.registry.move_to_canvas(
            transform.source_id, new_pos[1], transform.target_position
        )

        # Move the actual mobject + run the requested action
        action = transform.action.lower()
        rt = transform.run_time

        if action in ("flashandscale", "flash", "highlight"):
            anim = FLASH_AND_SCALE(source, transform.scale_factor, run_time=rt)
            self.play(anim)
            # Also physically move it to the new canvas coordinate
            self.play(source.animate.move_to(new_pos), run_time=rt * 0.6)
        else:
            # Default: just move it
            self.play(source.animate.move_to(new_pos), run_time=rt)

    # --------------------------- Builders & Behaviors ------------------------

    def _build_mobject(self, elem: CanvasElement) -> Mobject | None:
        """Create the Manim mobject via the shared measure/build pipeline."""
        return build_mobject(elem, surface_factory=self._make_default_surface)

    def _build_world_object(self, wo: WorldObject) -> None:
        """Phase 8: build a WorldObject in world space."""
        if wo.element:
            if isinstance(wo.element, dict):
                # from json, minimal support; full reconstruction later
                return
            mob = self._build_mobject(wo.element)
            if mob:
                wt = wo.transform or WorldTransform()
                pos = wt.position.as_tuple() if hasattr(wt.position, 'as_tuple') else getattr(wt, 'position', (0,0,0))
                mob.move_to(pos)
                # apply rotation if 3D support
                if hasattr(mob, 'rotate') and wt.rotation:
                    # simple apply, manim 3d rotation
                    pass  # extend as needed
                self.add(mob)
                self._world_objects[wo.id] = mob
                self.registry.register(wo.id, mob, pos[1] if len(pos)>1 else 0, pos)
                if wo.element:
                    self._element_specs[wo.id] = wo.element
        for child in wo.children:
            self._build_world_object(child)

    def _build_tape_container(self, tape: TapeObject) -> None:
        """Phase 2: build tape container (transformed in world) early.
        Tape content is instantiated lazily in _handle_element_reveal only when reached.
        This preserves the narrative writing feel even for positioned/rotated tapes.
        """
        if not tape:
            return
        tape_group = VGroup()
        wt = tape.world_transform or WorldTransform()
        pos = wt.position.as_tuple() if hasattr(wt.position, 'as_tuple') else (0.0, 0.0, 0.0)
        tape_group.move_to(pos)

        # Apply rotation (basic per-axis for container)
        rx, ry, rz = wt.rotation.as_tuple() if hasattr(wt.rotation, 'as_tuple') else (0.0, 0.0, 0.0)
        if abs(rx) > 1e-9:
            tape_group.rotate(rx * DEGREES, axis=RIGHT)
        if abs(ry) > 1e-9:
            tape_group.rotate(ry * DEGREES, axis=UP)
        if abs(rz) > 1e-9:
            tape_group.rotate(rz * DEGREES, axis=OUT)

        self.add(tape_group)
        self._world_objects[tape.id] = tape_group
        self._tape_containers[tape.id] = tape_group
        self.registry.register(tape.id, tape_group, pos[1] if len(pos) > 1 else 0, pos)

    def _make_default_surface(self, equation: str | None = None):
        """Render-quality 3D surface parsed from the element equation."""
        return make_render_surface(equation)

    def _setup_state_behavior(self, elem: CanvasElement, mob: Mobject):
        """Attach idle continuous behaviors (e.g. slow rotation for 3D objects)."""
        if not elem.state_behavior:
            return

        btype = elem.state_behavior.type.lower()
        params = elem.state_behavior.params or {}

        if btype == "rotate_slowly":
            speed = params.get("speed", 0.28)  # radians per second
            axis = UP
            updater = lambda m, dt: m.rotate(dt * speed, axis=axis)
            self.registry.add_updater(elem.id, updater)

    # =====================================================================
    # FULL CANVAS STATIC EXPORT (PNG / PDF) - second most important feature
    # =====================================================================

    def export_full_sheet(
        self,
        filename: str | Path,
        format: Literal["png", "pdf"] = "png",
        high_res_height: int | None = None,
        margin: float = 1.2,
        title: str | None = None,
        camera_preset: Literal["top_down", "isometric", "auto"] = "isometric",
        full_tape: bool = False,  # NEW: when True, the output image uses the natural aspect of the written content (no forced portrait/landscape from video settings). This makes full-tape screenshots trivial as you described.
    ) -> Path:
        """Export a clean static screenshot of the *entire* revealed canvas.

        This is designed for serious learners who want to study the full sheet
        after (or instead of) watching the video.

        - Collects all revealed elements (lazy system means only what was shown).
        - Applies pre-defined static states from the DSL (static_phi, static_theta, etc.)
          so 3D elements have a clean, study-friendly pose instead of mid-animation rotation.
        - Computes the full vertical bounding box.
        - Produces a high-quality full-view image of the "infinite sheet".
        - Supports PNG (best quality, efficient) and PDF (document-style, great for printing/studying).

        Args:
            filename: Output path (extension will be adjusted based on format).
            format: "png" (recommended for quality) or "pdf" (document style).
            high_res_height: Target height in pixels for the export (None = use current render height scaled to content).
            margin: Extra margin around the content (in Manim units).
            title: Optional title embedded in PDF.
            camera_preset: How to view 3D content statically ("isometric" is usually nicest for study).
            full_tape: When True, the output PNG/PDF uses the natural aspect ratio of the written content (the "entire tape" you described). No forced portrait/landscape cropping from the video settings. Perfect for study screenshots of the full sheet.

        Returns:
            Path to the saved file.
        """
        if Image is None:
            raise RuntimeError("Pillow (PIL) is required for sheet export. It should be in the venv.")

        filename = Path(filename)
        if format == "pdf":
            out_path = filename.with_suffix(".pdf")
        else:
            out_path = filename.with_suffix(".png")

        print(f"[export] Preparing full static sheet export ({format.upper()})...")

        # Phase 8: 3D world support (incl. multiple tapes)
        has_tapes = bool(getattr(self, 'root_tape', None) or getattr(self.dsl, 'additional_tapes', None))
        is_3d = bool(getattr(self, '_world_objects', None) or has_tapes)
        if is_3d and camera_preset == "auto":
            camera_preset = "isometric"

        # 1. Get all revealed mobjects + their specs
        entries = list(self.registry._store.values())
        if not entries:
            print("[export] No elements revealed yet. Nothing to export.")
            return out_path

        mobs_with_specs = []
        for uid, entry in self.registry._store.items():
            spec = self._element_specs.get(uid)
            mobs_with_specs.append((entry.mobject, spec, uid))

        # 2. Compute tight bounding box from ONLY the active visible mobjects.
        # This is the critical fix for the "defective auto-crop" reported.
        # We explicitly build a VGroup of real content (excluding any invisible anchors or extra camera padding).
        content_mobs = [m for m, spec, uid in mobs_with_specs if uid != "__title__"]  # title added separately

        min_x = float("inf")
        max_x = float("-inf")
        min_y = float("inf")
        max_y = float("-inf")

        for mob in content_mobs:
            try:
                bb = mob.get_bounding_box()
                min_x = min(min_x, bb[0][0])
                max_x = max(max_x, bb[2][0])
                min_y = min(min_y, bb[0][1])
                max_y = max(max_y, bb[2][1])
            except Exception:
                left = mob.get_left()[0]
                right = mob.get_right()[0]
                bottom = mob.get_bottom()[1]
                top = mob.get_top()[1]
                min_x = min(min_x, left)
                max_x = max(max_x, right)
                min_y = min(min_y, bottom)
                max_y = max(max_y, top)

        content_width = max_x - min_x
        content_height = max_y - min_y
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # If title provided, create it as a proper Manim Text above the content
        # so it participates in bounding box and feels integrated into the sheet
        title_mob = None
        if title:
            try:
                from manim import Text
                title_mob = Text(title, font_size=48, color=WHITE).scale(0.7)
                title_y = max_y + 1.2
                title_mob.move_to([center_x, title_y, 0])
                # Add to the list for later cleanup, but include in content for framing
                mobs_with_specs.append((title_mob, None, "__title__"))
                content_mobs.append(title_mob)  # so it affects the final tight bb
                # Recompute bb with title included
                t_left = title_mob.get_left()[0]
                t_right = title_mob.get_right()[0]
                t_bottom = title_mob.get_bottom()[1]
                t_top = title_mob.get_top()[1]
                min_x = min(min_x, t_left)
                max_x = max(max_x, t_right)
                min_y = min(min_y, t_bottom)
                max_y = max(max_y, t_top)
                content_width = max_x - min_x
                content_height = max_y - min_y
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2
            except Exception:
                title_mob = None

        # 3. Freeze to static states (critical for 2D/3D)
        # We apply static poses for the screenshot. Restore is best-effort only.
        for mob, spec, uid in mobs_with_specs:
            if spec is None:
                continue

            # Apply pre-defined static state from DSL (user can define clean pose for study)
            try:
                if spec.static_scale != 1.0:
                    mob.scale(spec.static_scale)

                if spec.static_opacity != 1.0 and hasattr(mob, "set_opacity"):
                    mob.set_opacity(spec.static_opacity)

                # 3D static pose - this is the key for "static state of 3D elements"
                if spec.static_phi is not None or spec.static_theta is not None:
                    phi = spec.static_phi if spec.static_phi is not None else 30
                    theta = spec.static_theta if spec.static_theta is not None else -60
                    mob.rotate(phi * DEGREES, axis=UP)
                    mob.rotate(theta * DEGREES, axis=RIGHT)  # approximate good view for study

                # Global fallback for 3D content if no per-element static defined
                # Also apply to standalone 2D texts (like the tagline) so they get oriented the same as the 3D view.
                # This makes them appear perfectly front-on and horizontal ("0 angle", no climbing/tilt) like the saddle formula.
                elif camera_preset != "auto" and (self._is_3d_like(mob) or isinstance(mob, (Text, MathTex))):
                    if camera_preset == "top_down":
                        mob.rotate(0 * DEGREES, axis=UP)
                    elif camera_preset == "isometric":
                        mob.rotate(25 * DEGREES, axis=UP)
                        mob.rotate(-35 * DEGREES, axis=RIGHT)
            except Exception:
                pass  # best effort for complex mobjects

        # Post-process for better export aesthetics (addresses overlap and uneven spacing)
        # Nudge text containing "remembers" clear of 3D surfaces
        for mob, spec, uid in mobs_with_specs:
            if mob is not None:
                try:
                    text_content = ""
                    if hasattr(mob, "get_tex_string"):
                        text_content = mob.get_tex_string()
                    elif hasattr(mob, "get_text"):
                        text_content = mob.get_text()
                    if "remembers" in str(text_content).lower():
                        mob.shift(DOWN * 0.7)
                except Exception:
                    pass

        # 4. Temporarily reconfigure camera to tightly frame the *full content* (not forced to original canvas aspect)
        # This is the deep fix for the defective auto-crop / massive empty black block.
        orig_center = self.camera.frame_center.copy()
        orig_frame_h = self.camera.frame_height
        orig_frame_w = self.camera.frame_width
        orig_ortho = getattr(self.camera, "use_orthographic_projection", True)

        if full_tape:
            # Full tape mode (your clarified desired behavior): the static screenshot is the entire written tape
            # in its natural shape. No forced portrait (9:16) or landscape (16:9) aspect from the video viewport.
            # This makes "generating the tape but without cropping it to portrait or landscape formats" trivial.
            total_width = content_width + 2 * margin
            total_height = content_height + 2 * margin
        else:
            # Classic behavior (respects original canvas_settings aspect for the sheet image, like video)
            total_height = content_height + 2 * margin
            total_width = max(content_width + 2 * margin, total_height * (self.settings.frame_width / self.settings.frame_height))

        self.camera.use_orthographic_projection = True
        self.camera.frame_center = np.array([center_x, center_y, 0])
        self.camera.frame_height = total_height
        self.camera.frame_width = total_width

        # 5. High-quality capture with independent resolution for the static export
        # (decoupled from the animation render resolution)
        target_height = high_res_height or 2160  # nice default for study images (can be 4K tall)
        aspect = total_width / total_height if total_height > 0 else 1.0
        target_width = int(target_height * aspect)

        # Use tempconfig to boost the pixel buffer for this snapshot only.
        # Explicitly disable any video writing to avoid conflicts with a previously active file_writer
        # (this was causing the avcodec_open2 crash in background threads).
        with tempconfig({
            "pixel_width": max(target_width, 100),
            "pixel_height": max(target_height, 100),
            "background_color": self.settings.background_color,
            "write_to_movie": False,
            "save_last_frame": False,
            "format": "png",  # not relevant but harmless
        }):
            self.wait(0.001)
            self.renderer.update_frame(self)

            # Billboard standalone 2D texts (tagline) to face the camera perfectly.
            # This ensures "very front look with 0 angle", perfectly horizontal, no climbing/tilt in the final image.
            # Applied here (after 3D poses and camera view are set) so the text plane is parallel to the view.
            for mob in self.mobjects:
                if isinstance(mob, (Text, MathTex)):
                    # Skip if it's inside a 3D VGroup (those labels stay with their surface rotation and look "fine")
                    # Top-level tagline Text will be billboarded.
                    if not any(self._is_3d_like(sub) for sub in getattr(mob, "submobjects", [])):
                        phi = self.camera.get_phi()
                        theta = self.camera.get_theta()
                        mob.rotate(-phi, axis=RIGHT)
                        mob.rotate(-theta, axis=UP)

            img = self.renderer.camera.get_image()
            if not isinstance(img, Image.Image):
                arr = np.array(img)
                img = Image.fromarray(arr)

        # Clean up temporary title mobject (if added for integrated layout)
        if 'title_mob' in locals() and title_mob is not None and title_mob in getattr(self, "mobjects", []):
            self.remove(title_mob)

        # Final tight PIL crop to the actual rendered content (eliminates wasted black space / black void)
        try:
            img = self._auto_crop_to_content(img, bg_threshold=25, padding=20)
        except Exception:
            pass  # best effort

        # 6. Optional nice title banner (now added after tight crop for better integration)
        if title:
            try:
                from PIL import ImageDraw, ImageFont
                banner_h = 70
                banner = Image.new('RGB', (img.width, banner_h), (15, 15, 15))
                draw = ImageDraw.Draw(banner)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
                except:
                    font = ImageFont.load_default()
                draw.text((25, 18), title, fill=(230, 230, 230), font=font)

                # Add a subtle separator line
                draw.rectangle([0, banner_h-3, img.width, banner_h], fill=(60, 60, 60))

                final = Image.new('RGB', (img.width, img.height + banner_h), (0,0,0))
                final.paste(banner, (0, 0))
                final.paste(img, (0, banner_h))
                img = final
            except Exception:
                pass

        # 8. Save
        if format == "pdf":
            save_kwargs = {"resolution": 200.0}
            if title:
                save_kwargs["title"] = title
            img.save(out_path, "PDF", **save_kwargs)
        else:
            img.save(out_path, "PNG", optimize=True)

        print(f"[export] Full sheet saved to {out_path}")

        # 8. Restore camera (we leave mobject static poses as-is since export is usually final)
        self.camera.frame_center = orig_center
        self.camera.frame_height = orig_frame_h
        self.camera.frame_width = orig_frame_w
        self.camera.use_orthographic_projection = orig_ortho

        return out_path

    def _is_3d_like(self, mob: Mobject) -> bool:
        """Heuristic to detect 3D content."""
        return any(
            hasattr(m, "get_z") or "3d" in type(m).__name__.lower() or "surface" in type(m).__name__.lower()
            for m in [mob] + list(getattr(mob, "submobjects", []))
        )

    def _auto_crop_to_content(self, img: "Image.Image", bg_threshold: int = 15, padding: int = 30) -> "Image.Image":
        """Crop the image to the actual non-background content area + padding.

        This is the key fix for eliminating the massive empty black space in exports.
        It makes the output a tight, usable study sheet instead of mostly void.
        """
        import numpy as np

        arr = np.array(img)
        if arr.ndim == 3:
            # For RGB, consider a pixel "content" if any channel differs from black by > threshold
            mask = np.any(arr > bg_threshold, axis=2)
        else:
            mask = arr > bg_threshold

        if not np.any(mask):
            return img

        # Find bounding box of content
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]

        # Add padding, clamp to image bounds
        h, w = arr.shape[:2]
        y_min = max(0, y_min - padding)
        y_max = min(h - 1, y_max + padding)
        x_min = max(0, x_min - padding)
        x_max = min(w - 1, x_max + padding)

        return img.crop((x_min, y_min, x_max + 1, y_max + 1))

    def _get_rate_func(self, name: str):
        name = (name or "smooth").lower()
        if name == "linear":
            return linear
        if name in ("rush", "rush_into"):
            from manim.utils.rate_functions import rush_into
            return rush_into
        if name in ("rush_out",):
            from manim.utils.rate_functions import rush_from
            return rush_from
        return smooth
