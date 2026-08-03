# Using Matemium

Write **plain, short Python** in `scenes.py` and get correctly laid-out
structured visual explanations plus full-tape study exports. Matemium began with
mathematics but the same public API supports any subject built from staged text,
math, paths, plots, diagrams, state, morphs, and spatial reasoning. In the
**desktop app**, AI edits this same source — it does not emit Sheet DSL JSON.

## Philosophy: tool first, scenes second

Matemium is a **compiler** (layout + timeline + camera + styling), not a bag of lesson-specific helpers. Projects under `projects/` are test videos and real content; they should **compose** the engine, not extend `canvas/builder.py` with topic methods.

**How to compose lessons (no extra packages):**

1. `style={...}` on generic `add_*` methods (CSS-like margins, width, wrap, align)
2. `add_flex_row` / `add_flex_column` with `text_spec`, `math_spec`, …
3. `add_camera_focus` for isolate-zoom or overlay magnifier
4. Topic-specific patterns → plain functions in `projects/<name>/helpers.py` (or `projects/_lib/` if shared)

There is **no** `canvas/extensions/` package. This extended guide and the
source-aligned [`../AUTHORING_API.md`](../AUTHORING_API.md) define the public
authoring contract. Exact signatures remain authoritative in `builder.py`.

See `architecture.md` §6 and `project-spec.md` for the full layer model.

## Recommended way: CanvasBuilder

```python
from canvas.builder import CanvasBuilder
from canvas import CanvasScene
# from scripts.legacy.render import render_sheet   # deprecated; use manim or matemium CLI directly

builder = CanvasBuilder(title="Solving x^2 - 5x + 6 = 0")

builder.add_text("Problem: Factor the quadratic", after_3d=False)
builder.add_math(r"x^2 - 5x + 6 = 0")

builder.add_camera_move(dy=3.5)

builder.add_observation("We look for two numbers that multiply to 6 and add to -5.")

builder.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")

builder.add_3d("z = x^2 - y^2")

builder.add_text("Conclusion: the solutions are x=2 or x=3", after_3d=True)

dsl = builder.build()
scene = CanvasScene(dsl=dsl)
```

Run it:

```bash
./matemium.sh demo                    # built-in test → outputs/demo/
./matemium.sh render my_video         # your project → outputs/my_video/
./matemium.sh new my_video            # scaffold projects/my_video/
```

### Why this is better than raw JSON / manual positions

- Automatic vertical layout with smart spacing (extra room after 3D elements).
- Good defaults for entry animations, 3D rotation, and static poses for screenshots.
- You write content, not pixel-perfect Y coordinates.
- Override everything when needed via `add_raw`, explicit positions, or styles.

### Core API (engine — use these in new projects)

**Content**

- `add_text("...")` / `add_text(..., style={...})`
- `add_text([...])` — inline styled runs (letter / word / phrase granularity)
- `builder.run("word", color=..., highlight=True)` — one styled run
- `add_math(r"latex here")`
- `add_3d("z = x^2 - y^2")`
- `add_heading("...")` / `add_body("...")` — typography presets (wrap defaults); also accept run lists
- `add_observation("...")` / `add_concept(title, explanation, formula?)` — thin aliases
- `add_data_path(points, ...)` — sampled trajectory, contour, route, or vector
- `add_data_plot(series, markers=..., ...)` — arbitrary named sampled series
- `add_diagram(nodes, edges, ...)` — semantic node-edge diagrams with explicit local positions

**State and morphing**

- `add_state_transition(patches, ...)` — change several elements or semantic parts in one beat
- `add_element_morph(element_id, target, ...)` — replace geometry/content through the normal compiler
- Address compound parts as `element_id::node:id`, `::edge:id`, `::series:id`,
  `::marker:id`, or `::path`.

```python
graph = tape.add_diagram(
    nodes=[
        {"id": "source", "label": "Source", "position": [-3, 0]},
        {"id": "sink", "label": "Sink", "position": [3, 0]},
    ],
    edges=[{"id": "flow", "from": "source", "to": "sink", "label": "signal"}],
    id="system",
)
builder.add_state_transition([
    {"target_id": f"{graph}::node:source", "changes": {"color": "#ffdd66"}},
    {"target_id": f"{graph}::edge:flow", "changes": {"stroke_width": 7}},
])
```

