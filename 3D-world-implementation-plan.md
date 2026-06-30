# 3D World Unification Implementation Plan

**Goal:** Evolve the Matemium engine from a sheet-first system (with bolted-on 3D) into a true infinite 3D space where the current "infinite tape/sheet" is simply one special kind of object (`TapeObject` or equivalent). This enables a more generic, abstract, granular engine while preserving (and enhancing) the powerful CSS-like styling, layout, lazy reveal, and WYSIWYG preview characteristics of the sheet.

**Source Vision:** See `3D-WORLD-DESCRIPTION.md` (the extended mental model).

**Key Problems This Plan Addresses:**
- Constant patching of lesson/object-specific code into the core engine.
- Need for a more granular/abstract engine (leveraging the original intent behind CSS-like styling for sheet positions).
- Deep but clean integration between rendering, layout, camera, and preview (manim-web).
- Supporting full 3D space (XZ ground + Y height) without duplicating systems or breaking the existing sheet UX.
- Renderer-agnostic measurement and 1-1 manim-web powered preview.
- Unified handling of absolute/relative positioning, camera keyframes, and "observation modes" that differ for tapes vs. regular 3D objects.
- Avoiding "two parallel universes" while keeping the sheet productive for narrative math videos.

**Guiding Principles:**
- **Evolutionary, not big-bang rewrite.** Current sheet behavior must continue to work (and improve) at every milestone.
- **Tape as a first-class but special Object.** It lives in world 3D space (with transform) but owns its internal 2D local space + layout engine + styling.
- **Observation modes over special cases.** Camera targets objects (or points) and delegates behavior based on the target's observation protocol.
- **Local spaces everywhere.** Measurement, layout, and content authoring happen in an object's local coordinates. World space is only for placement, transforms, and general camera.
- **Registry + protocols for extensibility.** New object kinds (or custom visuals) register their local renderer/measure/observe logic instead of requiring core patches.
- **Preview is the 3D world.** manim-web renders the full 3D scene; special "tape observation" reuses/enhances the existing high-fidelity sheet preview logic.
- **One by one.** Each step is small, testable, and builds only on completed prior steps. Backwards compatibility for existing `scenes.py` / DSL where possible.
- **Document as we go.** Update architecture.md, canvas/USAGE.md, desktop-architecture.md, etc.

**Risks & Mitigations (high-level):**
- Sheet UX regression → Prioritize "tape mode" preservation in every phase; use existing tests + new 3D examples.
- Preview complexity → Start with sheet-only 3D world (tapes only), add free 3D objects later.
- Performance (many objects/tapes) → Reuse lazy instantiation and registry patterns from current code.
- Migration effort → Provide compatibility shims and migration helpers in builder/scene.

**Overall Phases (Sequential)**

## Phase 0: Setup, Audit, and Modeling (No breaking changes)

**Purpose:** Establish the plan, map current code to new model, update docs. Make the vision concrete without touching logic yet.

1. Read and internalize `3D-WORLD-DESCRIPTION.md` (already done).
2. Audit current architecture:
   - Map `canvas/` modules (dsl.py, builder.py, scene.py, camera.py, layout.py, measure.py, coords.py, etc.) to new concepts (Object, TapeObject, local space, Observation).
   - Identify all places that hard-assume "sheet at z=0" (e.g., `SHEET_PLANE_Z`, camera defaults, flow state in LayoutEngine).
   - Document current 3D-on-sheet usage (Solid3D, pitch, CameraInspect, etc.).
3. Create/update supporting docs:
   - Add section to `architecture.md` and `canvas/README.md` describing the new model.
   - Create or update `canvas/3D-model.md` (or similar) with diagrams (ASCII or mermaid) of:
     - World space + Objects (Tape vs. Solid vs. Group).
     - Local vs. world coordinates.
     - Camera keyframe targeting + observation delegation.
   - Update `desktop-architecture.md` to mention future 3D canvas mode for preview.
4. Define core terminology and data shapes (in docs only for now):
   - `WorldTransform` (position, rotation, scale).
   - `ObjectId`, `Anchor` (named points like center, edge, local (x,y)).
   - `ObservationTarget` (WorldPoint | ObjectRef | TapeScroll {tape_id, local_y, framing}).
   - `CameraKeyframe` (time, target, params, easing).
5. Inventory existing special types and plan migration path (QuadraticPlot etc. → either composed or registered custom objects).
6. Set up basic test scaffolding if needed (e.g., a new `tests/test_3d_space.py` skeleton that currently just asserts current behavior).
7. **Milestone:** Plan approved, docs updated, current sheet still 100% functional. No code changes to core logic.

**Dependencies:** None (pure docs/audit).
**Success:** Anyone reading the docs understands "the tape is now a TapeObject in 3D space".

