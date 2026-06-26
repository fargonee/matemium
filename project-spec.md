# Matemium — Project Spec & Status

## Product direction (2026-06-26)

**We are building a commercial/freemium desktop application**, not an open-source developer tool as the primary product.

| Layer | Role |
|-------|------|
| **Cloud** | Thin router — auth, billing, **chat LLM**; returns text + code edits only |
| **Desktop (Tauri v2)** | Code editor + AI chat + preview; project workspaces with `scenes.py` |
| **Sidecar (PyInstaller)** | Frozen `canvas/` + Manim; lint, import, render project code locally |

**Authoring:** one `scenes.py` per project (v1 chat), `CanvasBuilder` + `CanvasScene`, visual `# ---DIV: ...---` section fences. **v2 agent mode:** strict `scenes.py` + `assets.py` with tool loop (view/edit/compile) and self-correction. **Not** AI → Sheet DSL JSON.

Full product architecture: [`desktop-architecture.md`](desktop-architecture.md). Agent upgrade: [`ai-agent-architecture.md`](ai-agent-architecture.md). Engine rules: [`architecture.md`](architecture.md) (incl. §8).

The CLI (`matemium`) and `projects/` layout remain for **engine development and parity testing**.

## Project layout

See [`STRUCTURE.md`](STRUCTURE.md) for the authoritative monorepo map.

```
math/
├── ENGINE (repo root)
│   ├── canvas/              # Compiler core
│   ├── matemium/            # CLI + sidecar IPC
│   ├── projects/            # Dev harness
│   ├── engine/README.md     # Engine layer guide
│   └── pyproject.toml
│
├── server/                  # Cloud middleware (FastAPI) — auth + chat LLM
│
├── desktop/                 # Cross-platform Tauri app (all OS targets)
│   ├── app/                 # TypeScript UI
│   ├── src-tauri/           # Rust shell
│   ├── packaging/           # PyInstaller sidecar spec
│   ├── scripts/             # Build helpers
│   └── targets/             # Windows / macOS / Linux notes
│
├── shared/                  # JSON schemas + protocol refs
├── fixtures/                # Dev test data
├── tests/                   # Engine tests
│
├── STRUCTURE.md
├── desktop-architecture.md
├── architecture.md
└── project-spec.md
```

## Commands (remember these)

```bash
./matemium.sh demo              # test portrait demo → outputs/demo/
./matemium.sh demo landscape
./matemium.sh list
./matemium.sh new my_video
./matemium.sh render my_video
```

## Vision

- Infinite vertically-scrollable "learning sheet" on a continuous Y-axis.
- Elements (MathTex, 3D graphs, text, diagrams) anchored at explicit `(x, y, z)` canvas coordinates.
- Camera pans down the sheet; elements trigger entry animations when the viewport reaches them.
- Full persistent state: elements can be re-animated / transformed later without being recreated.
- Output: long-form video that can be automatically chunked into 9:16 vertical social reels.
- **Tool-first:** We are building a robust compiler environment now; perfect lesson videos come later. Test scenes exist to stress the abstractions, not to permanently shape the engine API.

See `architecture.md` §6 for the abstraction layer model (engine + projects — **no** `canvas/extensions/`).

## Abstraction layers

| Layer | Path | Role |
|-------|------|------|
| Engine | `canvas/` | Generic DSL, CSS-like `Style`, flex layout, measure/render, scene timeline, camera, focus, registry, cutter — **the only API AIs should memorize** |
| Projects | `projects/<name>/` | `scenes.py` + optional `helpers.py` — topic recipes as plain Python functions |
| Shared (optional) | `projects/_lib/` | Helpers reused by 2+ lessons; explicit import, never auto-loaded by the engine |

**No `canvas/extensions/`:** A third package tier adds magic and confuses lesson authors. Topic code stays next to the lesson.

**Authoring rule:** compose via `style={}` and flex specs. New test projects must not add topic APIs to `canvas/builder.py`. Repeated lesson patterns → `helpers.py` in that project.

**CSS-like styling** (`layout.py` → `Style.from_dict`) is the intended way to control margins, width, wrap, and alignment without new builder surface area.