Generic visuals use sampled JSON-compatible data. Domain calculations and layout algorithms remain in
project helpers; the engine compiles their output deterministically.

Required contracts:

- `DataPath.points`: at least two finite 2D/3D points. Options include
  `smooth`, `closed`, `arrow`, `color`, and `stroke_width`.
- Every `DataPlot` series has a unique `id` and at least two finite `points`.
  Markers have unique IDs and finite points.
- Every `Diagram` node and edge has a unique ID; edge endpoints name existing
  nodes. Node positions are explicit and specialized layout remains a helper.
- Semantic parts include `path`, `axes`, `series:<id>`, `marker:<id>`,
  `node:<id>`, `edge:<id>`, and `edge-label:<id>`.
- State changes are limited to color, fill/stroke color and opacity,
  `stroke_width`, `opacity`, `scale`, `shift`, and `position`.
- `ElementMorph` accepts a target `CanvasElement`; its kind/content are
  validated and its semantic parts replace the previous part map.

**Layout & composition**

- `add_tape("name")` — create a secondary tape; returns a `TapeBuilder`
- `tape.add_heading(...)`, `tape.add_body(...)`, `tape.add_math(...)`, etc. — author directly into that tape
- `add_flex_row([...], gap=..., justify_content=..., align_items=...)`
- `add_flex_column([...], gap=...)`
- **Each flex item is its own timeline element** (separate id, individual `add_camera_focus`)
- `builder.last_flex_ids` — ids just placed by the latest flex row/column
- `element_spec(CanvasElement(...))` — any custom element in a flex row (topic code uses this from project `helpers.py`)
- `text_spec`, `math_spec`, `observation_spec` — flex item dicts

The root tape exists automatically and remains the simplest production path.
Additional tapes retain independent local layout. At runtime exactly one tape
is presented face-on; it is not placed or rotated in the free 3D world.

**Camera & focus**

- **Sheet model:** content sits on the XY plane at `z = 0`; scroll pans Y; zoom crops the frame on that plane
- Auto-focus on element reveal (default) — new content centers in the viewport
- `add_camera_focus(element_id, mode="isolate"|"overlay", zoom=..., ...)` — focus tool; isolate **caps** zoom so the target stays fully inside the viewport (never clips borders)
- 3D graphs optionally **tilt** the camera; flat content does not force a “2D mode” switch each time
- `add_camera_move(dy=...)` / `auto_camera()` — explicit scroll when needed

**Tape and 3D world model**

The public tape API creates isolated 2D layout contexts. Root-tape reveal
activates classic local scroll, lazy reveal, focus, and flex behavior.
When content from a tape becomes active, that tape closes over the current
camera like a curtain:

- world → tape: free-world objects disappear and the tape becomes readable;
- tape → tape: the new tape replaces the previous foreground tape;
- tape → world: the tape opens and only free-world objects are restored.

Context changes use a short opacity fade around an instantaneous camera cut.
Camera position, angle, and zoom never interpolate between tape and world
coordinate systems. Once the world is visible, later keyframes in the same
`add_camera_inspect()` path may animate normally.

Tapes do not accept `position`, `rotation`, or `scale`. Use `scroll_tape()` for
an explicit tape selection/local-Y move; ordinary tape-element reveal also
switches contexts automatically.

Free 3D objects use `add_object()` / `add_world_object()` and explicit
observation. `add_object(..., id=...)` preserves a stable author-selected ID.

Authoring examples:

- `add_object("Solid3D", position=(x,y,z), ...)`
- `analysis = add_tape("analysis", frame_width=6.4, frame_height=4.8)`
- use `scroll_tape(tape_id="analysis", local_y=...)` for an explicit switch
- author with `analysis.add_body(...)`; small solids can also be embedded with
  `analysis.add_solid(...)`
- return to free 3D with `observe_object(...)`, `add_camera_keyframe(...)`, or
  `add_camera_inspect(...)`

`add_solid_lift(...)` is specifically for raising 3D solids above a tape for orbit/inspection. Do not use it as a tape switching or tape stacking mechanism.

