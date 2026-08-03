# Matemium authoring API

**Current engine specification:** 2026-07-30
**Authority:** current `canvas/` and `matemium/` source plus executable tests

This is the concise, source-aligned reference for authoring projects with the
current Matemium engine. The public documentation site provides task-oriented
guides; [`canvas/USAGE.md`](canvas/USAGE.md) provides longer examples; exact
signatures remain authoritative in [`canvas/builder.py`](canvas/builder.py).

This document describes implemented authoring behavior. Persistent
parent-relative movement, generic traversal, surface-relative positioning, and
arbitrary-surface geodesics are not current API promises. Their possible
design is explicitly open; see
[`SPATIAL_AUTHORING_OPEN_QUESTIONS.md`](SPATIAL_AUTHORING_OPEN_QUESTIONS.md).

## 1. Authoring boundary

The normal project source is visible Python:

```text
project/
├── scenes.py              # visual narrative and timeline
├── helpers.py             # deterministic subject calculations and data
├── brief/                 # description, passport, roadmap, narration, …
└── assets/                # imported media
```

Authors and agents write `scenes.py` with `CanvasBuilder` and `CanvasScene`.
`builder.build()` produces `SheetDSL`, an internal, JSON-serializable compiler
representation. Raw DSL JSON and imperative Manim are debugging or specialist
escape hatches, not the product authoring format.

Subject facts, simulations, graph-layout calculations, chemistry coordinates,
historical source data, and similar logic belong in `helpers.py`. The engine
contains only reusable visual, layout, camera, and timeline abstractions.

## 2. Minimal scene

```python
from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder


# ---DIV: Explanation---
def part_explanation(b: CanvasBuilder) -> None:
    b.add_heading("A structured explanation")
    b.add_body("State the idea in plain language.")
    b.add_math(r"a^2 + b^2 = c^2")


# ---DIV: Main scene---
class Explanation(CanvasScene):
    def __init__(self, **kwargs):
        builder = CanvasBuilder(
            title="Explanation",
            canvas_settings=CanvasSettings.for_reels(title="Explanation"),
        )
        part_explanation(builder)
        super().__init__(dsl=builder.build(), **kwargs)
```

The root tape exists automatically, and ordinary `builder.add_*` calls author
into it. Do not create a second tape merely to obtain a “main” tape. Create
additional tapes only when the narrative genuinely benefits from separate
canvases:

```python
method = builder.add_tape(
    "method",
    frame_width=6.4,
    frame_height=4.8,
)
method.add_heading("Method")
method.add_body("Content authored through this object belongs to that tape.")
builder.scroll_tape(tape_id="method", local_y=0.0)
```

## 3. Stable high-level methods

### Content and composition

| Method | Result | Purpose |
| --- | --- | --- |
| `add_text`, `add_heading`, `add_body`, `add_observation` | builder | Text blocks and semantic typography presets |
| `add_math` | builder | LaTeX content |
| `run` | run dict | Inline text styling |
| `add_concept` | builder | Small title/explanation/formula composition |
| `add_flex_row`, `add_flex_column` | builder | Independently addressable flex items |
| `text_spec`, `math_spec`, `element_spec`, `observation_spec` | spec dict | Flex item specifications |
| `add_tape` | `TapeBuilder` | An isolated, camera-facing 2D presentation canvas |
| `add_data_path` | element ID | Generic sampled path |
| `add_data_plot` | element ID | Generic sampled plot |
| `add_diagram` | element ID | Generic node-edge diagram |

### Timeline and camera

| Method | Result | Purpose |
| --- | --- | --- |
| `add_state_transition` | builder | Synchronized property changes |
| `add_element_morph` | builder | Replace one compiled visual with another |
| `add_camera_focus` | builder | Isolate or overlay focus |
| `add_camera_move` / `auto_camera` | builder | Explicit or suggested root-tape movement |
| `scroll_tape` | builder | Select one foreground tape and move within its local layout |
| `add_camera_keyframe` | builder | Low-level world observation keyframe |
| `observe_object` | builder | World-object observation sugar |
| `add_camera_inspect` | builder | Keyframed 3D inspection |

