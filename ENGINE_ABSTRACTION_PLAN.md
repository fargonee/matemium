# Engine abstraction plan from the eleven flagship authoring passes

Status: **implemented and verified on 2026-07-27**

This plan is based on the authored sources and `AUTHORING_FEEDBACK.md` files in all eleven flagship
project folders. The planned injection is now implemented in `canvas/generic_visuals.py`, `canvas/dsl.py`,
`canvas/builder.py`, and `canvas/scene.py`. It deliberately does not promise to make those first-pass
projects flagship renders; reauthoring them after the engine change remains a separate task.

## 1. Evidence distilled across subjects

| General need | Independent project evidence |
| --- | --- |
| Data-backed path and plot geometry | Fourier, orbit, SN2, feedback, economics, water |
| Semantic nodes and routed relationships | Dijkstra, feedback, economics, history, philosophy, language, water |
| Stable identity for visual subparts | all 11; especially nodes, tokens, codons, blocks, curves, planks |
| One transition changing several views together | Fourier, SN2, Dijkstra, feedback, economics, biology, history, language, water |
| Replace/morph one visual state into another | SN2, economics, biology, philosophy, language |
| Nested scale/camera navigation | orbit, biology, history, philosophy, water |
| Timed external media | language (audio), later website/demo production |

The first five needs recur often enough and are sufficiently bounded to promote now. Nested world-camera
work and timed media are not safe to redesign in the same injection: their existing contracts are
unfinished and they require dedicated runtime/packaging evidence. They remain explicit follow-up seams,
not silent omissions.

## 2. Chosen core model

### 2.1 Three generic visual kinds

1. **`DataPath`** — points in local coordinates, optional smoothing/closure/arrows, stable semantic id.
   It represents a trajectory, flow route, contour, vector, or boundary without knowing the subject.
2. **`DataPlot`** — axes plus one or more named sampled series and named markers. It accepts data, not a
   Python callable, so DSL serialization, deterministic rendering, desktop inspection, and security remain
   straightforward.
3. **`Diagram`** — named nodes at explicit local positions plus named edges. Nodes expose label, shape,
   size, and style; edges expose endpoints, direction, label, and style. Layout algorithms remain project
   helpers initially. This avoids hiding domain choices inside an unstable automatic layout engine.

Every builder attaches a semantic part registry to its root Manim group:

```text
element-id
├── node:<id> / edge:<id>
├── series:<id> / marker:<id>
└── path
```

Timeline actions address these as `element_id::part_id`. The delimiter and lookup are engine-level;
domain names remain project data.

### 2.2 Two generic timeline actions

1. **`StateTransition`** applies an ordered collection of style/geometry patches in one `play` call.
   Supported properties are intentionally closed: color, fill/stroke color and opacity, stroke width,
   opacity, scale, shift, and absolute position. Unknown properties fail validation rather than being
   silently ignored.
2. **`ElementMorph`** rebuilds a target `CanvasElement` through the same registered measure/render pipeline
   and transforms the existing registry object into it. It is for content/geometry replacement; state
   patches remain the cheaper path for emphasis and movement.

These actions are generic. Dijkstra events, codon indices, reaction progress, or a historical date remain
project-generated data.

## 3. Public authoring API

`CanvasBuilder` gains only structural methods:

- `add_data_path(points, ...)`
- `add_data_plot(series, ...)`
- `add_diagram(nodes, edges, ...)`
- `add_state_transition(patches, ...)`
- `add_element_morph(element_id, target, ...)`

`TapeBuilder` forwards the three element methods and both timeline methods. Advanced authors can construct
the dataclasses directly. No subject noun appears in the core API.

## 4. Validation and failure behavior

- Object-kind registration gains an optional pure `validate(content)` callback.
- `SheetDSL.validate()` calls registered validators and reports `invalid_element_content`.
- Duplicate semantic part ids, missing edge endpoints, malformed/non-finite point coordinates, invalid
  ranges, and empty series fail before render.
- Timeline validation resolves `element_id::part_id` against the owning element’s declared semantic ids.
- Patch properties are allowlisted and numeric/vector forms are checked.
- `CanvasScene` raises structured `TimelineExecutionError` if a target disappears at runtime.
- Existing unknown-kind placeholder behavior remains for backward compatibility, but the new built-ins do
  not use it.

## 5. Compatibility and injection safety

1. Additive DSL dataclasses and object-kind registrations; no existing field changes.
2. `SheetDSL.from_dict()` and `to_dict()` round-trip new kinds/actions while old JSON remains unchanged.
3. Existing `TransformElement`, quadratic plot, grid, solid, camera, and tape behavior remains available.
4. New render code lives in one leaf module and is registered from `measure.py`; scene dispatch receives
   only the two new generic actions.
5. Unit tests cover schemas, rendering construction, semantic addressing, serialization, builder output,
   and action dispatch before broad tests run.
6. No flagship-specific source is imported by `canvas/`; dependency direction remains projects → engine.

Rollback is localized: remove the new registrations/actions and their exports. Existing serialized projects
and engine behavior are unaffected.

## 6. Efficiency choices

- Sampled data rather than runtime callables gives one representation to Python, JSON, desktop preview,
  deterministic tests, and future alternate renderers.
- One `Diagram` schema replaces separate graph, block-diagram, argument-map, dependency-tree, process-flow,
  and causal-network primitives.
- One semantic part protocol works across all registered compound objects.
- One batched `StateTransition` avoids eleven topic event types and minimizes Manim `play` calls.
- Explicit node positions defer automatic layout until real examples establish its requirements; projects
  may use NetworkX or plain helper calculations without coupling it to core.

## 7. Explicit non-goals for this mutation

- Reauthoring the eleven projects to use the new API.
- Claiming visual or production acceptance for their first authoring passes.
- Shipping an automatic graph-layout algorithm.
- Redesigning the unfinished 3D camera/world model.
- Adding audio download, playback, or packaging.
- Removing legacy quadratic/grid APIs in the same change.

## 8. Completion gates

Implementation is complete only when:

1. all five abstractions above exist in Python and serialized DSL;
2. invalid generic content/actions are rejected before render;
3. compound parts can be addressed by stable semantic id;
4. builder and direct-DSL paths are tested;
5. existing engine behavior remains green;
6. the entire repository Python test suite passes (with documented environmental exclusions only if a
   test is intrinsically unavailable);
7. formatting/diff checks show no accidental damage.

## 9. Implementation result

All five planned abstractions are public through `CanvasBuilder` and
`TapeBuilder`. Registered kinds provide build, measurement, content validation,
and semantic-part declaration. `SheetDSL` round-trips both new actions,
`CanvasScene` dispatches them, and strict structural validation runs before
render by default.

The implementation additionally:

- exposes labeled diagram edges as `edge-label:<id>` without conflating the
  label with the addressable edge geometry;
- reports DSL diagnostics through the workspace `check_project` path;
- preserves a morphed element's original registry ID while replacing its
  semantic-part map;
- fixes root-timeline placement so identity `WorldTransform` does not override
  normal tape-flow placement.

Verification completed with the full Python suite, explicit slow Manim render
tests, Rust tests, the desktop web build, focused linting of new authoring
surfaces, format checks, and real visual smoke renders. Exact user-facing
contracts are documented in [`AUTHORING_API.md`](AUTHORING_API.md).