See `3D-WORLD-DESCRIPTION.md` and `3D-model.md` as design records, not as a
guarantee that every described world-camera behavior is implemented.

**Escape hatch**

- `add_raw(CanvasElement(...))` — full DSL control

Most ordinary content/layout/action methods are chainable. Return values are
intentionally mixed:

- `add_data_path`, `add_data_plot`, `add_diagram`, `add_object`, and
  `add_relative` return stable ID strings;
- `add_tape` returns a `TapeBuilder`;
- `run` and `*_spec` helpers return dictionaries;
- text, flex, camera, state, morph, and solid actions return the builder.

`add_solid()` is therefore chainable rather than ID-returning. Give it an
explicit `id=` if later actions need a target.

### Project helpers (topic code — not engine API)

Lesson-specific logic lives **next to the video**, not under `canvas/`:

```
projects/my_lesson/
├── scenes.py      # narrative — imports core CanvasBuilder only
└── helpers.py     # optional — add_compare_pair(builder, ...), etc.
```

```python
# projects/quadratic_graphs/helpers.py
def add_compare_pair(builder, left_tex, right_tex, **style):
    builder.add_flex_row([
        builder.math_spec(left_tex, style={"width": 3.0}),
        builder.math_spec(right_tex, style={"width": 3.0}),
    ], gap=0.6, **style)
    return builder
```

For new lessons: **core + `style={}` + project helpers**. Do not add topic methods to `CanvasBuilder`.

### Legacy builder methods (transitional — will move to project helpers)

These still exist on `CanvasBuilder` from early test scenes. Prefer project helpers or core composition in new code:

| API | Use case | Planned home |
|-----|----------|--------------|
| `add_grid_board`, `add_grid_moves`, `grid_board_spec` | Board games (tic-tac-toe) | `projects/demo/helpers.py` |
| `add_quadratic_plot`, `add_quadratic_compare`, `add_plot_trace`, `quad_plot_spec` | Quadratic graphs | `projects/quadratic_graphs/helpers.py` |

### Full tape static export

```python
scene = builder.to_scene()
scene.export_full_sheet("my_reasoning", full_tape=True, format="png")
```

`full_tape=True` exports the entire written tape in its natural shape (no forced
9:16 or 16:9 crop). The exporter rebuilds the tape in local document
coordinates, so the video camera and any world/camera rotation cannot flip,
offset, or stretch the result. For projects containing more than one populated
tape, select one explicitly:

```python
scene.export_full_sheet(
    "worked_solution",
    full_tape=True,
    tape_id="main",
    format="png",
)
```

Without `high_res_height`, export density follows the canvas's native pixels per
logical unit. Long tapes are rendered in tiles and stitched at that consistent
resolution. Pass `high_res_height=2160` when an exact final image height is
preferred.

### Mixing with raw control

```python
from canvas import CanvasElement

builder.add_raw(CanvasElement(type=..., canvas_position=...))
```

Or use `SheetDSL` + `CanvasElement` directly for low-level control.

### Desktop AI chat (system prompt reference)

When integrated via chat APIs, the model edits **`scenes.py`** — the same file the user sees. Guidelines:

- Prefer **top-level `part_*` functions** for lesson sections; wire them in a thin `CanvasScene.__init__`.
- Use `# ---DIV: Section title---` comments before each top-level `def` or `class` for section-aware editing.
- Generate `builder.add_xxx(...)` calls inside section functions.
- Use `after_3d=True` on text that follows 3D graphics.
- Let the builder handle IDs and positions.
- End with `super().__init__(dsl=builder.build(), **kwargs)` in the scene class.
- Do **not** emit Sheet DSL JSON or raw Manim as the primary output.

### Tips for human / dev authoring

- Split lessons into `part_*` functions + `# ---DIV: ...---` markers (matches desktop editor UX).
- Keep one `scenes.py` per project in v1; use `projects/<name>/helpers.py` in the dev repo when needed.

### Running

```bash
./matemium.sh demo
./matemium.sh list
./matemium.sh --help
```

Author videos in `projects/<name>/scenes.py`. Outputs go to `outputs/<name>/media/`.

### JSON / raw DSL (internal & debugging only)