### 3D and low-level composition

| Method | Result | Purpose |
| --- | --- | --- |
| `add_3d` | builder | Equation-backed mathematical surface |
| `add_solid` | builder | Built-in volumetric solid |
| `add_solid_lift`, `add_solid_rotate` | builder | Solid actions |
| `add_object` | object ID | Registered/free world object with optional stable ID and transform |
| `add_relative` | element ID | Low-level relative placement |
| `add_raw` | builder | Low-level `CanvasElement` or `WorldObject` |

Most content methods are fluent. `add_data_path`, `add_data_plot`,
`add_diagram`, `add_object`, and `add_relative` return IDs because later
actions address them. `add_solid()` is fluent rather than ID-returning: provide
an explicit `id=` when a later lift, rotation, inspection, focus, or transition
must target that solid.

The early grid and quadratic methods remain available for compatibility but are
not current authoring primitives. New work should use generic visuals and
project helpers.

## 4. Generic data visuals

All coordinates must contain two or three finite numbers. Data is sampled and
JSON-compatible by design: helpers can compute it, validation can inspect it,
and alternate renderers can consume it without executing arbitrary callables.

### `DataPath`

```python
trajectory_id = builder.add_data_path(
    [[0, 0], [1, 1.4], [2.2, 0.6], [3, 1.8]],
    id="trajectory",
    smooth=True,
    arrow=True,
    color="#5eb3ff",
    stroke_width=5,
    style={"width": 6.5, "margin-bottom": 0.8},
)
```

Required:

- `points`: at least two 2D or 3D coordinates.

Options:

- `smooth` (default `False`)
- `closed` (default `False`)
- `arrow` (default `False`)
- `color`
- `stroke_width`

Semantic part: `trajectory::path`.

### `DataPlot`

```python
plot_id = builder.add_data_plot(
    [
        {
            "id": "measured",
            "points": [[0, 0], [1, 1.8], [2, 1.2], [3, 2.5]],
            "color": "#5eb3ff",
            "stroke_width": 4,
            "smooth": True,
        },
        {
            "id": "reference",
            "points": [[0, 0.4], [1, 1.0], [2, 1.6], [3, 2.2]],
            "color": "#ff8a65",
        },
    ],
    id="response",
    markers=[
        {"id": "current", "point": [2, 1.2], "color": "#ffdd66", "radius": 0.1}
    ],
    x_range=[0, 3, 1],
    y_range=[0, 3, 1],
    width=7.0,
    height=4.2,
    tips=False,
)
```

Required:

- `series`: a non-empty list.
- Every series has a unique non-empty `id` and at least two finite `points`.

Options:

- Series: `color`, `stroke_width`, `smooth`.
- Markers: unique `id`, `point`, optional `color` and `radius`.
- Plot: `x_range`, `y_range`, `width`, `height`, `tips`, `smooth`.
- Ranges may contain a third step value; their first two values must increase.
- When ranges are omitted, the engine derives padded ranges from the samples.

Semantic parts:

- `response::axes`
- `response::series:measured`
- `response::series:reference`
- `response::marker:current`

### `Diagram`

```python
diagram_id = builder.add_diagram(
    nodes=[
        {
            "id": "sensor",
            "label": "Sensor",
            "position": [-2.5, 0],
            "shape": "rounded",
            "color": "#5eb3ff",
        },
        {
            "id": "controller",
            "label": "Controller",
            "position": [2.5, 0],
            "shape": "rectangle",
            "color": "#8d82ff",
        },
    ],
    edges=[
        {
            "id": "measurement",
            "from": "sensor",
            "to": "controller",
            "label": "measurement",
            "directed": True,
        }
    ],
    id="control_loop",
)
```

Required:

- `nodes`: a non-empty list with unique non-empty IDs.
- Each node has a finite `position` (defaults to `[0, 0]`).
- Each edge has a unique non-empty ID and known `from`/`to` node IDs.

Options:

- Node: `label`, `position`, `shape` (`rounded`, `rectangle`, or `circle`),
  `width`, `height`, `color`, `fill_color`, `fill_opacity`, `font_size`.
- Edge: `label`, `directed`, `buff`, `color`, `stroke_width`, `font_size`.

Node positions are explicit. Automatic graph layout is intentionally a project
helper concern until cross-project evidence supports a stable engine contract.

Semantic parts:

- `control_loop::node:sensor`
- `control_loop::edge:measurement`
- `control_loop::edge-label:measurement` when the edge has a label

## 5. State transitions

`add_state_transition()` changes whole elements or semantic subparts in one
timeline beat:

```python
builder.add_state_transition(
    [
        {
            "target_id": f"{diagram_id}::node:sensor",
            "changes": {
                "fill_color": "#ffdd66",
                "fill_opacity": 0.35,
                "scale": 1.08,
            },
        },
        {
            "target_id": f"{diagram_id}::edge:measurement",
            "changes": {
                "stroke_color": "#ffdd66",
                "stroke_width": 7,
            },
        },
    ],
    run_time=0.8,
    lag_ratio=0.08,
    rate_func="smooth",
)
```

Allowed changes:

| Property | Value |
| --- | --- |
| `color`, `fill_color`, `stroke_color` | Manim-compatible color |
| `fill_opacity`, `stroke_opacity`, `opacity` | finite number |
| `stroke_width`, `scale` | finite number |
| `shift`, `position` | two or three finite numbers |

Unknown target IDs, semantic parts, or properties fail structural validation.
Use state transitions for emphasis, synchronized state, and movement. Use
`ElementMorph` when the visual's compiled content or geometry must be replaced.

## 6. Element morphs

```python
from canvas import CanvasElement

builder.add_element_morph(
    trajectory_id,
    CanvasElement(
        id="trajectory_target",
        type="DataPath",
        content={
            "points": [[0, 0], [1, 0.4], [2, 1.7], [3, 1.0]],
            "smooth": True,
            "color": "#81c784",
            "stroke_width": 5,
        },
    ),
    run_time=1.1,
    match_shapes=False,
)
```

The target passes through the registered build pipeline, is centered on the
source, replaces the registry entry under the source ID, and becomes the
authoritative semantic-part structure for later actions. Its type and content
are validated before render. Set `match_shapes=True` only when matching
subgeometry is appropriate.

## 7. Validation and checking

`CanvasScene` performs strict structural validation by default before Manim
setup. The desktop `check_project` path imports the scene, constructs its DSL,
and returns structured diagnostics without requiring a full render.

Validation covers, among other things:

- duplicate IDs and unknown targets;
- registered content schemas;
- malformed or non-finite data;
- diagram endpoints and semantic-part references;
- state-property names and values;
- morph target kind and content.

`strict_validation=False` is an explicit checker/debugging escape hatch. It
must not be used to make an invalid production scene render.

Unknown element kinds currently produce a warning rather than an error. That is
an extensibility compatibility behavior, not proof that an unknown kind can
render. Production projects should use registered kinds and resolve warnings.

Structural success is not visual acceptance. Authoring still requires preview
rendering, inspection of actual frames/video, domain review, and repair.

## 8. Capability maturity

Use this matrix when choosing an authoring method:

| Tier | Current methods | Meaning |
| --- | --- | --- |
| Production authoring | root-tape text/math, rich runs, block style, flex, `DataPath`, `DataPlot`, `Diagram`, `StateTransition`, `ElementMorph`, focus, portrait/landscape settings | Implemented, exercised by tests and real project renders |
| Specialized but usable | equation-backed surfaces, `Solid3D`, solid lift/rotation/inspection, static full-sheet export, legacy grid/quadratic helpers | Implemented; requires target-orientation preview evidence |
| Production spatial composition | additional camera-facing tapes, automatic curtain switching, explicit `scroll_tape`, `add_object`, stable-ID world morphs, `add_camera_inspect` | Exercised by the orbital flagship and engine tests |
| Experimental | `add_world_object`, low-level `add_camera_keyframe`, `observe_object`, relative world placement | Structural support exists, but composition ergonomics still require preview evidence |
| Not a current contract | arbitrary physical tape transforms or simultaneous visible tapes; generic timed traversal of `DataPath`/`DataPlot`; reactive bindings/shared clocks; timed audio/media; automatic domain-specific layouts | Do not advertise or fake these with lesson-specific engine patches |

The tape/world boundary is deliberate. A selected tape fills the presentation
context and hides the free world and every other tape. Selecting another tape
replaces it; inspecting a world object opens it. This prevents unreadable
compositing and keeps analytical text camera-facing.

The boundary is an opacity fade around a camera cut, not a camera move. On a
tape-to-world inspect path, the first authored shot is the cut destination;
subsequent shots remain available for purposeful movement within the world.

The generic visuals are sampled and static between timeline actions. Use
`StateTransition` and `ElementMorph` for staged changes. They do not yet share a
reactive clock with a simulation or offer a generic trace cursor.

## 9. Exact return-value and targeting notes

- `add_text`, `add_heading`, `add_body`, `add_math`, flex methods, state/morph
  actions, camera actions, `add_3d`, and `add_solid` return `CanvasBuilder`.
- `add_data_path`, `add_data_plot`, `add_diagram`, `add_grid_board`,
  `add_quadratic_plot`, `add_quadratic_compare`, `add_object`,
  `add_world_object`, and `add_relative` return an ID string.
- `add_tape` returns `TapeBuilder`; `run` and the `*_spec` helpers return
  serializable dictionaries.
- `last_flex_ids` returns a copy of the IDs created by the latest flex
  row/column.
- State/morph/focus targets must already identify an element in the compiled
  DSL. For compound visuals, use `element_id::semantic-part`.

## 10. Render profiles and orientation

`CanvasSettings.for_reels()` is 9:16 at 1080×1920.  
`CanvasSettings.for_youtube()` is 16:9 at 1920×1080.

CLI/sidecar quality profiles preserve the scene aspect ratio:

| Profile | Resolution scale | Frame rate |
| --- | ---: | ---: |
| `preview` | 0.50 | 15 fps |
| `draft` | 0.75 | 30 fps |
| `low` | 1.00 | 30 fps |
| `medium` | 1.00 | 30 fps |
| `high` | 1.00 | 60 fps |
| `final` | 1.00 | 60 fps |

An explicit `-r WIDTH,HEIGHT` overrides pixel dimensions. It does not
automatically recompose layout; author and inspect each intended orientation.

## 11. Engine extension contract

Registered visual kinds use the shared measure/build registry. A reusable kind
may provide:

- `build`: construct its Manim object;
- `measure`: return layout dimensions;
- `validate(content)`: pure structural validation;
- `parts(content)`: declared semantic-part IDs.

New product capabilities must be reachable through `CanvasBuilder`, remain
serializable where they enter `SheetDSL`, and be justified by needs shared
across unrelated projects. See
[`REAL_PROJECT_ENGINE_WORKFLOW_PROMPT.md`](REAL_PROJECT_ENGINE_WORKFLOW_PROMPT.md)
and [`ENGINE_ABSTRACTION_PLAN.md`](ENGINE_ABSTRACTION_PLAN.md).

## 12. Source-of-truth order

When documents disagree, use this order:

1. Current executable source and tests.
2. This file and the public `docs/` reference.
3. `canvas/USAGE.md` task examples.
4. Architecture/status documents.
5. Phase plans, TODOs, and historical implementation records.

Plans describe intent and history. They are not proof that an author-facing
method works.
