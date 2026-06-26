# Matemium — Project Introduction

Matemium is a **layout-to-animation compiler** for math education videos. It sits on top of [Manim Community Edition](https://www.manim.community/) (Python) and changes how you author animations: instead of writing imperative scene scripts where you manually call `self.play(Write(...))` and `self.wait()`, you describe content on an **infinite vertical learning sheet**. The engine handles layout, camera scroll, entry animations, persistent element state, and export to social-friendly formats.

---

## Product direction (2026-06-26)

We are building a **commercial/freemium desktop application** — not an open-source developer CLI as the primary product.

| Layer | Technology | Role |
|-------|------------|------|
| **Cloud** | HTTPS API (FastAPI) | Auth, billing, chat LLM routing — text + code edits only. **No cloud rendering.** |
| **Desktop** | Tauri v2 + TypeScript | Code editor, AI chat, project workspaces, sidecar lifecycle |
| **Local engine** | PyInstaller sidecar | Frozen `canvas/` + Manim; lint, import, render on the user's machine |

**Authoring surface:** Python `scenes.py` using `CanvasBuilder` + `CanvasScene` — the same API in the dev repo and the desktop app. `SheetDSL` is **internal IR** from `builder.build()`; AI does not emit JSON over the network.

**AI integration tiers:**

| Tier | Mode | Project shape |
|------|------|---------------|
| **v1 — Chat** | Completions + Search/Replace diffs | Single `scenes.py` |
| **v2 — Agent** | Tool loop (`view_file`, `edit_file`, `compile_manim`) + self-correction | `scenes.py` + `assets.py` only |

Visual section fences (`# ---DIV: Title---`) make one file feel like multiple collapsible cards in the editor without splitting the project.

**Key docs:**

- [desktop-architecture.md](desktop-architecture.md) — product goals, boundaries, workspace model
- [ai-agent-architecture.md](ai-agent-architecture.md) — autonomous agent: tools, patches, TinyTeX, self-correction loop
- [architecture.md](architecture.md) — engine design rules (§8 desktop summary)
- [STRUCTURE.md](STRUCTURE.md) — monorepo map

---

## The problem it solves

Traditional Manim authoring is sequence-oriented: elements appear, animate, and often disappear within a fixed frame. Math teaching often wants something closer to a **continuous reasoning tape** — a scrollable document where earlier steps stay visible, the camera moves down as the lesson progresses, and you can zoom back to an equation from ten steps ago without rebuilding it.

Matemium models that tape explicitly:

- Content is anchored at fixed `(x, y, z)` coordinates on a sheet
- The camera pans down the Y axis like scrolling a document
- Elements materialize **lazily** when the viewport reaches them
- Once revealed, elements persist in a registry and can be re-animated later
- Long-form output can be auto-chunked into **9:16 vertical reels** for TikTok, Shorts, and Reels

Default output is portrait 9:16; landscape 16:9 for YouTube is also supported.

---

## Core paradigm: the infinite learning sheet

Think of the canvas as a 3D scene with a flat learning sheet on the XY plane at `z = 0`:

```
                     ┌──────────────────────┐
                     │ 9:16 viewport camera │◄── lazy reveal when in view
                     └───────────┬──────────┘
                                 │ pans down Y axis
                                 ▼
 ┌ Learning sheet (XY plane, z=0) ───────────────────────────────┐
 │ ┌─────────┐   ┌───────────────┐  ┌────────────┐    ┌─────────┐ │
 │ │ Heading │   │ Math equation │  │ 3D surface │    │ Summary │ │
 │ └─────────┘   └───────────────┘  └────────────┘    └─────────┘ │
 └────────────────────────────────────────────────────────────────┘
```

| Axis | Role |
|------|------|
| **X** | Horizontal placement (left / center / right via layout) |
| **Y** | Scroll axis — the infinite vertical tape |
| **Z** | Depth — grid marks, lifted 3D solids, overlays |

The viewport is a 9:16 frame whose center moves along `(x, y, 0)`. Flat content stays on the sheet in **sheet view** (orthographic, top-down). **Tilt view** is optional and used only for 3D surface moments (`add_3d` with pitch).

---

## How authoring works: DSL → compiler → Manim

You do not write raw Manim scene logic for each lesson. You build a **Sheet DSL** — a declarative specification of elements and a timeline — then `CanvasScene` compiles it into a Manim `ThreeDScene`.

### Recommended path: `CanvasBuilder`

```python
from canvas import CanvasScene
from canvas.builder import CanvasBuilder

class MyLesson(CanvasScene):
    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="My Lesson")

        builder.add_heading("Chapter 1")
        builder.add_math(r"x^2 - 5x + 6 = 0")
        builder.add_observation("Find two numbers that multiply to 6 and add to -5.")
        builder.add_math(r"(x-2)(x-3) = 0")
        builder.add_3d("z = x^2 - y^2", pitch=45)
        builder.add_text("Solutions: x = 2 or x = 3", after_3d=True)

        super().__init__(dsl=builder.build(), **kwargs)
```

Save as `projects/my_lesson/scenes.py`, then render with `./matemium.sh render my_lesson`.

In the **desktop app**, the same file lives in a user workspace; the sidecar imports and renders it locally.

### Compilation pipeline

```
projects/<name>/scenes.py   ← lesson narrative (CanvasBuilder + style={})
        │
        ▼
canvas/                     ← engine: layout, measure, scene, camera, focus, registry
        │
        ▼
Manim ThreeDScene           ← rendered .mp4, PNG/PDF export, reel cuts
```

`CanvasScene` walks the timeline in order: lazy reveal, auto-focus, flex groups, camera moves, transforms, solid lifts, inspect paths, and focus modes. This is deliberately not a pre-laid static sheet the camera merely scrolls over.

---

## Architecture: two layers, no extensions package

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **Engine** | `canvas/` | Generic DSL, CSS-like layout, measure/render, timeline compiler, camera, focus, registry, reel cutter |
| **Projects** | `projects/<name>/` | `scenes.py` narrative + optional `helpers.py` (dev repo topic recipes) |
| **Shared helpers** | `projects/_lib/` | Optional cross-lesson Python (explicit import only) |

There is **no `canvas/extensions/`** tier. Topic code stays next to the lesson so authors memorize one API ([`canvas/USAGE.md`](canvas/USAGE.md)), not a growing jungle of `add_quadratic_*` methods.

**Desktop agent workspaces** use a strict two-file model instead of open-ended multi-file repos:

| File | Role |
|------|------|
| `scenes.py` | Visual timeline — `# ---DIV:` markers, `part_*` functions, `CanvasScene` |
| `assets.py` | Engine room — computations, coordinate arrays, LaTeX strings, mesh data |

Composition uses **CSS-like `style={}`** dicts and flex rows/columns rather than endlessly growing `CanvasBuilder` with domain methods.

---

## Desktop system boundaries

```
┌─────────────────────────────────────────────────────────────┐
│  CLOUD — auth, billing, chat LLM (no rendering)             │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────┐
│  DESKTOP — Tauri v2 + TypeScript UI                         │
│    Code editor · AI chat/agent · diff apply · preview       │
└────────────────────────────┬────────────────────────────────┘
                             │ NDJSON stdin/stdout
┌────────────────────────────▼────────────────────────────────┐
│  SIDECAR — PyInstaller matemium-sidecar                     │
│    lint → import scenes.py → render → progress events       │
└─────────────────────────────────────────────────────────────┘
```

**TypeScript never imports Python.** Rust orchestrates; the sidecar owns Manim.

### Cross-platform shipping

The TypeScript and Rust shell are **shared across Windows, macOS, and Linux**. The PyInstaller sidecar **cannot be cross-compiled** — each OS needs its own native binary:

```
desktop/src-tauri/binaries/
├── matemium-sidecar-x86_64-pc-windows-msvc.exe
├── matemium-sidecar-x86_64-apple-darwin
├── matemium-sidecar-aarch64-apple-darwin
└── matemium-sidecar-x86_64-unknown-linux-gnu
```

Production releases use a **GitHub Actions CI matrix** (Windows, macOS, Linux runners). See [desktop/targets/README.md](desktop/targets/README.md).

### AI agent (v2)

The agent upgrades chat from "copy markdown code blocks" to an **autonomous coding loop**:

1. **Context bundler** — editor text, cursor/selection, section map, last compile errors
2. **Tools** — `view_file`, `edit_file` (Search/Replace patches), `compile_manim`
3. **Self-correction** — compile failure → feed stderr to LLM → auto-fix → retry

Full spec: [ai-agent-architecture.md](ai-agent-architecture.md).

### LaTeX (TinyTeX)

Manim needs LaTeX for math. Full TeX Live installs are too large to bundle. Production ships a **TinyTeX micro-distribution** (~80–120 MB), installed on first run, with PATH injection at sidecar startup. Pre-install required packages (`amsmath`, `amssymb`, etc.) in CI when building the master bundle.

---

## Key engine modules

| Module | Purpose |
|--------|---------|
| `dsl.py` | Sheet specification — elements, timeline, settings |
| `builder.py` | Fluent `CanvasBuilder` API |
| `layout.py` | CSS-like `Style`, flex rows/columns, vertical flow |
| `measure.py` | Unified measure + mobject build |
| `scene.py` | Timeline compiler — lazy reveal, auto-focus, dispatch |
| `registry.py` | Persistent `MobjectRegistry` for re-animation |
| `camera.py` | Sheet-view pan/zoom; optional tilt for 3D |
| `focus.py` + `viewport_fit.py` | Isolate-zoom and overlay magnifier |
| `surfaces.py` | Parse `z = f(x,y)` into Manim 3D surfaces |
| `solids.py` | Generic 3D primitives on the tape |
| `cutter.py` | `ReelCutter` — chunk long videos at chapter boundaries |
| `rich_text.py` | Inline styled text runs (per-letter color/highlight) |

**Persistent state:** `MobjectRegistry` holds every revealed element by ID. `TransformElement` and similar actions reference existing mobjects — no rebuild required.

---

## CLI and sidecar

**Development CLI** (`matemium/`):

```bash
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

./matemium.sh demo              # portrait smoke test → outputs/demo/
./matemium.sh list              # all projects and scenes
./matemium.sh new my_lesson     # scaffold projects/my_lesson/
./matemium.sh render my_lesson  # render → outputs/my_lesson/
```

**Desktop sidecar** (production):

```bash
echo '{"type":"request","id":"1","command":"ping","params":{}}' | python -m matemium.sidecar
```

IPC protocol: [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md).

---

## Example projects

Each folder under `projects/` is one video module with a required `scenes.py`:

| Project | What it demonstrates |
|---------|---------------------|
| `demo` | Engine smoke tests — portrait/landscape, flex layout, tic-tac-toe grid |
| `quadratic_factoring` | Clean core-only lesson — factoring with flex rows and 3D parabola |
| `em_waves` | Multi-section physics — Maxwell's equations, wave equation, 3D surfaces |
| `quadratic_graphs` | Side-by-side parabola comparison, plot traces, camera focus |
| `inscribed_sphere` | 3D solids — cube + inscribed sphere, lift, camera orbit |
| `olmoshlar` | Additional lesson |

Topic-specific geometry lives in `helpers.py` (dev repo) or `assets.py` (desktop agent mode); the scene file stays readable narrative.

---

## Output formats

**Video:**

```python
from canvas import CanvasSettings

CanvasSettings.for_reels()      # 9:16 portrait (default)
CanvasSettings.for_youtube()    # 16:9 landscape
```

**Static export** — full reasoning tape as PNG or PDF:

```python
scene.export_full_sheet("my_sheet", format="png", full_tape=True)
```

**Reel cutting** — auto-slice long renders at `CameraMove` boundaries via `ReelCutter` + ffmpeg.

---

## Repository layout

```
math/
├── canvas/                 # Engine (DSL, layout, scene, camera, …)
├── matemium/               # CLI + sidecar IPC
├── projects/               # Dev harness / parity scenes
├── desktop/                # Tauri app (app/, src-tauri/, packaging/)
├── server/                 # Cloud middleware (auth + chat)
├── shared/                 # Schemas, prompts, templates
├── tests/                  # Engine tests
├── outputs/                # Local renders (gitignored)
│
├── INTRODUCTION.md         # This file
├── STRUCTURE.md            # Monorepo map
├── desktop-architecture.md # Product architecture
├── ai-agent-architecture.md# Autonomous agent spec
├── architecture.md         # Engine design spec
└── project-spec.md         # Feature status
```

Dependencies: Python 3.11+, Manim Community Edition, Pillow. Desktop also needs Rust, Node.js, and per-platform PyInstaller builds.

---

## What is done vs. planned

### Engine (implemented)

- Sheet DSL + `CanvasBuilder` authoring
- CSS-like layout, flex, inline text runs
- Persistent registry + re-animation
- Sheet camera + optional 3D tilt
- 3D surfaces, solids, camera inspect paths
- Camera focus (isolate / overlay)
- Full static canvas export (PNG/PDF)
- Reel cutter + manifest generator
- CLI with project scaffolding
- Multiple lesson projects (demo, quadratic_*, em_waves, inscribed_sphere, olmoshlar) + demo suite

### Desktop (Linux MVP shipping)

| Phase | Status | Deliverable |
|-------|--------|-------------|
| Sidecar IPC | **done** | `lint/check/list/render_project` + progress, export, cut etc. |
| PyInstaller (Linux) | **done** | `matemium-sidecar` binary + Tauri `binaries/` |
| Tauri scaffold + Rust shell | **done** | `src-tauri/`, sidecar spawn, invoke bridge, project CRUD |
| UI shell (MVP) | **done** | Editor (Monaco + sections), AI chat, preview, two-file support |
| Cloud client + auth | **done** | Auth (Supabase/Google) + chat API |
| Linux ship | **done** | `.deb` / `.AppImage` + CI workflow |
| CI matrix (Win/Mac) | pending | Windows + macOS GitHub Actions |
| Agent mode (v2) | partial | Two-file + chat/patch foundation; full tool loop + self-correction |
| TinyTeX bootstrap | pending | First-run install + PATH injection |

### Engine (planned)

- Move legacy grid/quadratic builder methods into project `helpers.py`
- Generic parametric curve trace (replace quadratic-only `PlotTrace`)
- SolutionTape integration as canvas elements
- Element-type plugin registry in `measure.py` / `scene.py`
- Sidecar progress events for desktop preview matrix

---

## Mental model summary

| Traditional Manim | Matemium |
|-------------------|----------|
| Imperative `self.play()` sequences | Declarative sheet + timeline DSL |
| Fixed frame, elements come and go | Infinite vertical tape, persistent anchors |
| Manual layout positioning | CSS-like `style={}` + flex layout engine |
| Rebuild mobjects to revisit them | Registry-backed re-animation by ID |
| One video = one scene script | One compiler + many projects / lessons |
| Landscape-first thinking | Portrait reels-first, with landscape and static export |
| Developer installs Python + Manim | Desktop app bundles engine; zero cloud rendering |
| Copy-paste AI code blocks | v2 agent: inspect, patch, compile, self-correct |

Matemium is a **document compiler for animated math** — you write what should appear on the learning sheet and when the camera should move; the engine turns that into Manim animations, study-material exports, and social-ready reel segments. The long-term bet is a clean, generic compiler that scales to hundreds of lessons without the engine becoming a pile of topic-specific hacks.