## Phase 1: Core 3D Object Model & World Space (Foundation)

**Purpose:** Introduce the generic "everything is an object in 3D space" without changing behavior for the current tape.

1. Introduce world coordinate primitives (new or in `canvas/coords.py` or new `canvas/space.py`):
   - `WorldTransform`, `Vector3`, helpers for absolute vs. relative resolution (resolve position relative to another object's anchor or origin).
2. Refactor `CanvasElement` (in `dsl.py`):
   - Keep backward compat (default to tape-local behavior).
   - Add `world_transform: WorldTransform` (or position/orientation/scale fields).
   - Add `parent_object_id` or `space` hint (for now mostly implicit).
   - Make `type: str` (already trending this way) fully open.
3. Introduce minimal `Object` / scene graph concept:
   - A registry (extend or replace current `MobjectRegistry`) that tracks objects by id + their world transforms.
   - Base "object" handling that can wrap current elements.
4. Update `CanvasSettings` / `SheetDSL`:
   - Add `mode` or `coordinate_system` (initially only "sheet" for compat).
   - Support declaring root objects.
5. **Internal only for now:** Make the current sheet implicitly a root `TapeObject` at identity transform.
6. Update serialization (to_dict, from_dict, IPC) to carry transforms (backward compatible).
7. **Milestone:** Code can represent elements with explicit world transforms. Existing code paths still treat everything as on the default sheet. Tests pass.

**Dependencies:** Phase 0.
**Success Criteria:** Can place two elements with relative positioning in docs/tests (without full runtime).

## Phase 2: TapeObject as First-Class Special Object

**Purpose:** Explicitly model the current sheet behavior as the internal logic of a TapeObject.

1. Define `TapeObject` (new dataclass or subclass of CanvasElement / new abstraction in dsl.py):
   - `world_transform`
   - `local_elements: list[CanvasElement]` (the old timeline items now live inside a tape).
   - `local_layout: LayoutEngine` (reuse existing, scoped to the tape's local space).
   - Internal 2D size / surface reporting for measurement & 3D rendering.
2. Move / adapt current sheet layout, flex, styling, lazy reveal, and flow logic to operate on a TapeObject's local space.
3. Update `CanvasBuilder`:
   - By default, operations build inside an implicit root TapeObject (for backward compat).
   - Add explicit methods like `add_tape(...)`, `enter_tape_context(id)`, `place_object_in_world(...)` (later phases).
   - `element_spec`, `math_spec`, etc. become ways to populate a tape's local content.
4. Adapt `LayoutEngine` and `measure.py` to be instantiable per-object (especially for tapes) + support the new measurement protocol.
5. Update coords.py, viewport_fit.py, etc. to handle local vs world.
6. **Milestone:** The existing sheet authoring (`add_flex_row`, styling, etc.) now conceptually lives inside a TapeObject. Runtime behavior identical.

**Dependencies:** Phase 1 (transforms).
**Success:** All current projects/ demos still render exactly the same.

## Phase 3: Generalized Camera & Keyframe Observation System

**Purpose:** Replace sheet-centric camera with a general 3D observer that has special behavior for tapes.

1. Redesign camera primitives (in `canvas/camera.py` or new `canvas/observation.py`):
   - `ObservationTarget` union: `WorldPoint`, `ObjectAnchor`, `TapeScroll(local_y, framing_mode, ...)`.
   - `CameraKeyframe(time, target, look_at_offset?, easing, duration, ...)` 
   - General smooth path interpolation (position + angles).
2. Extend `CameraController` (or new `CameraSystem`):
   - Support world 3D navigation (free XYZ + full phi/theta when not on a tape).
   - When target is a TapeObject (or TapeScroll): delegate to "tape observation protocol" that reuses existing pan_to, focus, reveal logic in the tape's *local* coordinates, while applying the tape's world transform to the outer camera.
   - Modes: "free_3d", "observing_tape", "cinematic_lookat", etc.
   - Support relative targets ("follow object X while also tracking tape Y").
3. Update timeline items:
   - Generalize `CameraMove` → `CameraObservation` (or keep alias for compat).
   - Add support for object-targeted keyframes (`target_object_id`, `tape_scroll_params`).
4. Adapt `scene.py` execution loop:
   - During construct, resolve observations against the object registry + current world transforms.
   - Trigger tape-internal lazy reveal when observing a tape.
5. Preserve existing sheet camera behavior exactly when using old-style CameraMove on the default tape.
6. **Milestone:** Camera can keyframe to world points and to a tape (with correct internal scrolling/reveal). Old scenes unchanged.

**Dependencies:** Phase 2 (tapes as objects).
**Success:** Existing tilt/inspect/sheet panning still work; new tape-targeted keyframes produce equivalent or better behavior.

## Phase 4: Positioning, Relative Anchors & Transforms (Core Power)

**Purpose:** Make relative/absolute positioning and object-relative camera natural.

1. Implement resolution helpers:
   - `resolve_position(target, relative_to=None)` → world coords. Supports centers, named anchors, local offsets on any object.
2. Update `CanvasBuilder` and DSL with relative placement APIs (e.g., `place_relative_to(other_id, local_offset, style=...)`).
3. Extend `TapeObject` (and other objects) to expose anchors (e.g., "top_edge", "content_center", custom).
4. Update camera keyframes to support `target: {object_id: "...", anchor: "center"}`.
5. Add support for object transforms affecting children (a rotated tape affects its internal local coords when observed).
6. **Milestone:** Can author a scene with a tape at an angle + a 3D solid positioned relative to a point on the tape, with camera keyframing between them.

**Dependencies:** Phase 3.
**Success:** Relative positioning works for both regular objects and tape-local content.

## Phase 5: Timeline, DSL & Builder Generalization

**Purpose:** Make the authoring model support the new 3D world while keeping sheet ergonomics.

1. Evolve `SheetDSL` → more general `WorldDSL` or `SceneGraph` (keep SheetDSL as sugar for tape-heavy cases).
2. Timeline becomes a mix of:
   - Object creation/placement (with world_transform or relative).
   - Animations on objects (entry + state behaviors).
   - Camera observations.
   - Special actions (still supported inside tapes or generalized).
3. Update builder methods to be context-aware (current tape context vs world).
4. Support `add_raw` for low-level 3D objects.
5. Backward compat layer: old builder calls implicitly target the default tape.
6. Update IPC protocol (`get_preview_data`, etc.) to include object graph + observations.
7. **Milestone:** New scenes can mix tape content and free 3D objects using the builder. Old scenes unaffected.

**Dependencies:** Phases 1-4.
**Success:** `CanvasBuilder` remains the primary authoring surface; complexity of 3D is opt-in.

## Phase 6: Renderer-Agnostic Measurement & Layout (Deepen Existing Work)

**Purpose:** Make the measurement protocol and layout fully object-local and ready for mixed 2D/3D.

1. Expand the `MeasurementBackend` protocol (already started in `canvas/measurement/`) to support:
   - Per-object-kind backends.
   - 2D content inside tapes (current KaTeX path).
   - 3D bounding / surface measurement for general objects.
2. Make `LayoutEngine` always scoped to a specific object's local space (tapes get the full CSS+flex; other objects may use identity or simple rules).
3. For content on a tape: measurement must be accurate for manim-web preview even when the tape is transformed in world space.
4. Add "surface reporting" API on TapeObject (and other planar objects) so 3D renderers know where the 2D content lives.
5. **Milestone:** Layout/measurement works correctly for content inside a transformed TapeObject.

**Dependencies:** Phase 2 (tapes), Phase 1 (objects).
**Success:** WYSIWYG fidelity preserved/improved; new measurement backends easy to plug (including future web-side ones).

## Phase 7: manim-web Preview as Full 3D World + Special Tape Mode

**Purpose:** Make the desktop live preview a true manim-web 3D renderer that handles the new model.

1. Update preview data (from `sidecar_get_preview_data` / `get_preview_data`):
   - Include full object graph with world transforms.
   - List of observations / camera keyframes.
   - Per-object "observation hints" or type info.
2. In desktop/app:
   - Enhance or replace current `LiveMeasurementPreview` with a 3D manim-web scene.
   - Render all objects in world space.
   - When playing observations:
     - For regular 3D targets: use manim-web camera controls (moveTo, lookAt, orbit).
     - For Tape targets: apply tape's world transform + invoke the existing high-fidelity sheet rendering logic projected onto the tape's plane (reuse rich text, math, etc. from current code).
   - Support smooth camera interpolation between mixed targets.
3. Add UI for 3D preview (orbit controls when in free space, "follow tape" button, etc.).
4. Keep a "sheet-only" fallback or mode for pure legacy previews.
5. **Milestone:** Loading a (future) mixed scene in desktop shows correct 3D layout + accurate tape content + camera keyframes that respect tape observation rules. Current pure-sheet projects still preview beautifully.

**Dependencies:** Phases 3 (camera), 6 (measurement), 5 (data).
**Success:** "manim-web powered preview from the very beginning" is now in a real 3D context, solving the 1-1 + gap issues at a deeper level.

## Phase 8: Scene/Render Execution & Existing 3D Features Migration

**Purpose:** Make the Manim runtime use the new model. Migrate current 3D-on-sheet features.

1. Update `CanvasScene` (and `build_mobject`, etc.):
   - Build a world object registry.
   - For each TapeObject: build its local content using existing logic, then place the resulting group at the tape's world transform.
   - General objects built directly in world space.
2. Migrate special 3D behaviors:
   - SolidLift/Rotate/Inspect → general object animations + "inspect" observation mode on the target object.
   - Current tilt → part of tape or 3D object observation.
   - Plot traces, etc. → behaviors attached to objects (still scoped to their local space when appropriate).
3. Camera execution in scene now drives the generalized keyframe system.
4. Keep full backward compat for existing scenes (they implicitly create a default tape at identity).
5. Update reel cutter, export_sheet, etc. to handle world space (or per-tape).
6. **Milestone:** `matemium render` and desktop render produce correct output for migrated scenes. 3D features work in the new unified model.

**Dependencies:** All prior phases.
**Success:** No regression on existing outputs; new 3D capabilities unlocked.

## Phase 9: Builder Ergonomics, Extensibility & Polish

**Purpose:** Make the new model pleasant to use and truly extensible (solving bloat).

1. High-level builder APIs for the 3D world:
   - `add_object(type=..., position=..., relative_to=...)`
   - Context managers or `with builder.in_object_space(id): ...`
   - Helpers for common patterns (e.g., "floating label relative to tape element").
2. Full registration system (build on `register_element_builder`):
   - Register new object kinds with: local build fn, measure fn, observation handler (for camera), preview recipe.
3. Update project templates and `USAGE.md` to show mixed 3D + tape examples.
4. Improve AI chat prompts / shared templates to generate code using the new abstractions.
5. Performance, error messages, docs for relative positioning and observation modes.
6. **Milestone:** Adding a new viz type (e.g. a custom diagram) requires only registering a handler + using it in a project helper — no core patches, works in both sheet and 3D contexts, previews correctly.

**Dependencies:** Phase 8.
**Success:** The engine feels "more granular and abstract" as intended.

## Phase 10: Full Migration, Examples, Tests & Cutover

**Purpose:** Productionize and clean up.

1. Migrate all existing projects/demos to the new model (or keep compat shims + deprecate old paths).
2. Create compelling demo scenes that showcase:
   - Tape floating/rotated in 3D space.
   - Camera moving between 3D solids and tapes.
   - Relative positioning.
   - Mixed content.
3. Comprehensive test suite (unit for transforms/resolution, integration for camera + preview data, render parity tests).
4. Update desktop UI (if needed) for new 3D preview features.
5. Performance tuning, documentation, changelog.
6. Optional: Deprecate old "sheet at z=0 only" assumptions in docs.
7. **Final Milestone:** The 3D world model is the canonical architecture. Current sheet videos continue to be the easiest to author. New 3D capabilities are available without pain.

**Dependencies:** Phase 9.
**Success:** The ideas from the description are reality; future features are easier because of the abstraction.

## Cross-Cutting Concerns & Tooling

- **Testing strategy per phase:** Run existing test suite + render parity + new 3D preview smoke tests. Use `scripts/verify-*.sh` patterns.
- **Desktop / IPC:** All phases must keep `get_preview_data`, `render_project`, etc. working. Extend payload gradually.
- **manim-web specifics:** Coordinate closely with desktop/app changes. The preview player becomes the place where "observation mode" is most visible.
- **AI / Authoring:** Update prompts in `shared/prompts/` and `USAGE.md` as soon as Phase 5 lands.
- **Versioning:** Use feature flags or `canvas_mode` during transition.
- **Documentation updates:** Touch `architecture.md`, `canvas/USAGE.md`, `desktop-architecture.md`, `project-spec.md`, `canvas/README.md` in relevant phases.

## Suggested Ordering & Prioritization

Follow the phases strictly (0 → 10). Within a phase, the numbered steps are intended to be done sequentially where dependencies exist.

Start with Phase 0 + Phase 1 in parallel where possible (audit + modeling).

After Phase 3, the "tape as object + general camera" vision is already demonstrable in preview + a simple scene.

After Phase 7, the manim-web preview is delivering on the "from the very beginning" goal in the new model.

## Open Questions to Resolve During Implementation

- Exact name: `TapeObject`, `SheetObject`, `PlanarTape`?
- How much of the old `CameraMove` / special timeline items to keep as sugar vs. migrate to `CameraObservation`.
- Should free 3D objects also support a limited form of "local styling/layout" or stay explicit?
- Performance model for very large scenes with many tapes/objects.
- How "infinite" the 3D space needs to be vs. bounded for practical math videos.

This plan applies the creative 3D-world ideas to reality in small, verifiable increments while directly addressing abstraction, preview fidelity, renderer independence, and avoiding future patching.

**Next Step Recommendation:** Review this plan, prioritize/adjust phases if needed, then begin Phase 0 (audit + docs). We can create more detailed sub-plans or tickets per phase as we go.

---

*This file is the living implementation roadmap. Update it as phases are completed.*