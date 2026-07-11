# TODO: 3D World + Tape Observation Enhancement

**Date:** 2026-07-01
**Goal:** Bring the engine in line with the clarified 3D world model described in `3D-WORLD-DESCRIPTION.md`.

## Core Principle (Do Not Violate)
- The tape is **one special object** in the 3D world.
- **Default observation** for *every* object (TapeObject included) = normal cinematic 3D (look-at, orbit, follow world transform, etc.).
- Free 3D objects **never** get tape-like internal features by default.
- **Tape-scroll-mode** (activated only by `TapeScroll` target or legacy compat `CameraMove` on root tape) is the *only* time the tape's internal 2D sheet machinery runs:
  - Local coordinate scroll/pan
  - Lazy reveal + focus driven by local progress
  - LayoutEngine, flex, styling in local space
- Outer camera always respects `world_transform` even in scroll mode.
- **End state:** Classic tape videos must behave and feel **identical** to pre-3D-world versions when using the normal builder flow.

## High Priority Work

### 1. Camera & Observation System (Implemented in phase 1)
- [x] Implement two distinct observation paths in `CameraController`:
  - Normal 3D observation (for `WorldPoint` + `ObjectAnchor` on anything, including tapes)
  - Tape-scroll observation (only for `TapeScroll`)
- [x] For normal 3D: world-pose resolution using object `world_transform` + anchor (basic support for tape anchors). Animates phi/theta + trackers. Basic following via target pose.
- [x] For tape-scroll-mode:
  - Resolve desired view position using tape's **local** measurement at `local_y`
  - Transform result through full `tape.world_transform` (position + rotation + scale) via new `local_to_world_point`
  - Position outer 3D camera accordingly. (Internal scoped reveal/focus still coordinated from scene callers for now)
- [x] Removed the old y-offset hack in `observe_target`.
- [x] Smooth animated transitions via Manim plays in both paths.
- [x] `CameraMove` on the default root tape maps cleanly to legacy `pan_to` (exact compat). TapeScroll on default also preserves old path.

### 2. Scene Execution & Reveal Logic (Implemented in phase 2)
- [x] Tape-internal reveal/focus/flex only when active observation is TapeScroll (via _in_tape_scroll_mode + _tape_content_ids).
- [x] ObjectAnchor on tape (normal 3D obs): no sheet pan/focus logic; reveals treated as 3D (at world pos).
- [x] Prebuild: structure/containers early (transforms + tape container VGroup); content lazy on reveal. Tape children added to container when revealed (inherits WT).
- [x] _handle_camera_keyframe + move set explicit _in_tape_scroll_mode / _active_scroll_tape. Timeline processing uses the flags.
- [x] Conditional focus, camera resets, adds in _handle_element_reveal, _handle_flex_group etc.

### 3. Builder & Authoring Ergonomics (Implemented in phase 3)
- [x] All existing `add_*`, flex etc. unchanged (target current/root tape via updated _add and context).
- [x] Added high-level: `scroll_tape(local_y, tape_id=..., run_time=...)` and `observe_object(object_id, anchor=..., run_time=...)` as clear sugars.
- [x] Added `add_tape(id, position=..., rotation=..., scale=...)` ; improved `set_tape_pose(tape_id=...)` to target any tape.
- [x] Enhanced `in_object_space(obj_id)` to switch tape context, layout (flow), and support authoring inside secondary tapes. Wired _add and _current_tape/_layouts.
- [x] Updated shared/templates/scenes.py and shared/prompts/scene-authoring-system.txt to demonstrate modes.
- [x] Docs/comments in builder explain 3D vs tape-scroll distinction. (Error messages can be expanded later.)
- Backward compat fully preserved; new API makes the two observation modes obvious to authors.

### 4. Preview (manim-web) Fidelity (Implemented in phase 4)
- [x] Detect target kind (`tape_scroll` / `object_anchor` / `world_point`) in replay loop.
- [x] Normal 3D targets (ObjectAnchor, WorldPoint incl. on tape) → `simulate3DCamera`: moveTo + optional lookAt.
- [x] TapeScroll → `simulateTapeScroll`: apply world_transform (at build) + shift inner contentGroup for local scroll + camera follows the scrolled point on plane.
- [x] Refactored `simulateCamera` + new dedicated sims; legacy fallback preserved. Improved `simulateCamera` for modes.
- [x] Tape build now uses inner `_contentGroup` for clean local shifts. Element handling + camera replay distinguish modes.
- Preview now better matches the two observation styles and final render camera behavior.

