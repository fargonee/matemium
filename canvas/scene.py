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
    CanvasElement,
    CanvasSettings,
    PlotTrace,
    SheetDSL,
    SolidLift,
    SolidRotate,
    TimelineItem,
    TransformElement,
)
from .solids import place_solid_on_tape
from .focus import FocusEngine
from .inspect_engine import InspectEngine
from .rotation_engine import RotationEngine
from .solid_labels import apply_billboard_labels
from .plots import get_plot_part
from .measure import build_mobject, make_render_surface
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

        # IMPORTANT: No pre-instantiation of elements.
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
        """Pan once to the centroid of a flex group before combined reveal."""
        if not self.camera_ctl or not elements:
            return
        ys = [float(e.canvas_position[1]) for e in elements]
        target_y = sum(ys) / len(ys)
        current_y = self.camera_ctl.current_y
        distance = abs(target_y - current_y)
        if distance < 0.12:
            return
        run_time = min(2.0, max(0.45, 0.3 + distance * 0.11))
        self.registry.pause_far_updaters(current_y, buffer=5.0)
        self.camera_ctl.pan_to(target_y, run_time=run_time)
        self.registry.pause_far_updaters(target_y, buffer=3.5)

    def _handle_flex_group_reveal(
        self,
        elements: List[CanvasElement],
        play_animation: bool = True,
    ) -> None:
        """Reveal each flex item as its own element — one scroll, simultaneous entry."""
        if not elements:
            return

        for elem in elements:
            self._element_specs[elem.id] = elem

        if not play_animation:
            for elem in elements:
                self._handle_element_reveal(elem, play_animation=False)
            return

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

        # Pause far updaters before big camera travel
        if self.camera_ctl:
            self.registry.pause_far_updaters(self.camera_ctl.current_y, buffer=5.0)
            self.camera_ctl.pan_to(target_y, run_time=move.run_time, rate_func=rate)
            # After arrival, resume relevant updaters
            self.registry.pause_far_updaters(target_y, buffer=3.5)

    def _should_auto_focus(self, elem: CanvasElement) -> bool:
        """Overlays (e.g. grid marks) stay on an already-framed board — no re-pan."""
        return elem.auto_focus and elem.type != "GridMark"

    def _focus_on_element(self, elem: CanvasElement) -> None:
        """Pan the viewport so the element reveals at the center of the frame."""
        if not self.camera_ctl or not self._should_auto_focus(elem):
            return

        target_y = float(elem.canvas_position[1])
        current_y = self.camera_ctl.current_y
        distance = abs(target_y - current_y)
        if distance < 0.12:
            return

        run_time = min(2.0, max(0.45, 0.3 + distance * 0.11))
        self.registry.pause_far_updaters(current_y, buffer=5.0)
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
        if first_time:
            # Lazy instantiation - the key "not pre-written" behavior
            mob = self._build_mobject(elem)
            if mob is None:
                return
            pos = np.array(elem.canvas_position, dtype=float)
            if elem.type == "Solid3D":
                place_solid_on_tape(mob, tuple(pos), elem.content)
                pos = mob.get_center()
            else:
                mob.move_to(pos)
            # Register early so the element is known in the model (for visibility, re-use, etc.)
            # even during its entry animation. State behavior (updaters) attached after
            # introduction so idle animations (e.g. 3D rotation) start cleanly right after
            # the element has appeared, without delay or concurrent with FadeIn/Write.
            self.registry.register(elem.id, mob, pos[1], elem.canvas_position)

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
        if first_time:
            self._focus_on_element(elem)

        # Sheet plane (z=0) is the default. Tilt only for 3D surfaces; return to sheet
        # when flat content follows — never flip camera mode on every text block.
        if self.camera_ctl:
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
        """
        if dsl is None:
            dsl = self.dsl
        for item in dsl.timeline:
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
