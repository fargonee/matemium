
# SYSTEM PROMPT & ARCHITECTURE SPECIFICATION: PROJECT MATEMIUM

## 1. Project Vision
"Matemium" is a proprietary layout-to-animation compiler built on top of the Manim Community Edition (Python). It shifts the Manim paradigm from a "code-driven sequence of scenes" to an "infinite, vertically scrollable learning sheet." The output engine splits a single long-form canvas into micro-dose 9:16 vertical chunks suitable for social media short-form reels.

## 2. Core Architectural Paradigm

The root is one **infinite 3D space** (XZ ground, Y up by convention). The legacy "infinite sheet" is a special `TapeObject` inside that space.

- **The sheet:** The infinite tape is the **XY plane at `z = 0`**. Text, math, plots, and anchored 3D graphs live here by default.
- **Z axis:** Depth — grid marks lifted slightly above the sheet, optional explicit `z` on elements, future camera dolly. Not a separate “2D mode.”
- **The viewport:** A 9:16 frame whose center pans along `(x, y, 0)` down the sheet.
- **The elements:** Stateless components anchored at `(x, y, z)` canvas coordinates.
- **The engine:** Scrolls the camera on the sheet; zoom crops the frame on the plane; optional **tilt** only for 3D surface moments.

**Canonical model (clarified model — see `3D-WORLD-DESCRIPTION.md`):**

The root is one **infinite 3D space** (XZ ground / Y up). The legacy "tape/sheet" is a special `TapeObject` inside the world.

**Clarified observation model:**
- Every object (tapes included) is observed by default with normal cinematic 3D behavior (look-at, orbit, follow transforms).
- Free 3D objects do not get tape-like features.
- `TapeScroll` target (tape-scroll-mode) is the only way to activate a tape's internal 2D mechanisms: local-coordinate scroll, lazy reveal driven by local progress, sheet focus/layout logic.
- The outer camera always respects a tape's `world_transform`, even in scroll mode.
- Classic tape videos continue to work identically when authored the old way (they use tape-scroll-mode under the hood on the default root tape).

See `3D-WORLD-DESCRIPTION.md` and `canvas/3D-model.md` for the full model, terminology, and current status. Architecture and camera implementation still need work to fully realize the separation between normal 3D observation and tape-scroll-mode.

## 3. Data Schema (The Sheet DSL)
Claude, we will not write pure Manim scripts directly. We will build a JSON/YAML-based layout specification (or a lightweight Python DSL) that compiles into a Manim scene. 

An example data representation you must support:

```json
{
  "canvas_settings": { "default_width": 9, "default_height": 16 },
  "timeline": [
    {
      "id": "element_01",
      "type": "MathTex",
      "content": "\\nabla \\times \\vec{E} = -\\frac{\\partial \\vec{B}}{\\partial t}",
      "canvas_position": [0, 0, 0],
      "entry_animation": { "type": "Write", "run_time": 1.5 }
    },
    {
      "id": "viewport_scroll_1",
      "type": "CameraMove",
      "target_position": [0, -10, 0],
      "run_time": 2.0,
      "rate_func": "smooth"
    },
    {
      "id": "element_02",
      "type": "ThreeDGraph",
      "equation": "z = x^2 - y^2",
      "canvas_position": [0, -10, 0],
      "entry_animation": { "type": "FadeIn", "run_time": 1.0 },
      "state_behaviors": { "idle": "rotate_slowly", "axis_pitch": 45 }
    },
    {
      "id": "reanimate_01",
      "type": "TransformElement",
      "source_id": "element_01",
      "target_position": [0, -12, 0],
      "action": "FlashAndScale",
      "scale_factor": 1.2
    }
  ]
}
````

4. Key Engineering Modules to Build
We will build this system modularly. Prepare to build the following components:
Phase 1: The Camera Tracker Override
We use ``ThreeDScene`` with a **sheet-first camera** (`canvas/camera.py`). Scroll = pan on the `z = 0` plane. Zoom = frame crop on that plane (reliable for flat content). Perspective **tilt** is optional for `ThreeDGraph` / `Surface` reveals — not toggled on every text block. Avoid fighting `ThreeDCamera.zoom_tracker` for tape content.
Phase 2: Persistent State & "Re-animation" Engine
Standard Manim garbage-collects or drops tracking of elements if they aren't explicitly inside the current view. We need an object dictionary (self.canvas_registry) that holds references to all rendered Mobjects.

* If an element from 3 scrolls up is needed again, the system must reference its pointer in self.canvas_registry and animate it down to the current camera viewport without redefining it.

* Idle Loops: Support background processes (updaters) so that elements left behind continue a low-compute operational loop (e.g., oscillating vector fields).

Phase 3: Automated Micro-Chunker (The Reel Cutter)
A script that maps the length of the long-form sheet and automatically calculates safe render chunks based on CameraMove markers, slicing them into discrete 60-second .mp4 vertical videos.
5. Development Strategy

1. We will start by building the Python parser that maps the JSON/DSL specification into valid Manim instructions.

2. We will implement the continuous camera tracking physics.

3. We will handle the 2D to 3D matrix blending.

## Design goals

- **Code-first authoring (product):** Lessons are `scenes.py` using `CanvasBuilder`, not raw Manim. Compiled `SheetDSL` is internal IR.
- **Persistent infinite tape:** Elements stay anchored; the camera scrolls through them.
- **Social output:** Long-form sheets can be chunked into 9:16 vertical reels.
- **Tool-first, scene-second:** Test videos validate the engine; they must not grow the engine into a topic-specific jungle.

---

## 6. Abstraction Layers (authoritative)

Matemium is a **layout-to-animation compiler**, not a collection of lesson scenes. The product is the **tool** — reusable primitives, layout, camera, timeline, and styling — that can compose any math video later.

### 6.1 Two layers — no `canvas/extensions/`

We deliberately **do not** add a third package tier (`canvas/extensions/`). Extra namespaces on top of Manim + Canvas confuse human and AI authors, who treat every import under `canvas/` as canonical API.

```
projects/<name>/     Lesson scripts + optional helpers.py (topic recipes)
projects/_lib/       Optional shared helpers (explicit opt-in across 2+ lessons)
    │
    ▼  compose via CanvasBuilder + style={}
canvas/              Engine only — generic DSL, layout, measure, scene, camera, focus
```

| Layer | Lives in | Responsibility | Must NOT contain |
|-------|----------|----------------|------------------|
| **Engine** | `canvas/` | Sheet DSL, `LayoutEngine`, `Style`, flex, measure/render pipeline, `CanvasScene` timeline compiler, camera pan/2D↔3D, `FocusEngine`, registry, reel cutter | Topic-specific builder methods, lesson copy, one-off scene hacks |
| **Projects** | `projects/<name>/` | `scenes.py` narrative; `helpers.py` for topic functions that call core APIs | Patches to `builder.py` / `scene.py` |
| **Shared project lib** (optional) | `projects/_lib/` | Plain Python copied or imported by multiple lessons — never auto-discovered by the engine | Engine timeline dispatch, camera physics |

**Rule:** A new test scene must **not** add `add_<topic>_*` methods to core `CanvasBuilder`. If a lesson needs a pattern twice, write a **plain function** in that project's `helpers.py` (or `projects/_lib/`) that takes a `CanvasBuilder` and uses core methods — not the engine.

**Why no extensions package:** The goal is engine hygiene, not a new vocabulary. AIs authoring `scenes.py` should only memorize `canvas/USAGE.md` (core API). Topic code is visible, local Python next to the lesson.

### 6.2 CSS-like styling is the primary composition mechanism

Authors express layout and presentation through **`style={...}` dicts** (parsed by `Style` in `layout.py`), not through growing the builder API:

- `margin`, `margin-top`, `margin-bottom`, `margin-left`, `margin-right`
- `width`, `height`
- `wrap`, `align` / `text-align`

Core methods stay **structural and generic**:

- `add_text`, `add_math`, `add_3d` — content + style
- `add_flex_row`, `add_flex_column` — composition via specs (`text_spec`, `math_spec`, …)
- `add_camera_focus` — viewport tool (isolate / overlay)
- `add_raw` — escape hatch to `CanvasElement`

Semantic typography (`add_heading`, `add_body`, `add_observation`) are **thin style presets** on `add_text` — acceptable in core because they encode layout intent, not a math topic.

### 6.2.1 Inline text runs (letter / word / phrase granularity)

Block-level `style={}` controls margins, width, and wrap on the whole text element. **Inline styling** is a separate axis: authors pass a **list of runs** to `add_text` (or `add_body`, flex `text_spec`). Each run is one atomic fragment — as small as a single letter or as large as a phrase.

Two levels, enforced early:

| Level | Controls | Example |
|-------|----------|---------|
| **Block** | `style={}` on `add_text` | `margin-bottom`, `wrap`, `width` |
| **Inline run** | per-run dict in the list | `color`, `highlight`, `bold`, `underline` |

```python
builder.add_text([
    "In ",
    builder.run("f", color="#cccccc"),
    builder.run("(", color="#cccccc"),
    builder.run("x", color="#5eb3ff"),
    builder.run(")", color="#cccccc"),
    " the letter ",
    builder.run("x", color="#5eb3ff", highlight=True),
    " is the variable.",
])