## Core modules

| Module | Role |
|--------|------|
| `dsl.py` | Sheet specification + `LayoutBox` on each element |
| `layout.py` | `LayoutEngine` — border-box flow, flex rows/columns |
| `rich_text.py` | Inline text runs — letter/word/phrase color and highlight |
| `measure.py` | Unified measure + mobject build (single source of truth) |
| `builder.py` | High-level `CanvasBuilder` — fluent authoring API |
| `scene.py` | `CanvasScene` engine — lazy element reveal, camera-driven timeline |
| `registry.py` | Persistent `MobjectRegistry` for re-animation |
| `coords.py` | Sheet plane conventions — XY at `z=0`, Z for depth |
| `camera.py` | Sheet-view pan/zoom on `z=0`; optional tilt for 3D surfaces |
| `animations.py` | Entry animations, transforms |
| `cutter.py` | `ReelCutter` — auto-chunk long videos into reels |
| `solids.py` | Generic 3D primitives (cube, sphere) — center-anchored on the tape |
| `inspect_path.py` | Keyframe camera inspect paths for volumetric orbit tours |
| `viewport_fit.py` | Viewport-fit zoom capping for isolate focus |
| `overlay.py` | Focus overlay magnifier rendering |

## How to use (recommended)

See `canvas/USAGE.md` for the complete guide.

Use `CanvasBuilder` for plain, short, reliable code. JSON loading remains as an advanced escape hatch only.

```python
from canvas.builder import CanvasBuilder
from canvas import CanvasScene

builder = CanvasBuilder(title="My Video")
builder.add_text("We start with the observation that...")
builder.add_math(r"x^2 - 5x + 6 = 0")
builder.add_3d("z = x^2 - y^2")
builder.add_text("Therefore the solutions are...", after_3d=True)

dsl = builder.build()
scene = CanvasScene(dsl=dsl)
```

Render:

```bash
./matemium.sh demo
./matemium.sh render my_video
```

Videos are written to `outputs/<project>/media/videos/...` (isolated per project).

### Video formats — portrait-first

- **Portrait (Reels / TikTok / Shorts)**: 9:16 vertical — default and primary target
- **Landscape (YouTube)**: 16:9 horizontal

```python
from canvas import CanvasSettings

settings = CanvasSettings.for_reels()    # Portrait 9:16 (default)
settings = CanvasSettings.for_youtube()  # Landscape 16:9
```

`CanvasSettings` provides `for_reels()`, `for_youtube()`, `get_manim_resolution()`, and `get_manim_config_dict()`.

See `scripts/legacy/demo_canvas.py` (deprecated) for `LandscapeCanvasDemo`.

### Full canvas static export (PNG / PDF)

The canvas is a persistent infinite tape:

- Elements appear in timeline order as the view scrolls down.
- Once written, they stay at their anchored `canvas_position`.
- The view can scroll or jump anywhere; elements remain in default state.
- `MobjectRegistry` keeps all elements for re-animation on demand.

```python
scene.export_full_sheet("my_sheet", format="png")
scene.export_full_sheet("my_full_tape", format="png", full_tape=True, title="My Full Reasoning Tape")
```

```bash
python scripts/legacy/render.py --demo portrait --export-full-sheet png --full-tape --export-title "My Full Tape"  # deprecated; prefer ./matemium.sh
```

### Reel cutting

```python
from pathlib import Path
from canvas import ReelCutter

cutter = ReelCutter(segment_duration=50)
manifest = cutter.generate_manifest_from_dsl(dsl)
cutter.save_manifest(manifest, Path("cuts/demo_cuts.json"))
cutter.cut(
    input_video=Path("media/videos/.../CanvasDemo.mp4"),
    output_dir=Path("media/reels"),
    manifest=manifest,
)
```

## Current status (2026-06-26)

