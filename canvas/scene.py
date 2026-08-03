"""CanvasScene — the heart of Matemium.

Consumes a SheetDSL and renders an infinite vertically scrollable sheet
by driving camera moves and element entry / transform animations.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import Any, Iterator, List, Literal, Optional, Tuple, Union

from manim import (
    AnimationGroup,
    DEGREES,
    FadeIn,
    FadeOut,
    Mobject,
    OUT,
    RIGHT,
    Text,
    ThreeDScene,
    Transform,
    TransformMatchingShapes,
    UP,
    UR,
    ValueTracker,
)
from manim.utils.rate_functions import linear, smooth


from .animations import FLASH_AND_SCALE, get_entry_animation
from .camera import CameraController
from .dsl import (
    CameraFocus,
    CameraInspect,
    CameraMove,
    CameraKeyframe,  # Phase 3
    CanvasElement,
    CanvasSettings,
    ElementMorph,
    ObjectAnchor,  # Phase 5
    ObservationMode,  # Phase 8
    PlotTrace,
    SheetDSL,
    SolidLift,
    SolidRotate,
    StateTransition,
    TapeScroll,
    TimelineItem,
    TransformElement,
    TapeObject,
    WorldObject,
    WorldTransform,
)
from .solids import place_solid_on_tape
from .coords import local_to_world_point
from .focus import FocusEngine
from .generic_visuals import resolve_semantic_part
from .inspect_engine import InspectEngine
from .rotation_engine import RotationEngine
from .solid_labels import apply_billboard_labels
from .plots import get_plot_part
from .measure import build_mobject, make_render_surface, _OBJECT_KINDS
from .registry import MobjectRegistry


# ---------------------------------------------------------------------------
# Per-item error isolation
# ---------------------------------------------------------------------------

class TimelineExecutionError(Exception):
    """Raised when a timeline item fails during CanvasScene.construct().

    Carries structured, machine-parseable fields so the desktop sidecar's
    AI self-correction loop can pinpoint and fix the offending item without
    having to parse a raw traceback.

    Attributes:
        timeline_index: 0-based position of the failing item in the timeline.
        item_kind:      Broad category — "element", "camera_move",
                        "camera_keyframe", "transform", "plot_trace",
                        "solid_lift", "solid_rotate", "camera_inspect",
                        "camera_focus", "flex_group", or "unknown".
        item_type:      The ``type`` field of the DSL object (e.g. "MathTex",
                        "CameraMove") or the Python class name as a fallback.
        element_id:     The ``id`` of the offending DSL item, or ``None`` when
                        the item carries no stable identifier.
        cause:          The original exception message (str).
        original:       The original exception instance for chained tracebacks.
    """

    def __init__(
        self,
        *,
        timeline_index: int,
        item_kind: str,
        item_type: str,
        element_id: Optional[str],
        cause: str,
        original: BaseException,
    ) -> None:
        self.timeline_index = timeline_index
        self.item_kind = item_kind
        self.item_type = item_type
        self.element_id = element_id
        self.cause = cause
        self.original = original
        super().__init__(
            f"[timeline:{timeline_index}] kind={item_kind!r} type={item_type!r}"
            + (f" id={element_id!r}" if element_id is not None else "")
            + f" — {cause}"
        )

    def to_dict(self) -> dict:
        """Machine-parseable representation for IPC / AI self-correction."""
        return {
            "error": "TimelineExecutionError",
            "timeline_index": self.timeline_index,
            "item_kind": self.item_kind,
            "item_type": self.item_type,
            "element_id": self.element_id,
            "cause": self.cause,
        }


def _item_meta(payload: Any) -> Tuple[str, str, Optional[str]]:
    """Extract (item_kind, item_type, element_id) from a timeline payload.

    Works for both single items and flex-group lists.
    """
    from .dsl import (
        CanvasElement, CameraMove, CameraKeyframe, ElementMorph, StateTransition, TransformElement,
        PlotTrace, SolidLift, SolidRotate, CameraInspect, CameraFocus,
    )

    if isinstance(payload, list):
        # flex_group — use the first element's metadata
        if payload:
            first = payload[0]
            return (
                "flex_group",
                getattr(first, "type", type(first).__name__),
                getattr(first, "flex_group", None) or getattr(first, "id", None),
            )
        return ("flex_group", "unknown", None)

    kind_map = {
        CanvasElement: "element",
        CameraMove: "camera_move",
        CameraKeyframe: "camera_keyframe",
        TransformElement: "transform",
        StateTransition: "state_transition",
        ElementMorph: "element_morph",
        PlotTrace: "plot_trace",
        SolidLift: "solid_lift",
        SolidRotate: "solid_rotate",
        CameraInspect: "camera_inspect",
        CameraFocus: "camera_focus",
    }
    item_kind = next(
        (v for cls, v in kind_map.items() if isinstance(payload, cls)),
        "unknown",
    )
    item_type = getattr(payload, "type", type(payload).__name__)
    element_id = getattr(payload, "id", None)
    return item_kind, item_type, element_id




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
        strict_validation = bool(kwargs.pop("strict_validation", True))
        super().__init__(**kwargs)
        self.dsl = dsl
        self.settings: CanvasSettings = dsl.canvas_settings
        self.registry = MobjectRegistry(viewport_margin=3.0)
        self.camera_ctl: CameraController | None = None

        # --- DSL validation pass (pre-render) ---
        # Run before any Manim setup so errors surface immediately with clear
        # diagnostics rather than as cryptic AttributeErrors mid-render.
        issues = dsl.validate(raise_on_error=strict_validation)
        warnings = [i for i in issues if i.severity.value == "warning"]
        if warnings:
            import sys
            print(
                f"[Matemium] DSL validation: {len(warnings)} warning(s):",
                file=sys.stderr,
            )
            for warning in warnings:
                print(f"  {warning}", file=sys.stderr)
        # Phase 3
        self.root_tape = getattr(dsl, "root_tape", None)
        # Phase 8
        self._world_objects: dict[str, Mobject] = {}
        self._world_transforms: dict[str, WorldTransform] = {}
        # Phase 2/8 (clarified model): explicit observation mode
        self._observation_mode: ObservationMode = ObservationMode.NORMAL_3D
        self._active_scroll_tape: Optional["TapeObject"] = None
        self._tape_content_ids: set[str] = set()
        self._element_tape_map: dict[str, "TapeObject"] = {}  # elem_id -> owning tape (for correct WT even if revealed out of order)
        # Dimming for tape-scroll focus
        self._dimmed_opacities: dict[str, float] = {}
        self._current_dim_tape_id: Optional[str] = None
        self._current_dim_opacity: float = 0.15
        all_tapes = [
            tape
            for tape in (
                [self.root_tape] + list(getattr(self.dsl, "tapes", []) or [])
            )
            if tape is not None
        ]
        for t in all_tapes:
            if t and getattr(t, "local_elements", None):
                for el in t.local_elements:
                    if el and getattr(el, "id", None):
                        self._tape_content_ids.add(el.id)
                        self._element_tape_map[el.id] = t

        # Store specs for all revealed elements (needed for static export with pre-defined static states)
        self._element_specs: dict[str, CanvasElement] = {}

    def construct(self):
        import numpy as np

        self.camera_ctl = CameraController(
            self,
            frame_width=self.settings.frame_width,
            frame_height=self.settings.frame_height,
            existing_camera=self.camera,
        )
        self.camera_ctl._view_mode = "sheet"
        self.camera.set_phi(0)
        self.camera.set_theta(-np.pi/2)
        self.camera.set_gamma(0)

        # Build persistent free-world objects before timeline actions target
        # them. Tapes are camera-facing presentation contexts, not world-space
        # containers, and their content remains lazy.
        for world_object in getattr(self.dsl, "root_objects", []) or []:
            self._build_world_object(world_object)

        # Phase 2/8: build world object structure (transforms) early for 3D placement.
        # Content is kept lazy (revealed on timeline) to preserve narrative "writing".
        # Tape internal content lazy unless in tape-scroll-mode.
        # Default identity root tape keeps full legacy lazy path.
        # Execute the timeline in order (the "compiler")
        for tl_index, (kind, payload) in enumerate(self._iter_timeline_batches()):
            try:
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
                elif isinstance(payload, StateTransition):
                    self._handle_state_transition(payload)
                elif isinstance(payload, ElementMorph):
                    self._handle_element_morph(payload)
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
            except TimelineExecutionError:
                # Already wrapped — re-raise as-is so the structured diagnostic
                # propagates cleanly without double-wrapping.
                raise
            except Exception as exc:
                item_kind, item_type, element_id = _item_meta(payload)
                raise TimelineExecutionError(
                    timeline_index=tl_index,
                    item_kind=item_kind,
                    item_type=item_type,
                    element_id=element_id,
                    cause=str(exc),
                    original=exc,
                ) from exc

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
        """Pan once to the centroid of a flex group in its foreground tape."""
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

        self.camera_ctl._x.set_value(group_x)
        self.camera_ctl._inspect_x.set_value(group_x)
        self.camera_ctl._inspect_y.set_value(target_y)
        
        current_y = self.camera_ctl.current_y
        distance = abs(target_y - current_y)
        if distance < 0.12: return
        run_time = min(2.0, max(0.45, 0.3 + distance * 0.11))
        
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

        active_tape = next(
            (
                self._element_tape_map.get(element.id)
                for element in elements
                if element.id in self._tape_content_ids
            ),
            None,
        )
        if active_tape is not None:
            target_y = sum(float(e.canvas_position[1]) for e in elements) / len(elements)
            self._activate_tape_context(active_tape, local_y=target_y)
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

        prepared: List[Tuple[CanvasElement, Mobject, bool]] = []
        for elem in elements:
            mob = self.registry.get(elem.id)
            first_time = mob is None
            if first_time:
                mob = self._build_mobject(elem)
                if mob is None:
                    continue
            pos = np.array(elem.canvas_position, dtype=float)
            if elem.type == "Solid3D":
                place_solid_on_tape(mob, tuple(pos), elem.content)
                pos = mob.get_center()
            else:
                mob.move_to(pos)
            self.registry.register(elem.id, mob, pos[1], tuple(pos))
            prepared.append((elem, mob, first_time))

        # Add before playing entry animations.
        for elem, mob, first_time in prepared:
            if (
                first_time
                and not (
                    getattr(self, "_world_objects", None)
                    and elem.id in getattr(self, "_world_objects", {})
                )
                and mob not in getattr(self, "mobjects", [])
            ):
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
        switched_context = self._active_scroll_tape is not self.root_tape
        self._activate_tape_context(
            self.root_tape,
            local_y=target_y,
            run_time=min(0.7, move.run_time),
        )
        if self.camera_ctl and not switched_context:
            self.camera_ctl.tape_center_x = 0.0
            self.camera_ctl._x.set_value(0.0)

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
        entered_from_tape = self._observation_mode == ObservationMode.TAPE_SCROLL

        if isinstance(target, TapeScroll):
            tapes = [self.root_tape] + list(getattr(self.dsl, "tapes", []) or [])
            tape = next(
                (candidate for candidate in tapes if candidate and candidate.id == target.tape_id),
                None,
            )
            if tape is None:
                raise ValueError(f"Unknown tape {target.tape_id!r}")

            switched_context = self._active_scroll_tape is not tape
            self._activate_tape_context(
                tape,
                local_y=float(target.local_y),
                run_time=min(0.7, kf.duration),
            )
            if self.camera_ctl and not switched_context:
                self.camera_ctl.observe_target(
                    target,
                    run_time=kf.duration,
                    rate_func=self._get_rate_func(kf.rate_func),
                    tape=tape,
                )
            return

        tape = None
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
            if not entered_from_tape and kind and kind in _OBJECT_KINDS:
                obs_fn = _OBJECT_KINDS[kind].get("observe")
                if obs_fn:
                    try:
                        obs_fn(
                            target,
                            self.camera_ctl,
                            run_time=getattr(kf, "duration", getattr(kf, "run_time", 2.0)),
                            rate_func=self._get_rate_func(getattr(kf, "rate_func", "smooth")),
                            tape=None,
                        )
                        return  # hook handled the observation
                    except Exception:
                        pass  # fall through to default

        if self.camera_ctl:
            if entered_from_tape:
                initial_pose = self.camera_ctl.resolve_observation_pose(
                    target,
                    tape=None,
                    target_transform=target_transform,
                    target_pos_world=target_pos_world,
                )
                self._enter_world_context(initial_pose=initial_pose)
                return
            self._enter_world_context()
            self.camera_ctl.observe_target(
                target,
                run_time=getattr(kf, "duration", getattr(kf, "run_time", 2.0)),
                rate_func=self._get_rate_func(getattr(kf, "rate_func", "smooth")),
                tape=None,
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

    def _all_context_mobjects(self) -> dict[str, Mobject]:
        all_mobs: dict[str, Mobject] = {}
        if self.registry:
            for uid, entry in list(self.registry._store.items()):
                if entry.mobject:
                    all_mobs[uid] = entry.mobject
        for uid, mob in list(getattr(self, "_world_objects", {}).items()):
            if mob:
                all_mobs[uid] = mob
        return all_mobs

    def _protected_context_mobjects(self) -> set[Mobject]:
        """Runtime sentinels that must survive every presentation-context cut."""
        dummy = getattr(getattr(self, "camera_ctl", None), "_dummy", None)
        return {dummy} if dummy is not None else set()

    def _active_tape_mobjects(self, active_tape) -> set[Mobject]:
        active_ids = self._get_active_ids(active_tape)
        return {
            mob
            for uid, mob in self._all_context_mobjects().items()
            if uid in active_ids
        }

    def _get_context_switch_animations(self, active_tape) -> list:
        """Close the active tape over the camera and hide every other context."""
        if not active_tape:
            return []
        active_ids = self._get_active_ids(active_tape)
        self._current_dim_tape_id = getattr(active_tape, "id", None)
        self._current_dim_opacity = 0.0
        anims = []
        seen: set[Mobject] = set()
        
        for uid, mob in self._all_context_mobjects().items():
            seen.add(mob)
            if uid in active_ids:
                if uid in self._dimmed_opacities:
                    self._dimmed_opacities.pop(uid)
                    if mob not in getattr(self, "mobjects", []):
                        anims.append(FadeIn(mob))
            else:
                if uid not in self._dimmed_opacities:
                    self._dimmed_opacities[uid] = 1.0
                if mob in getattr(self, "mobjects", []):
                    anims.append(FadeOut(mob))
        protected = self._protected_context_mobjects()
        for mob in list(getattr(self, "mobjects", [])):
            if mob not in seen and mob not in protected:
                anims.append(FadeOut(mob))
        return anims

    def _enforce_tape_context(self, active_tape) -> None:
        """Make tape isolation true even if Manim leaves faded objects present.

        The animation layer is best-effort: with complex 3D groups/updaters a
        ``FadeOut`` can fail to fully remove the object from the scene graph.
        The presentation model is stricter than that. While a camera-facing tape
        is selected, only already-built content owned by that tape may remain in
        ``scene.mobjects``; free-world objects and other tape contexts are hard
        removed after the transition.
        """
        active_mobs = self._active_tape_mobjects(active_tape)
        protected = self._protected_context_mobjects()
        for mob in list(getattr(self, "mobjects", [])):
            if mob not in active_mobs and mob not in protected:
                self.remove(mob)
        for mob in active_mobs:
            if mob not in getattr(self, "mobjects", []):
                self.add(mob)

    def _enforce_world_context(self) -> None:
        """Show free-world objects and keep every tape context closed."""
        world_mobs = set(getattr(self, "_world_objects", {}).values())
        protected = self._protected_context_mobjects()
        for mob in list(getattr(self, "mobjects", [])):
            if mob not in world_mobs and mob not in protected:
                self.remove(mob)
        for mob in world_mobs:
            if mob not in getattr(self, "mobjects", []):
                self.add(mob)

    def _play_tape_context_switch(
        self,
        active_tape,
        *,
        run_time: float,
        local_y: float = 0.0,
    ) -> None:
        """Fade out, cut to a tape pose, then fade in the selected context."""
        animations = self._get_context_switch_animations(active_tape)
        outgoing = [animation for animation in animations if isinstance(animation, FadeOut)]
        incoming = [animation for animation in animations if isinstance(animation, FadeIn)]
        phases = int(bool(outgoing)) + int(bool(incoming))
        phase_time = run_time / max(phases, 1)
        if outgoing:
            self.play(*outgoing, run_time=phase_time)
        active_mobs = self._active_tape_mobjects(active_tape)
        protected = self._protected_context_mobjects()
        for mob in list(getattr(self, "mobjects", [])):
            if mob not in active_mobs and mob not in protected:
                self.remove(mob)
        if self.camera_ctl:
            self.camera_ctl.snap_to_sheet(target_y=local_y)
        if incoming:
            self.play(*incoming, run_time=phase_time)
        self._enforce_tape_context(active_tape)

    def _activate_tape_context(
        self,
        active_tape,
        *,
        local_y: float,
        run_time: float = 0.7,
    ) -> bool:
        """Select a tape once and return whether a presentation cut occurred."""
        if active_tape is None:
            return False
        switched = self._active_scroll_tape is not active_tape
        self._observation_mode = ObservationMode.TAPE_SCROLL
        self._active_scroll_tape = active_tape
        self._current_focused_tape_id = getattr(active_tape, "id", None)
        if switched:
            self._play_tape_context_switch(
                active_tape,
                run_time=run_time,
                local_y=local_y,
            )
            self._just_transitioned = True
        return switched

    def _get_world_context_animations(self) -> list:
        """Open the foreground tape and restore only free-world content.

        Previously revealed tapes stay hidden. Restoring every dimmed object
        caused the unreadable pile-up captured in the orbital bug screenshot.
        """
        anims = []
        tape_ids = set(self._tape_content_ids)
        for uid, mob in self._all_context_mobjects().items():
            if uid in tape_ids:
                if mob in getattr(self, "mobjects", []):
                    anims.append(FadeOut(mob))
            elif mob not in getattr(self, "mobjects", []):
                anims.append(FadeIn(mob))

        self._dimmed_opacities.clear()
        self._current_dim_tape_id = None
        self._current_dim_opacity = 0.15
        return anims

    def _enter_world_context(self, *, initial_pose=None, run_time: float = 0.7) -> None:
        """Fade out the tape, cut the camera, then reveal the free 3D world."""
        if self._observation_mode == ObservationMode.TAPE_SCROLL:
            animations = self._get_world_context_animations()
            outgoing = [animation for animation in animations if isinstance(animation, FadeOut)]
            incoming = [animation for animation in animations if isinstance(animation, FadeIn)]
            phases = int(bool(outgoing)) + int(bool(incoming))
            phase_time = run_time / max(phases, 1)
            if outgoing:
                self.play(*outgoing, run_time=phase_time)
            for uid, mob in self._all_context_mobjects().items():
                if uid in self._tape_content_ids and mob in getattr(self, "mobjects", []):
                    self.remove(mob)
            self._observation_mode = ObservationMode.NORMAL_3D
            if initial_pose is not None and self.camera_ctl:
                self.camera_ctl.snap_to_pose(initial_pose)
            if incoming:
                self.play(*incoming, run_time=phase_time)
            self._enforce_world_context()
        self._observation_mode = ObservationMode.NORMAL_3D
        self._active_scroll_tape = None
        self._current_focused_tape_id = None

    # Backward-compatible internal name used by older tests.
    def _get_restore_animations(self) -> list:
        return self._get_world_context_animations()

    def _should_auto_focus(self, elem: CanvasElement) -> bool:
        """Overlays (e.g. grid marks) stay on an already-framed board — no re-pan."""
        return elem.auto_focus and elem.type != "GridMark"

    def _focus_on_element(self, elem: CanvasElement) -> None:
        """Pan within the active camera-facing tape."""
        if getattr(self, "_just_transitioned", False):
            setattr(self, "_just_transitioned", False)
            return
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
        if distance < 0.12:
            return

        local_x = float(elem.canvas_position[0]) if len(elem.canvas_position) > 0 else 0.0
        
        self.camera_ctl._x.set_value(local_x)
        self.camera_ctl._inspect_x.set_value(local_x)
        self.camera_ctl._inspect_y.set_value(target_y)
        self.camera_ctl.pan_to(target_y, run_time=run_time)
        self.registry.pause_far_updaters(target_y, buffer=3.5)


    def _handle_element_reveal(self, elem: CanvasElement, play_animation: bool = True):
        """Reveal an element lazily: create + (optionally) play entry animation."""

        # --- AUTO-TRANSITION TO NEW TAPE ---
        is_tape_content = elem.id in getattr(self, "_tape_content_ids", set())
        active_tape = self._element_tape_map.get(elem.id)
        
        if is_tape_content and play_animation and active_tape:
            self._activate_tape_context(
                active_tape,
                local_y=float(getattr(elem, "canvas_position", (0, 0, 0))[1]),
            )

        # --- END AUTO-TRANSITION ---

        # This is called when the timeline reaches this element's slot.
        # Creation happens here (lazy), not upfront.
        # 
        # play_animation=False is used for static population (e.g. full sheet exports)
        # so elements appear in their final state instantly without Write/FadeIn etc.
        # In the normal video timeline, play_animation=True ensures the "writing" animation
        # plays exactly when we reach the element during scrolling - no premature add.
        self._element_specs[elem.id] = elem

        mob = self.registry.get(elem.id)
        first_time = mob is None
        pos = None
        # Hoist for use in placement and add logic
        is_tape_content = elem.id in getattr(self, "_tape_content_ids", set())
        owning_tape = self._element_tape_map.get(elem.id)
        active_tape = owning_tape or getattr(self, "_active_scroll_tape", None)

        if first_time:
            # Lazy instantiation - the key "not pre-written" behavior
            # Phase 8: in 3D prebuilt path, may already exist
            mob = self._build_mobject(elem)
            if mob is None:
                return
            wt = getattr(elem, 'world_transform', None)

            has_explicit_world_position = bool(
                not is_tape_content
                and wt
                and hasattr(wt, "position")
                and any(abs(float(value)) > 1e-12 for value in wt.position.as_tuple())
            )
            if has_explicit_world_position:
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
        is_tape_content = elem.id in getattr(self, "_tape_content_ids", set())
        # Tape elements scroll in local 2D coordinates. Free-world objects with
        # explicit positions remain under cinematic camera control.
        do_focus = first_time and self._should_auto_focus(elem)
        if do_focus:
            if is_tape_content or not (wt and getattr(wt, 'position', None) and any(getattr(wt.position, 'x', 0) or getattr(wt.position, 'y', 0) or getattr(wt.position, 'z', 0) for _ in [1])):
                self._focus_on_element(elem)

        # Camera mode adjustments (tilt/return) only apply in tape-scroll mode for tape content.
        # In normal 3D observation, leave the camera as the keyframe set it.
        # Tape content always uses the flat, camera-facing presentation camera.
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
            if not (getattr(self, '_world_objects', None) and elem.id in self._world_objects):
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
        """Open the foreground tape, then inspect a free 3D target."""
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

    def _resolve_state_target(self, target_id: str) -> Mobject:
        element_id, separator, part_id = target_id.partition("::")
        root = self.registry.get(element_id)
        if root is None:
            raise ValueError(f"State target element {element_id!r} is not in the registry")
        if not separator:
            return root
        part = resolve_semantic_part(root, part_id)
        if part is None:
            raise ValueError(f"Semantic part {part_id!r} is not available on {element_id!r}")
        return part

    @staticmethod
    def _vector3(value: Any) -> np.ndarray:
        values = list(value)
        if len(values) == 2:
            values.append(0.0)
        return np.array(values, dtype=float)

    def _handle_state_transition(self, transition: StateTransition) -> None:
        animations = []
        for patch in transition.patches:
            target = self._resolve_state_target(patch.target_id)
            changes = patch.changes
            animation = target.animate
            if "color" in changes:
                animation = animation.set_color(changes["color"])
            if "fill_color" in changes:
                animation = animation.set_fill(color=changes["fill_color"])
            if "fill_opacity" in changes:
                animation = animation.set_fill(opacity=float(changes["fill_opacity"]))
            stroke_kwargs: dict[str, Any] = {}
            if "stroke_color" in changes:
                stroke_kwargs["color"] = changes["stroke_color"]
            if "stroke_opacity" in changes:
                stroke_kwargs["opacity"] = float(changes["stroke_opacity"])
            if "stroke_width" in changes:
                stroke_kwargs["width"] = float(changes["stroke_width"])
            if stroke_kwargs:
                animation = animation.set_stroke(**stroke_kwargs)
            if "opacity" in changes:
                animation = animation.set_opacity(float(changes["opacity"]))
            if "scale" in changes:
                animation = animation.scale(float(changes["scale"]))
            if "shift" in changes:
                animation = animation.shift(self._vector3(changes["shift"]))
            if "position" in changes:
                animation = animation.move_to(self._vector3(changes["position"]))
            animations.append(animation)
        if animations:
            group = AnimationGroup(
                *animations,
                lag_ratio=transition.lag_ratio,
                run_time=transition.run_time,
                rate_func=self._get_rate_func(transition.rate_func),
            )
            self.play(group)

    def _handle_element_morph(self, morph: ElementMorph) -> None:
        source = self.registry.get(morph.element_id)
        if source is None:
            raise ValueError(f"Morph target {morph.element_id!r} is not in the registry")
        target = self._build_mobject(morph.target)
        if target is None:
            raise ValueError(f"Morph target kind {morph.target.type!r} did not build a mobject")
        world_transform = self._world_transforms.get(morph.element_id)
        if world_transform is not None:
            # Registered world builders author their geometry in local coordinates.
            # Preserve that local origin across state changes instead of aligning
            # visual bounding-box centers. Bounding boxes can move dramatically
            # when an asymmetric path or annotation is added, which used to pull
            # stable geometry (and especially 3D surfaces) sideways during morphs.
            self._apply_world_transform(target, world_transform)
        else:
            target.move_to(source.get_center())
        source_was_visible = source in getattr(self, "mobjects", [])
        if source_was_visible:
            animation_cls = TransformMatchingShapes if morph.match_shapes else Transform
            self.play(
                animation_cls(source, target),
                run_time=morph.run_time,
                rate_func=self._get_rate_func(morph.rate_func),
            )
        # Keep the freshly compiled target so its semantic part registry is authoritative.
        self.remove(source)
        if source_was_visible:
            self.add(target)
        self.registry.replace(morph.element_id, target)
        self._element_specs[morph.element_id] = morph.target
        if morph.element_id in self._world_objects:
            self._world_objects[morph.element_id] = target

    # --------------------------- Builders & Behaviors ------------------------

    def _build_mobject(self, elem: CanvasElement) -> Mobject | None:
        """Create the Manim mobject via the shared measure/build pipeline."""
        return build_mobject(elem, surface_factory=self._make_default_surface)

    @staticmethod
    def _apply_world_transform(mob: Mobject, wt: WorldTransform) -> None:
        """Apply a world pose around the builder's local origin.

        ``Mobject.move_to`` aligns bounding-box centers, not object-space
        origins. That distinction matters for asymmetric registered objects:
        changing a long trajectory, callout, or tail must not move the central
        solid. World transforms therefore translate local coordinates directly
        and rotate/scale around the translated origin.
        """
        pos = np.array(
            wt.position.as_tuple()
            if hasattr(wt.position, "as_tuple")
            else getattr(wt, "position", (0.0, 0.0, 0.0)),
            dtype=float,
        )
        mob.shift(pos)
        if hasattr(mob, "rotate") and wt.rotation:
            rx, ry, rz = wt.rotation.as_tuple()
            if abs(rx) > 1e-9:
                mob.rotate(rx * DEGREES, axis=RIGHT, about_point=pos)
            if abs(ry) > 1e-9:
                mob.rotate(ry * DEGREES, axis=UP, about_point=pos)
            if abs(rz) > 1e-9:
                mob.rotate(rz * DEGREES, axis=OUT, about_point=pos)
        if abs(float(wt.scale) - 1.0) > 1e-9:
            mob.scale(float(wt.scale), about_point=pos)

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
                self._apply_world_transform(mob, wt)
                self.add(mob)
                self._world_objects[wo.id] = mob
                self._world_transforms[wo.id] = wt
                self.registry.register(wo.id, mob, pos[1] if len(pos)>1 else 0, pos)
                if wo.element:
                    self._element_specs[wo.id] = wo.element
        for child in wo.children:
            self._build_world_object(child)

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
        full_tape: bool = False,
        tape_id: str | None = None,
    ) -> Path:
        """Export a clean static document of a complete tape.

        The tape is rebuilt in local document coordinates and rendered through
        fresh orthographic cameras.  The live video camera, renderer, world
        transforms, and mobject updaters are never reused.  ``camera_preset`` is
        retained for API compatibility but does not affect a 2D tape document.
        """
        from .tape_export import export_tape_document

        print(f"[export] Preparing isolated tape export ({format.upper()})...")
        output = export_tape_document(
            self.dsl,
            filename,
            format=format,
            tape_id=tape_id,
            high_res_height=high_res_height,
            margin=margin,
            title=title,
            natural_aspect=full_tape,
        )
        print(f"[export] Tape saved to {output}")
        return output

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