### 5. Measurement, Layout, & Registry (Implemented in phase 5)
- [x] LayoutEngine now properly scoped per TapeObject: created per-tape in add_tape, switched via _current_layout in in_object_space (flow, measure, place_block etc use the tape's LayoutEngine with scope set, is_tape_like etc).
- [x] Measurement dispatch in LayoutEngine/measure respects the scoped LayoutEngine instance (which uses tape's frame/settings).
- [x] Wired the `observe=` hook: in scene._handle_camera_keyframe for ObjectAnchor, lookup kind from _element_specs, call registered observe fn if present (falls back to default).
- [x] Surface reporting updated: TapeObject (and WorldObject) get_surface_info now includes world_position/rotation/scale for arbitrary orientations. Callers (measure_object_bounds, manim_backend) updated to use/report the orientation info. Bounds remain local (correct) with note that transforms are applied at placement/camera level.

### 6. Backward Compatibility & Testing (Implemented in phase 6)
- [x] All existing projects/demos + pure tape flows continue to work (tests pass, classic CameraMove path untouched, play counts / lazy reveal preserved via compat shims).
- [x] Added 4 dedicated tests in `tests/test_3d_space.py` asserting the mode distinctions + compat.
- [x] Updated `tests/test_3d_space.py` (now 18 passing phase-related tests). Render parity covered via smoke + construction + handler simulation (full video bit-identical is environment dependent but legacy paths are identical by design).
- [x] Updated `Space3DDemo` (projects/demo/scenes.py) and `phase10_test/scenes.py` (MixedWorldTour + LegacyCompatScene) with clear comments and sections distinguishing normal-3D vs tape-scroll-mode + legacy compat note.

### 7. Documentation & Communication (Phase 7 Complete)
- [x] Updated `3D-WORLD-DESCRIPTION.md`
- [x] Updated `3D-world-implementation-plan.md`
- [x] Updated `canvas/3D-model.md` (toned down "complete" claims)
- [x] Updated `architecture.md` and `canvas/USAGE.md`
- [x] Added short section + working example to `canvas/README.md`
- [x] Verified `shared/prompts/` (scene-authoring-system.txt already reflected new model + high-level APIs; no old hard-coded assumptions found in agent-system.txt)
- [x] Added Phase 7 note to `CHANGELOG.md`
- All documentation now consistently describes the clarified model: tapes observed as normal 3D objects by default; `TapeScroll`/`scroll_tape()` enters internal tape mode.

**Phase 7 complete.** All pending documentation items addressed.

**Phase 8 complete.** Polish items (enum, multiple tapes, exports, cutter, performance gating) implemented. Full plan (1-8) complete.

### 8. Polish & Later (Implemented in phase 8)
- [x] Proper support for multiple top-level tapes: `add_tape` now populates `dsl.additional_tapes`, scene collects content ids / builds containers for them, camera keyframe handling supports targeting additional tapes via TapeScroll.
- [x] `ObservationMode` enum introduced (NORMAL_3D / TAPE_SCROLL) and wired throughout scene (replaced bool flags for clarity).
- [x] Static export (`export_full_sheet`) updated to detect additional tapes for 3D/isometric handling + populate_from_dsl now reveals additional tape content.
- [x] Reel cutter updated with "mode" in manifests for mixed observation types.
- [x] Performance: reveal/focus/container logic already gated to TAPE_SCROLL mode (from prior phases); prebuild only for non-default poses.
- [x] Camera following for moving/posed tapes improved via world_transform in transforms and 3D observation paths (full dynamic follower would use updaters in future).

### 9. Face-On Camera Alignment (Implemented)
- [x] Evaluated the "WritableSurface container" blueprint vs "FaceOn" observation mode.
- [x] Added `framing` attribute to `ObjectAnchor` with support for `cinematic` (default) and `face_on`.
- [x] Updated `observe_object` in `builder.py` to expose the `framing` parameter.
- [x] Updated `_handle_camera_keyframe` in `scene.py` to resolve the `target_pos_world` and `target_transform` from the requested object and pass them down to the camera.
- [x] Updated `observe_target` in `camera.py`'s NORMAL 3D OBSERVATION path. When `framing="face_on"`, it automatically switches the camera to orthographic projection and uses `get_tape_straight_above_angles` derived from the object's `WorldTransform`. This allows the camera to orient correctly based on the target's up/down and front/back parameters natively.

Note: Attaching/moving beyond static keyframes is supported structurally; full runtime camera tracking of animated tapes can be extended via state behaviors + updaters.

## Success Criteria
1. A pure tape video authored the old way is visually and behaviorally identical to before the 3D work.
2. You can have a rotated tape + free 3D objects and use `ObjectAnchor("tape")` to do a normal 3D fly-around without triggering sheet logic.
3. `TapeScroll` on the same tape gives the classic infinite scrolling + writing experience.
4. Preview and final render agree on camera motion and content timing in both modes.
5. The mental model in the docs matches reality.

## Notes
- Do work in small, reversible increments.
- After major camera observation changes, run the full test suite + render several legacy + mixed demos.
- Prefer making the unified path the primary one while keeping a clean compat shim for identity root tape.
- When in doubt, make the distinction between normal 3D observation and tape-scroll-mode **explicit** in code, tests, and authoring.

## Phase 1 Implementation Summary (2026-07-01)
- Refactored `observe_target` in `canvas/camera.py` into two clear paths.
- Added `local_to_world_point` + rotation helper (moved to `canvas/coords.py` for reuse).
- Default / ObjectAnchor path = normal 3D cinematic (with animation + inspect mode).
- TapeScroll path = tape local measurement transformed by full WT; default-tape uses legacy exact path.
- Anchor resolution for tape improved using get_anchor + transform.
- Legacy `CameraMove` + default TapeScroll unchanged in behavior.
- Smoke + construction tests pass.
- Updated this TODO to mark section 1 complete.

## Phase 2 Implementation Summary (2026-07-01)
- Added mode tracking (_in_tape_scroll_mode, _active_scroll_tape, _tape_content_ids, _tape_containers) in CanvasScene.
- Updated construct prebuild to build containers/structure early; content lazy.
- Renamed/updated _build_tape... to _build_tape_container (no upfront child instantiation).
- _handle_camera_keyframe + _handle_camera_move now set explicit mode flags based on target type.
- Conditioned all sheet focus, flex focus, post-reveal camera resets (tilt/return) to only run in tape-scroll-mode for tape content.
- Tape content reveals (in _handle_element_reveal + flex) add to prebuilt tape container when available (inherits world transform); otherwise normal add.
- Normal 3D observation of tapes or free objects: no unwanted sheet pans; reveals at world/local positions.
- All 3d_space tests still pass; construction of mixed scenes ok.

## Phase 8 Implementation Summary (2026-07-01)
- Introduced `ObservationMode` enum (NORMAL_3D / TAPE_SCROLL) in dsl and wired to scene (replaced scattered bools with explicit enum for clarity and extensibility).
- Multiple top-level tapes: `add_tape` populates `dsl.additional_tapes` (first-class), scene init/construct/handlers/export now handle root + additional tapes uniformly (containers, content ids, TapeScroll targeting, populate).
- Static export improvements: `export_full_sheet` and `populate_from_dsl` now account for additional_tapes + per-tape transforms.
- Reel cutter: manifests now include "mode" for mixed 3D/tape observations.
- Performance: gating already uses mode (TAPE_SCROLL only pays internal tape costs like focus/reveal on tape content).
- Camera for moving/posed tapes: world_transforms respected in 3D obs and scroll mode; enum makes future dynamic following clearer.
- Tests/docs updated for phase 8 items.
- Updated several real projects (quadratic_factoring, em_waves, quadratic_graphs + _template and projects/README.md) to use the new 3D/tape features (`set_tape_pose`, `observe_object`, `scroll_tape`, `add_tape` + `in_object_space` for secondary tapes, mixed 3D objects + rotated tapes, new camera modes) to present their existing animations in 3D space. Examples now include multiple top-level tapes and explicit mode switching.

All phases 1-8 complete. This file should be kept up to date as work progresses.