- [x] DSL (JSON + Python builder)
- [x] Registry + persistent elements
- [x] Camera panning on XY sheet (`z=0`) + optional 3D tilt (not per-text mode flip)
- [x] Entry animations + state behaviors (rotate)
- [x] Transform / re-animation of previous elements
- [x] Real 3D surfaces (`z = f(x,y)` parsing)
- [x] Lazy element display + auto-focus on reveal
- [x] ReelCutter + manifest generator from DSL
- [x] Full static canvas export as PNG/PDF
- [x] CSS-like border-box layout + flex rows/columns
- [x] Inline text runs (letter / word / phrase color + highlight)
- [x] Camera focus tool (`add_camera_focus` — isolate / overlay)
- [x] 3D solids on the tape (`add_solid`, `add_solid_lift`, multi-part groups)
- [x] Camera inspect paths (`add_camera_inspect` — keyframe orbit tours)
- [x] Matemium CLI (`matemium demo|render|list|new`) with per-project isolated outputs
- [x] Lesson projects: `quadratic_factoring`, `em_waves`, `quadratic_graphs`, `inscribed_sphere`
- [ ] Move leaked domain APIs off `CanvasBuilder` into owning `projects/*/helpers.py`
- [ ] Generic curve trace timeline action (replace quadratic-only `PlotTrace`)
- [ ] Full production-quality mobject support for every Manim primitive
- [ ] Sophisticated idle behaviors beyond rotation
- [ ] SolutionTape integration (embed tapes as canvas elements)
- [ ] Reel cutting polish (audio, titles, padding)

## Abstraction audit (2026-06-26)

Audit after test-scene iteration (`quadratic_graphs`, `em_waves`, `demo/tictactoe`). Goal: measure how much scene/topic logic leaked into the engine.

### Properly generic (keep in core)

| Module | What | Reusability |
|--------|------|-------------|
| `layout.py` | `Style`, `LayoutEngine`, flex row/column, vertical flow | High — any lesson |
| `focus.py` | `FocusEngine`, isolate/overlay focus | High — any element id |
| `coords.py` + `camera.py` | XY sheet at `z=0`, sheet-view zoom, optional tilt | High |
| `scene.py` | Timeline compiler, lazy reveal, auto-focus, `CameraFocus` dispatch | High |
| `surfaces.py` | `z = f(x,y)` → Manim surface | High — any 3D equation |
| `registry.py` | Persistent mobject store | High |
| `builder.py` (partial) | `add_text/math/3d`, flex, `add_camera_focus`, `add_raw`, specs | High |

### Domain-specific leakage (move to project helpers)

| Location | API / type | Introduced for | Target home |
|----------|------------|----------------|-------------|
| `builder.py` | `add_grid_board`, `add_grid_mark`, `add_grid_moves`, `grid_board_spec` | Tic-tac-toe demo | `projects/demo/helpers.py` or `projects/_lib/grids.py` |
| `builder.py` | `quad_plot_spec`, `add_quadratic_plot`, `add_quadratic_compare`, `add_plot_trace` | `quadratic_graphs` | `projects/quadratic_graphs/helpers.py` |
| `dsl.py` | `GridBoard`, `GridMark`, `QuadraticPlot`, `QuadraticPlotPair`, `PlotTrace` | Same | Keep in DSL render path short-term; authoring via project helpers + `add_raw` |
| `scene.py` | `_handle_plot_trace` (quadratic `PlotPart` only) | Plot trace demo | Generic `TraceAction` in core, or project-local timeline assembly |
| `measure.py` | Branches for grid + quadratic element types | Render support | OK in core short-term; long-term via element plugin registry |

### Gray area (acceptable presets, watch for growth)

| API | Verdict |
|-----|---------|
| `add_heading`, `add_body`, `add_observation`, `add_concept` | Thin typography presets on `add_text` — stay in core |
| `diagrams.py`, `plots.py` | Low-level render helpers — fine in `canvas/`; builder wrappers should move |
| `add_camera_move` / `auto_camera` | Legacy/explicit scroll; auto-focus on reveal is preferred |

### Projects (correct layer)