builder.add_body([
    "The ",
    builder.run("quadratic", color="#ffdd66", highlight=True),
    " formula uses ",
    builder.run("a", color="#ff8a65"),
    ", ",
    builder.run("b", color="#5eb3ff"),
    ", and ",
    builder.run("c", color="#81c784"),
    ".",
])
```

Implementation: `canvas/rich_text.py` composes Manim `Text` per run (with optional `BackgroundRectangle` for word highlight). Layout and wrap treat the result as one measured text block. No topic-specific APIs — this is core typography.

### 6.3 What belongs in the engine timeline

**Generic timeline actions** (stay in `dsl.py` + `scene.py`):

- `CanvasElement` reveal (lazy build + entry animation)
- `CameraMove` — explicit scroll
- `TransformElement` — re-animate existing registry entry
- `CameraFocus` — isolate-zoom or overlay magnifier (`focus.py`)

**Topic-coupled timeline actions** (should become generic or live only in project helpers):

- `PlotTrace` — currently hard-wired to quadratic `PlotPart` in `scene.py`; long-term → generic `TraceAction` on any parametric curve, or project-local timeline assembly via `add_raw`

### 6.4 Element types: core vs topic-specific

**Core element types** (primitives any lesson can use):

`MathTex`, `Text`, `ThreeDGraph`, `Surface`, `Axes`, `NumberPlane`, `ParametricFunction`, `VGroup`, `Dot`, `Arrow`, `Image`, `SVG`

**Topic-specific element types** (added during test-scene work — technical debt in DSL):

`GridBoard`, `GridMark`, `QuadraticPlot`, `QuadraticPlotPair`

Render support for these may remain in `measure.py` temporarily. **Authoring** must not stay on `CanvasBuilder` — project `helpers.py` functions build `CanvasElement` instances (or call core + flex) and use `add_raw` / timeline APIs where needed.

### 6.5 Development workflow

1. **Stress-test** with real projects under `projects/` (quadratic graphs, EM waves, tic-tac-toe).
2. **Extract** repeated patterns into project `helpers.py`, or into `projects/_lib/` if two unrelated lessons need the same code.
3. **Promote to core** only when a pattern is truly generic (e.g. `add_axes_plot(fn, x_range)` — not `add_quadratic_plot(a,b,c)`).
4. **Never** merge lesson-specific logic into `CanvasScene.construct()` or `CanvasBuilder` for convenience.
5. **Prefer** `style={}` + flex composition over new `add_*` methods.
6. Test scenes are **disposable**; the engine abstractions are **durable**.

### 6.6 Correct vs incorrect growth

```python
# CORRECT — scenes.py uses core + style
builder.add_flex_row([
    builder.math_spec(r"y = x^2 - 2x + 1", style={"width": 3.0}),
    builder.math_spec(r"y = -x^2 + 2x + 1", style={"width": 3.0}),
], gap=0.6)
builder.add_camera_focus("pair_el", mode="isolate", zoom=2.0)

