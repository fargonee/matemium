# Matemium

A **layout-to-animation compiler and agentic desktop studio** for structured visual explanations, built on [Manim Community Edition](https://www.manim.community/). Matemium began with mathematics, but its generic paths, plots, diagrams, state transitions, morphs, tapes, and 3D world can express any subject that benefits from staged visual reasoning. Instead of writing imperative scene scripts, you describe content on an **infinite vertical learning tape**; the engine handles layout, camera movement, entry animations, persistent element state, and reusable transitions.

Output targets **9:16 portrait reels** (TikTok / Shorts) by default, with landscape YouTube support. Long-form sheets can be exported as static study materials or auto-chunked into short clips.

**Documentation baseline (2026-07-27):** author-facing claims are aligned to
the current source and tests. Historical phase plans describe intent and do not
override the current contract in [`AUTHORING_API.md`](AUTHORING_API.md).

## Product direction

Monorepo for a **free, source-available desktop app** under the Matemium Source-Available License — three deployable layers:

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
| `generic_visuals.py` | Validated `DataPath`, `DataPlot`, and `Diagram` renderers + semantic parts |
| `scene.py` | Timeline compiler — lazy reveal, auto-focus, state transitions, morphs |
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

### 3. Visual explanation projects (`projects/`)

Each folder is one video. A project has `scenes.py` (required; **the desktop app's single authoring file**) and optional `helpers.py` for topic-specific composition functions in the dev repo. The desktop v1 product uses **one `scenes.py`** with `# ---DIV: ...---` section markers for navigable editing.

The bundled flagship library currently contains projects across
eleven subjects: Fourier epicycles, orbital mechanics, an SN2 reaction,
Dijkstra’s algorithm, feedback control, a supply shock, DNA-to-protein,
the July Crisis, the Ship of Theseus, cross-language sentence structure, and
municipal clean-water systems. Fourier epicycles has an accepted preview;
the remaining projects are reauthoring inputs and engine evidence, not yet
accepted showcase renders.

See [`projects/flagship_library.md`](projects/flagship_library.md) for the index
and evidence status.

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
- **Sampled paths** — `add_data_path(points, ...)` for trajectories, routes, contours, and vectors
- **Sampled plots** — `add_data_plot(series, markers=...)` with named semantic series/markers
- **Semantic diagrams** — `add_diagram(nodes, edges, ...)` for flows, maps, graphs, and argument structures
- **State transitions** — `add_state_transition(...)` targets whole elements or `element::semantic-part`
- **Element morphs** — `add_element_morph(...)` recompiles changed content/geometry
- **Camera focus** — `add_camera_focus(element_id, mode="isolate", zoom=2.0)`
- **3D solids** — `add_solid(shape="cube", ...)`, `add_solid_lift(id, lift=1.8)`, `add_camera_inspect(id, path=[...])`
- **Escape hatch** — `add_raw(CanvasElement(...))` for full DSL control

The production-safe default is the automatic root tape. Additional tapes are
camera-facing curtains: one selected tape hides the free world and all other
tapes, and a world observation opens it again. `scroll_tape()` explicitly
selects a tape and local position. See the capability-maturity table in
[`AUTHORING_API.md`](AUTHORING_API.md).

Topic-specific calculations and recipes belong in `projects/<name>/helpers.py`,
not in the engine. See [`AUTHORING_API.md`](AUTHORING_API.md) for the current
contract and [`canvas/USAGE.md`](canvas/USAGE.md) for the extended guide.

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
scene.export_full_sheet(
    "my_sheet",
    format="png",
    full_tape=True,
)
```

Use `tape_id="main"` when selecting among multiple populated tapes.

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
- Validated `DataPath`, `DataPlot`, and `Diagram` compound visuals
- Stable semantic-part addressing for paths, axes, series, markers, nodes, edges, and edge labels
- Synchronized allowlisted state transitions + compiled element morphs
- Strict pre-render DSL validation and structured project-check diagnostics
- Real 3D surfaces (`z = f(x,y)`)
- 3D solids (cube/sphere), lift, camera inspect paths
- Camera focus (isolate / overlay) with viewport-fit zoom capping
- Lazy element reveal + auto-focus on scroll
- Full static canvas export (PNG/PDF)
- Reel cutter + manifest generator
- CLI tool with project scaffolding and isolated outputs
- Eleven cross-subject first-pass flagship projects + development demos

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
- Reauthor and visually validate the flagship projects with the current generic primitives
- Generic timed traversal/trace over `DataPath` or `DataPlot` (the old `PlotTrace` remains quadratic-specific)
- Keep additional-tape and free-world curtain composition covered by preview
  and runtime regressions as more flagship projects adopt it
- Dedicated future work for unfinished world-camera seams and timed media/audio
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
