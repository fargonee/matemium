# Matemium

A **layout-to-animation compiler** for math education videos, built on [Manim Community Edition](https://www.manim.community/). Instead of writing imperative scene scripts, you describe content on an **infinite vertical learning sheet**; the engine handles layout, camera scroll, entry animations, and persistent element state.

Output targets **9:16 portrait reels** (TikTok / Shorts) by default, with landscape YouTube support. Long-form sheets can be exported as static study materials or auto-chunked into short clips.

**PAD Phase 10 complete:** Packaging, CI, cross-platform builds, and docs refresh per [`PRODUCT-ARCHITECTURE-IMPLEMENTATION.md`](PRODUCT-ARCHITECTURE-IMPLEMENTATION.md). Full product architecture (lazy sidecar, first-run assets, RAG/MCP, strict gating, thin publishing) integrated.

## Product direction

Monorepo for a **free, source-available desktop app** — three deployable layers:

| Layer | Path | Role |
|-------|------|------|
| **Engine** | `canvas/`, `matemium/`, `projects/` | Local Manim compiler + sidecar IPC |
| **Server** | [`server/`](server/) | Optional cloud auth + BYO chat routing helpers (no rendering, no Matemium-owned model quota) |
| **Desktop** | [`desktop/`](desktop/) | Tauri app — Windows, macOS, Linux from one tree |

Overview: [`INTRODUCTION.md`](INTRODUCTION.md). Map: [`STRUCTURE.md`](STRUCTURE.md). Product spec: [`desktop-architecture.md`](desktop-architecture.md). AI agent: [`ai-agent-architecture.md`](ai-agent-architecture.md).

```bash
# Test the desktop sidecar IPC (no Tauri required yet)
echo '{"type":"request","id":"1","command":"ping","params":{}}' | python -m matemium.sidecar
```

## Install

**From source (recommended for development):**

```bash
git clone <repo-url> && cd math
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

**Requirements only (legacy):** `pip install -r requirements.txt`

**System dependencies for video renders:** FFmpeg and LaTeX (see [Manim installation](https://docs.manim.community/en/stable/installation.html)).

**Docker (reproducible renders — engine only):**

```bash
docker build -t matemium .
docker run --rm -v "$PWD:/workspace" -w /workspace matemium render demo
```

Note: See `.dockerignore` + `server/Dockerfile` for isolated PaaS builds (Northflank). Website is deployed to Cloudflare Pages from `website/`.

## Quick start

```bash
matemium demo                   # portrait test → outputs/demo/
matemium demo landscape         # 16:9 YouTube format
matemium list                   # all projects
matemium new my_lesson          # scaffold projects/my_lesson/
matemium render my_lesson       # render → outputs/my_lesson/
matemium render demo -q preview # fast preview (half res, 15 fps)
```

From a git checkout you can also use `./matemium.sh` (same as `python -m matemium`).

Set `MATEMIUM_ROOT` to point at a workspace directory when projects/ and outputs/ live outside the install location.

## What we built

### 1. Canvas engine (`canvas/`)

The core compiler. Authors describe a lesson via **`CanvasBuilder` in `scenes.py`**; `builder.build()` produces internal `SheetDSL`; `CanvasScene` compiles it into a Manim `ThreeDScene`.

| Module | Purpose |
|--------|---------|
| `dsl.py` | Sheet specification — elements, timeline, settings |
| `builder.py` | Fluent `CanvasBuilder` API (recommended authoring surface) |
| `layout.py` | CSS-like `Style`, flex rows/columns, border-box flow |
| `rich_text.py` | Inline text runs — per-letter/word color and highlight |
| `measure.py` | Unified measure + mobject build (single source of truth) |
| `scene.py` | Timeline compiler — lazy reveal, auto-focus, transforms |
| `registry.py` | Persistent `MobjectRegistry` for re-animation |
| `coords.py` | Sheet plane conventions — XY at `z=0`, Z for depth |
| `camera.py` | Sheet-view pan/zoom; optional tilt for 3D surfaces |
| `focus.py` | Isolate-zoom and overlay magnifier (`add_camera_focus`) |
| `viewport_fit.py` | Caps zoom so focused elements never clip the frame |
| `surfaces.py` | `z = f(x,y)` equation → Manim 3D surface |
| `solids.py` | Generic 3D primitives (cube, sphere) anchored on the tape |
| `inspect_path.py` | Keyframe camera inspect paths for volumetric elements |
| `plots.py` / `diagrams.py` | Low-level plot and diagram render helpers |
| `animations.py` | Entry animations, transforms, idle behaviors |
| `cutter.py` | `ReelCutter` — chunk long videos into reel segments |
| `overlay.py` | Focus overlay magnifier rendering |

**Paradigm:** Content lives on the **XY plane at `z = 0`**. The camera pans down the Y axis. Elements appear as the viewport reaches them, stay anchored, and can be re-animated later via the registry. 3D surfaces optionally tilt the camera; flat content does not thrash between 2D/3D modes.

### 2. Matemium CLI (`matemium/`)

User-facing tool for discovering, scaffolding, and rendering video projects.

| Command | What it does |
|---------|--------------|
| `matemium demo [variant]` | Render built-in test scenes (`portrait`, `landscape`, `builder`, `tictactoe`) |
| `matemium render <project> [scene]` | Render a project scene class |
| `matemium new <name>` | Scaffold `projects/<name>/` from template |
| `matemium list` | List projects, scenes, and output paths |

Entry points: `./matemium.sh` or `python -m matemium`.

Renders are isolated per project under `outputs/<project>/media/` (gitignored).

### 3. Video projects (`projects/`)

Each folder is one video. A project has `scenes.py` (required; **the desktop app's single authoring file**) and optional `helpers.py` for topic-specific composition functions in the dev repo. The desktop v1 product uses **one `scenes.py`** with `# ---DIV: ...---` section markers for navigable editing.

| Project | Scene | What it demonstrates |
|---------|-------|---------------------|
| `demo` | `PortraitDemo`, `LandscapeDemo`, `BuilderDemo`, `TicTacToeTutorial` | Engine smoke tests — portrait/landscape, flex layout, grid boards |
| `quadratic_factoring` | `QuadraticFactoring` | Core-only lesson — factoring \(x^2 - 5x + 6\) with flex rows and inline runs |
| `em_waves` | `EmWaves` | Multi-section physics — Maxwell's equations, wave propagation, 3D surfaces |
| `quadratic_graphs` | `QuadraticGraphs` | Side-by-side parabola comparison, plot traces, camera focus (uses `helpers.py`) |
| `inscribed_sphere` | `InscribedSphere` | 3D solids on the tape — cube + inscribed sphere, lift, camera orbit inspect |
| `olmoshlar` | (various) | Additional lesson content |

The `projects/_template/` folder scaffolds new projects. `projects/_lib/` is reserved for helpers shared across multiple lessons (explicit import only).

## Authoring a video

```python
from canvas import CanvasScene
from canvas.builder import CanvasBuilder

class MyLesson(CanvasScene):
    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="My Lesson")

        builder.add_heading("Chapter 1")
        builder.add_math(r"x^2 - 5x + 6 = 0")
        builder.add_observation("We look for two numbers that multiply to 6 and add to -5.")
        builder.add_math(r"(x-2)(x-3) = 0")
        builder.add_3d("z = x^2 - y^2", pitch=45)
        builder.add_text("Solutions: x = 2 or x = 3", after_3d=True)

        super().__init__(dsl=builder.build(), **kwargs)
```

Save as `projects/my_lesson/scenes.py`, then `./matemium.sh render my_lesson`.

### Composition tools

- **Block styling** — `style={"margin-bottom": 1.0, "width": 5.0, "wrap": True}` on any `add_*` call
- **Inline runs** — `builder.add_text([builder.run("x", color="#5eb3ff", highlight=True), " = 2"])`
- **Flex layout** — `add_flex_row` / `add_flex_column` with `text_spec`, `math_spec`, etc.
- **Camera focus** — `add_camera_focus(element_id, mode="isolate", zoom=2.0)`
- **3D solids** — `add_solid(shape="cube", ...)`, `add_solid_lift(id, lift=1.8)`, `add_camera_inspect(id, path=[...])`
- **Escape hatch** — `add_raw(CanvasElement(...))` for full DSL control

Topic-specific patterns belong in `projects/<name>/helpers.py`, not in the engine. See `canvas/USAGE.md` for the full API.

## Architecture

```
projects/<name>/          Lesson scripts + optional helpers.py
projects/_lib/            Shared helpers (explicit import)
    │
    ▼  compose via CanvasBuilder + style={}
canvas/                   Engine — DSL, layout, measure, scene, camera, focus
    │
    ▼  compiles to
Manim ThreeDScene         Rendered video / static export
```

**Two layers, no extensions package.** The engine stays generic; lesson logic stays next to the lesson. Test scenes validate abstractions — they must not grow `CanvasBuilder` with topic methods.

Deeper specs: [`desktop-architecture.md`](desktop-architecture.md) (product), [`ai-agent-architecture.md`](ai-agent-architecture.md) (autonomous agent), [`architecture.md`](architecture.md) (engine), [`project-spec.md`](project-spec.md) (status), [`canvas/USAGE.md`](canvas/USAGE.md).

## Video formats

```python
from canvas import CanvasSettings

CanvasSettings.for_reels()     # 9:16 portrait (default)
CanvasSettings.for_youtube()   # 16:9 landscape
```

## Static export

Export the full reasoning tape as PNG or PDF (natural aspect, no forced crop):

```python
scene = builder.to_scene()
scene.export_full_sheet("my_sheet", format="png", full_tape=True)
```

## Reel cutting

Long-form videos can be auto-sliced into short vertical clips:

```python
from canvas import ReelCutter

cutter = ReelCutter(segment_duration=50)
manifest = cutter.generate_manifest_from_dsl(dsl)
cutter.cut(input_video=..., output_dir=..., manifest=manifest)
```

## Current status

**Done:**
- Sheet DSL + `CanvasBuilder` authoring
- CSS-like layout, flex rows/columns, inline text runs
- Persistent element registry + re-animation
- Sheet camera (pan/zoom on `z=0`) + optional 3D tilt
- Entry animations, transforms, idle rotation
- Real 3D surfaces (`z = f(x,y)`)
- 3D solids (cube/sphere), lift, camera inspect paths
- Camera focus (isolate / overlay) with viewport-fit zoom capping
- Lazy element reveal + auto-focus on scroll
- Full static canvas export (PNG/PDF)
- Reel cutter + manifest generator
- CLI tool with project scaffolding and isolated outputs
- Multiple lesson projects (demo, quadratic_*, em_waves, inscribed_sphere, olmoshlar) + demo suite

**Desktop** ([`desktop/`](desktop/)):
- [x] Monorepo layout (`desktop/app`, `desktop/src-tauri`, `desktop/packaging`, `desktop/targets`)
- [x] Sidecar JSON IPC (`matemium-sidecar`, `matemium/ipc/`)
- [x] Tauri v2 + TypeScript UI (Monaco editor, AI chat, section outline, render preview, project workspaces)
- [x] Sidecar project commands — `lint_project`, `check_project`, `list_scenes`, `render_project`, `export_sheet`, etc. + progress events
- [x] PyInstaller Linux binary + full Linux ship (`.deb` / `.AppImage`) via `./desktop/scripts/build-linux.sh`
- [x] Cloud auth + chat client (Supabase / Google sign-in; AI uses user-owned provider keys)
- [ ] Full CI matrix for Windows + macOS desktop builds (Linux complete)

**Server** ([`server/`](server/)):
- [x] FastAPI — `/health`, auth (Supabase token + Google sign-in session), `/v1/chat/completions`, admin routes
- [x] BYO LLM proxy helpers for user-owned OpenAI-compatible providers; OpenRouter is the default provider
- [x] Stub mode for dev

**Cost model:** Matemium is completely free to use. The project does not sell subscriptions, in-app AI tokens, or model access. Users connect their own external provider keys, preferably through OpenRouter OAuth, or use their own local models.

**CI / Deploy**: Engine tests on path changes; zero-downtime deploys for `server/` (Northflank) and `website/` (Cloudflare) with health verification + rollback. See `.github/workflows/`.

**Engine (in progress / planned):**
- Move legacy grid/quadratic builder methods into project helpers
- Generic parametric curve trace (replace quadratic-only `PlotTrace`)
- SolutionTape integration as canvas elements
- Reel cutting polish (audio, titles, padding)
- Element-type plugin registry to avoid unbounded `if type ==` growth
- Sidecar progress events for desktop preview matrix

## Project layout

Each publish target is isolated (see STRUCTURE.md for details):

```
math/
├── canvas/, matemium/, projects/   # Engine (pip + Docker root)
├── server/                         # Backend (Northflank/PaaS, own Dockerfile + context)
├── website/                        # Frontend (Cloudflare Pages)
├── desktop/                        # Desktop (Tauri bundles)
├── shared/                         # Contracts only
├── .dockerignore .gitignore        # Enforce isolation at build time
├── STRUCTURE.md
└── ...
```

## Dependencies

- Python 3.11+
- `manim >= 0.20.1`
- `pillow >= 12.0.0`

## Development

```bash
pip install -e ".[dev]"
pytest                 # unit tests (skips slow Manim renders)
pytest -m slow         # optional full render smoke test
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for architecture rules and PR expectations.