`SheetDSL.from_file("path/to/sheet.json")` and inline-`dsl` sidecar IPC are for **tests, fixtures, and engine debugging**. Product authoring (desktop and dev) uses **`CanvasBuilder` in `scenes.py`**.

### Strict structural validation

`CanvasScene(dsl)` validates before Manim setup and raises on structural errors
by default. Desktop `check_project` returns the same class of DSL issues as
structured diagnostics. Registered visual schemas, semantic targets, state
properties, and morph targets are checked before render.

`strict_validation=False` is a checker/debugging escape hatch only. A clean
structural check does not replace preview rendering, visual inspection, or
domain review.

### Layout foundation

Layout is resolved by `LayoutEngine` into a typed `LayoutBox` on each element
(width, height, wrap, align, margins). Content stays pure; the scene reads
`element.layout` via the shared `measure.py` pipeline.

Semantic helpers (preferred over guessing wrap behavior):

```python
builder.add_heading("Chapter 1")          # short title, scale-to-fit
builder.add_body("Long explanation...")   # wraps at safe viewport width
builder.add_observation("We notice...")   # alias for add_body
```

Explicit control:

```python
builder.add_text("Label", style={"wrap": False, "align": "left"})
builder.add_text("Notes...", style={"wrap": True, "margin-bottom": 1.2})
builder.auto_camera()  # scroll when content exceeds ~65% of viewport
```

### Inline text runs (letter / word / phrase)

Use a **list** instead of a string when part of the text needs different color or highlight.
Each item is plain text or a styled run. Granularity is your choice: one letter, one word, or a phrase.

```python
# Letter-level — color one symbol in a formula mention
builder.add_text([
    "Evaluate ",
    builder.run("f", color="#aaaaaa"),
    builder.run("(", color="#aaaaaa"),
    builder.run("x", color="#5eb3ff"),
    builder.run(")", color="#aaaaaa"),
    " at ",
    builder.run("x", color="#5eb3ff", highlight=True),
    " = 2.",
])

# Word-level — highlight a vocabulary term
builder.add_body([
    "A ",
    builder.run("quadratic", color="#ffdd66", highlight=True),
    " has the form ",
    builder.run("ax² + bx + c", color="#cccccc"),
    ".",
])
```

Per-run style keys: `color`, `highlight` (`True` or a fill color), `font_size`, `bold`, `italic`, `underline`, `opacity`.

Block-level `style={}` still controls margins, width, and wrap for the whole line or paragraph.

### CSS-like styling (block level)

All `add_*` methods accept `style={...}` with border-box sizing by default:

- `margin`, `margin-top`, `margin-bottom`, `margin-left`, `margin-right`
- `width`, `height`
- `wrap`: `true` / `false` (explicit; otherwise inferred for plain `add_text`)
- `align` or `text-align`: `"left"` | `"center"` | `"right"`

```python
builder.add_math(r"E = mc^2", style={"margin": "0.5 0 1.5 0", "width": 5.0})
```

### Grids and board games (legacy builder API — transitional)

```python
# Standalone grid in vertical flow
board_id = builder.add_grid_board(rows=3, cols=3, cell_size=1.0, id="board")
builder.add_grid_moves("board", [("X", 1, 1), ("O", 0, 0), ("X", 2, 2)])

# Grid inside a flex row (side-by-side with text)
builder.add_flex_row([
    builder.grid_board_spec(rows=3, cols=3, id="ttt", style={"width": 2.8}),
    builder.text_spec("Commentary...", style={"width": 3.2, "wrap": True}),
], gap=0.8)
builder.add_grid_moves("ttt", [("X", 1, 1), ("O", 0, 0)])
```

Render the demo: `./matemium.sh demo tictactoe`

### Flexbox

```python
builder.add_flex_row(
    [
        builder.text_spec("We have: ", style={"align": "right"}),
        builder.math_spec(r"f(x) = x^2", style={"width": 3.5}),
    ],
    gap=0.6,
    justify_content="start",
    align_items="center",
    style={"margin-bottom": 1.5},
)
```

See also:

- `canvas/dsl.py` — underlying data model
- `canvas/scene.py` — render engine
- `project-spec.md` — vision and status