# CORRECT — topic logic in project helpers; core only provides generic flex
# projects/quadratic_graphs/helpers.py
def quadratic_plot_flex_spec(builder, a, b, c, *, id, **kwargs):
    return builder.element_spec(quadratic_plot_element(a, b, c, id=id, **kwargs), style=...)

builder.add_flex_row([left_spec, right_spec], gap=0.55)

# INCORRECT — topic types or specs on CanvasBuilder
builder.quadratic_plot_spec(...)   # belongs in projects/quadratic_graphs/helpers.py
builder.add_quadratic_compare(...) # legacy debt on builder — do not extend
```

The quadratic and grid methods on `CanvasBuilder` today are **technical debt** from rapid test-scene iteration. They work, but violate this spec until moved into the owning project (or `projects/_lib/`).

---

## 7. Coordinate system & camera (authoritative)

### 7.1 Sheet plane

| Axis | Role |
|------|------|
| **X** | Horizontal placement on the tape (align left/center/right via layout) |
| **Y** | Scroll axis — infinite vertical tape |
| **Z** | Depth on/above the sheet (`0` default); overlays use a tiny epsilon |

Constants: `canvas/coords.py` — `SHEET_PLANE_Z = 0`, `OVERLAY_Z_EPSILON`.

Elements default to `z = 0`. Authors may set explicit `z` on `CanvasElement` or via `add_raw` for lifted content.

### 7.2 Camera views

| View | When | Zoom mechanism |
|------|------|----------------|
| **Sheet view** (default) | Text, math, plots, scroll, focus | Top-down on `z = 0`; **`camera.set_zoom`** (not frame crop alone) |
| **Tilt view** (optional) | `ThreeDGraph` / `Surface` reveal with `pitch` | Perspective; `phi` / `theta` tilt |

**Not allowed anymore:** calling “2D mode” on every flat element reveal. Flat content stays on the sheet; the camera does not thrash between modes.

### 7.3 Why zoom was hard before

`ThreeDScene` + `ThreeDCamera` expose `zoom_tracker`, `phi_tracker`, etc. Tape content is flat on a plane, but we alternated between orthographic top-down and perspective 3D **per timeline item**. Zoom on the wrong mode looked broken or invisible.

**Fix:** one default sheet view; zoom drives ``ThreeDCamera.zoom_tracker``; isolate focus uses ``viewport_fit.py`` to **cap** zoom so the target's occupation box never overflows the pixel viewport; tilt is optional for 3D moments only.

### 7.4 API surface

- `CameraController.return_to_sheet()` — orthographic sheet view
- `CameraController.tilt_for_3d(phi=...)` — perspective tilt for surfaces
- `transition_to_2d` / `transition_to_3d` — legacy aliases
- `add_camera_focus(..., mode="isolate")` — pan + sheet zoom; returns to sheet if still tilted

---

## 8. Desktop product architecture (authoritative)

**Full spec:** [`desktop-architecture.md`](desktop-architecture.md)

Matemium is pivoting from a developer CLI/library to a **free, source-available desktop application**. The engine in `canvas/` becomes a **local compilation farm** packaged as a PyInstaller sidecar inside a **Tauri v2** shell. This section records how that pivot relates to the engine — without changing engine internals.

### 8.1 Three boundaries

| Boundary | Technology | Responsibility |
|----------|------------|----------------|
| **Cloud** | HTTPS API | Optional auth, profile/provider sync, **BYO chat LLM helpers** — returns text + code edits only |
| **Desktop shell** | Tauri (Rust) + TypeScript UI | Projects, code editor, AI chat, diff apply, sidecar lifecycle |
| **Local engine** | Python sidecar (`canvas/` + Manim) | Lint/import `scenes.py`, render, emit progress events |

**Hard rule:** No cloud rendering. No render farms. No Matemium-owned model quota or pooled provider keys.

**Cross-platform ship:** TS/Rust are shared; the PyInstaller sidecar is **not** cross-compiled — one native binary per OS triple, built via CI matrix. See [`desktop/targets/README.md`](desktop/targets/README.md).

### 8.2 Authoring model

| Context | Authoring surface | Artifact |
|---------|-------------------|----------|
| **Product (desktop)** | Code editor + AI chat → **autonomous agent** (v2) | `scenes.py`; optional `helpers.py`; first-class `brief/` project memory |
| **Development (repo)** | `projects/*/scenes.py` + optional `helpers.py` | Same Python → `CanvasBuilder` → `SheetDSL` |

- **AI edits Python code** on the user's behalf — not Sheet DSL JSON, not builder-op JSON.
- **`SheetDSL`** is **internal IR** produced by `builder.build()` inside `scenes.py`. It is not the network authoring format.
- **`SheetDSL.from_dict()`** and inline-`dsl` IPC remain for **tests, fixtures, and engine debugging** only.

Visual **section fences** (`# ---DIV: Title---` before top-level `def`/`class`) give a multi-pane editor UX while keeping one Python file. See [`desktop-architecture.md`](desktop-architecture.md) §5.

**v1** can stay single-file (`scenes.py` only). **v2 agent/project mode** uses a bounded workspace: `scenes.py` as the render entrypoint, `helpers.py` for reusable Python support, and `brief/` for structured creative/production context such as passport, description, tape plan, roadmap, and narration. See [`ai-agent-architecture.md`](ai-agent-architecture.md).

The `brief/` files are product memory for the user, UI, and AI. They do not replace `SheetDSL`, and the engine should not treat Markdown/JSON brief files as animation IR.

**Latest product decisions** (free/source-available distribution, OpenRouter-first BYO AI providers, local vector DB/RAG in sidecar, lazy loading, first-run downloads of Jina embeddings + TinyTeX, YouTube-based thin publishing, strict user gating until fully ready, local + hosted MCP) are in [`PRODUCT-ARCHITECTURE-DECISIONS.md`](PRODUCT-ARCHITECTURE-DECISIONS.md).

**PAD-10 complete:** Cross-platform packaging, CI updates, docs refresh. Full implementation details in [`PRODUCT-ARCHITECTURE-IMPLEMENTATION.md`](PRODUCT-ARCHITECTURE-IMPLEMENTATION.md).

### 8.3 Process architecture

```
TypeScript UI  ──(Tauri invoke)──►  Rust orchestrator  ──(IPC)──►  Python sidecar
       ▲                                    │                           │
       └──────────── progress events ──────┴───────────────────────────┘
```

IPC transport: stdin/stdout JSON lines. Primary desktop commands: `lint_project`, `check_project`, `render_project`. Legacy: `validate_dsl` / `render` with inline `dsl` for dev. See [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md).

When adding engine features, expose them through **`CanvasBuilder`** so project code (human or AI) can use them. Sidecar IPC commands are for orchestration, not animation authoring.

### 8.4 Repository roles under the pivot

| Path | Desktop role | Dev role (unchanged) |
|------|--------------|----------------------|
| `canvas/` | Frozen into PyInstaller sidecar binary | Engine source of truth |
| `matemium/` | Sidecar IPC + CLI | Local iteration |
| `projects/` | Parity reference for workspace `scenes.py` | Lesson harness |
| `outputs/` | Per-job render dirs (user-scoped) | Per-project render dirs |

### 8.5 Engine constraints for desktop authors

All code in `canvas/`, `matemium/`, and future `src-tauri/` must respect:

1. **Strict TS ↔ Rust ↔ Python boundary** — no cross-language imports across layers.
2. **Code-first product path** — new timeline actions and element types must be reachable from `CanvasBuilder` in project `scenes.py`.
3. **`SheetDSL` serializability** — internal IR must remain JSON-serializable for debugging and legacy IPC.
4. **Streamed progress** — long renders emit structured events for the UI.
5. **Lint/check before render** — catch bad project code before Manim/LaTeX spend.
6. **§6 abstraction rules still apply** — no topic APIs on `CanvasBuilder`; no `canvas/extensions/`.