| Project | Uses | Notes |
|---------|------|-------|
| `quadratic_factoring`, `em_waves` | Core only (`add_heading`, `add_math`, `add_3d`) | Good — no engine patches |
| `quadratic_graphs` | Core + `helpers.py` (compare rows, plot traces) | Quadratic builder methods still on core — trim when convenient |
| `inscribed_sphere` | Core solids + `helpers.py` (inscribed pair, inspect path) | Good pattern — topic logic in helpers |
| `demo/tictactoe` | Core + leaked grid APIs on builder | Move to `projects/demo/helpers.py` |

### Reusability score

- **Core layout + camera + focus:** reusable across all current and future lessons.
- **Builder surface:** ~60% generic, ~40% test-scene patches that should not have landed in core.
- **Scene timeline:** one topic handler (`PlotTrace`); otherwise clean.
- **Measure pipeline:** single source of truth — good pattern; topic element types should register rather than hard-code new `if elem.type ==` branches indefinitely.
- **Authoring surface for AIs:** one documented API (`canvas/USAGE.md` core section); project helpers are local and explicit.

## Desktop build phases

See [`desktop-architecture.md`](desktop-architecture.md) §6 for full detail. (Linux desktop MVP shipping.)

| Phase | Status | Deliverable |
|-------|--------|-------------|
| P0 — Document | **done** | Product architecture engraved in repo docs |
| P1 — Sidecar | **done** | `matemium-sidecar`, project IPC (`lint/check/list/render_project` + more), `workspace_project.py` |
| P2 — PyInstaller | **done** | `dist/matemium-sidecar`, Tauri `binaries/` copy, `verify-sidecar-binary.sh` |
| P3 — Tauri scaffold | **done** | `src-tauri/`, sidecar spawn, `invoke` bridge |
| P4 — Rust shell | **done** | sidecar IPC, project CRUD, `cloud_chat` |
| P5 — UI shell | **done** | Vite + React + Monaco (editor, chat, preview, sections, assets support) |
| P6 — Cloud client + auth | **done** | `auth_login`, Supabase/Google, `cloud_chat` → [`server/`](../server/) |
| P7 — Linux ship | **done** | `build-linux.sh` → `.deb` / `.AppImage`; CI in [`.github/workflows/build-linux.yml`](.github/workflows/build-linux.yml) |
| P8 — CI matrix (Win/Mac) | pending | Windows + macOS GitHub Actions workflows (Linux done) |

**Cross-platform rule:** PyInstaller sidecars cannot be cross-compiled — one native binary per OS triple, built on matching CI runners. See [`desktop/targets/README.md`](desktop/targets/README.md).

## Agent mode phases (v2)

See [`ai-agent-architecture.md`](ai-agent-architecture.md) §12. (UI supports two-file scenes+assets + chat; full autonomous loop + patch engine in progress.)

| Phase | Status | Deliverable |
|-------|--------|-------------|
| A1 — Patch engine | partial | Code edit utils + apply; Rust parser / full apply in progress |
| A2 — Context bundler | partial | Sections, editor state in chat context; full bundle for agent |
| A3 — Tool loop orchestrator | partial | `compile_manim` via sidecar + render pipeline; full view/edit/compile agent loop |
| A4 — Async render bridge | **done** | Non-blocking render + streamed `render_progress` events |
| A5 — Two-file workspace | **done** | `assets.py` template + editor support for scenes/assets files |
| A6 — TinyTeX bootstrap | pending | First-run install + PATH injection in sidecar |
| A7 — Agent system prompt | **done** | [`shared/prompts/agent-system.txt`](shared/prompts/agent-system.txt) |

## Engine next steps (parallel)

1. Move grid and quadratic builder helpers into owning `projects/*/helpers.py`; trim `CanvasBuilder`.
2. Generalize `PlotTrace` → parametric `TraceAction` in core, or assemble traces from project helpers via `add_raw`.
3. Embed `SolutionTape` as a canvas element.
4. Dry-run time simulator for cutter duration estimates.
5. Optional YAML support.
6. Element-type plugin registry in `measure.py` / `scene.py` to avoid unbounded `if type ==` growth.
7. Sidecar progress events from `CanvasScene` / `render_sheet()` for desktop preview matrix.