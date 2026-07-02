# Using Matemium

Write **plain, short Python** in `scenes.py` and get correctly laid-out math animation videos plus full-sheet study exports. In the **desktop app**, AI chat edits this same file on your behalf — it does not emit Sheet DSL JSON.

## Philosophy: tool first, scenes second

Matemium is a **compiler** (layout + timeline + camera + styling), not a bag of lesson-specific helpers. Projects under `projects/` are test videos and real content; they should **compose** the engine, not extend `canvas/builder.py` with topic methods.

**How to compose lessons (no extra packages):**

1. `style={...}` on generic `add_*` methods (CSS-like margins, width, wrap, align)
2. `add_flex_row` / `add_flex_column` with `text_spec`, `math_spec`, …
3. `add_camera_focus` for isolate-zoom or overlay magnifier
4. Topic-specific patterns → plain functions in `projects/<name>/helpers.py` (or `projects/_lib/` if shared)

There is **no** `canvas/extensions/` package. Only `canvas/USAGE.md` (this file) documents the engine API that AIs and authors should memorize.

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

**Layout & composition**

- `add_flex_row([...], gap=..., justify_content=..., align_items=...)`
- `add_flex_column([...], gap=...)`
- **Each flex item is its own timeline element** (separate id, individual `add_camera_focus`)
- `builder.last_flex_ids` — ids just placed by the latest flex row/column
- `element_spec(CanvasElement(...))` — any custom element in a flex row (topic code uses this from project `helpers.py`)
- `text_spec`, `math_spec`, `observation_spec` — flex item dicts

**Camera & focus**

- **Sheet model:** content sits on the XY plane at `z = 0`; scroll pans Y; zoom crops the frame on that plane
- Auto-focus on element reveal (default) — new content centers in the viewport
- `add_camera_focus(element_id, mode="isolate"|"overlay", zoom=..., ...)` — focus tool; isolate **caps** zoom so the target stays fully inside the viewport (never clips borders)
- 3D graphs optionally **tilt** the camera; flat content does not force a “2D mode” switch each time
- `add_camera_move(dy=...)` / `auto_camera()` — explicit scroll when needed

**3D world model (Clarified)**

The "sheet" is a `TapeObject` — one special object inside the infinite 3D world. 

**Default behavior:** Any object, including a TapeObject, can be observed with normal cinematic 3D (via `ObjectAnchor`). The tape acts like a movable/rotatable plane in 3D space. Free 3D objects do **not** get internal tape features.

**Tape-scroll-mode:** Only a `TapeScroll(...)` target activates the tape's classic internal behaviors (local scroll using its internal measurements, lazy reveal, focus, flex, etc.). The outer camera still uses the tape's world transform.

Old pure-tape videos continue to work exactly as before (they implicitly use tape-scroll-mode on the root tape).

Authoring examples:
- `add_object("Solid3D", position=(x,y,z), ...)`
- `set_tape_pose(rotation=(30,0,0))`
- `add_camera_keyframe(target=ObjectAnchor("my_tape"))`          # 3D view of the tape plane
- `add_camera_keyframe(target=TapeScroll("root_tape", local_y=5))` # enter classic tape scroll + reveal

See `3D-WORLD-DESCRIPTION.md` for the mental model.

See 3D-model.md for full details.

**Escape hatch**

- `add_raw(CanvasElement(...))` — full DSL control

All methods are chainable.

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

`full_tape=True` exports the entire written tape in its natural shape (no forced 9:16 or 16:9 crop).

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