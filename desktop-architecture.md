# Matemium Desktop — Product Architecture & Goals

**Status:** Core desktop model (2026-06-26). **Latest product decisions** (lazy sidecar, first-run downloads, UX gating, YouTube publishing, vector intelligence) are in [`PRODUCT-ARCHITECTURE-DECISIONS.md`](PRODUCT-ARCHITECTURE-DECISIONS.md).  
**Audience:** All contributors — engine, desktop shell, cloud middleware, and AI integration authors.

**Phase 10 status:** Packaging/CI/cross-platform + docs refresh implemented. See [`PRODUCT-ARCHITECTURE-IMPLEMENTATION.md`](../PRODUCT-ARCHITECTURE-IMPLEMENTATION.md) §11 and phased roadmap.

This document records the **strategic pivot** to a **free, source-available desktop application** where users author animations as **Python project code** assisted by **user-owned AI provider access** — not as cloud-generated JSON specs or platform-resold model credits.

Engine internals remain in [`architecture.md`](architecture.md); feature status in [`project-spec.md`](project-spec.md). Product-level architecture decisions (sidecar lazy loading, intelligence engine, publishing, user gating) live in [`PRODUCT-ARCHITECTURE-DECISIONS.md`](PRODUCT-ARCHITECTURE-DECISIONS.md).

---

## 1. Strategic pivot

| Before | After |
|--------|-------|
| Developer CLI + Python library | Free, source-available **desktop application** |
| Hypothesis: AI emits Sheet DSL JSON from prompts | **AI edits `scenes.py`** on the user's behalf (mini-Cursor) |
| `matemium render` as primary UX | **Code editor + AI chat + render** in a Tauri shell |
| Repo is the product | Repo is the **local compilation engine** packaged inside the desktop app |

The repository layout (`canvas/`, `projects/`, `matemium/`, etc.) **stays intact**:

- **`canvas/`** — frozen into a platform-specific **PyInstaller sidecar**; the render farm on the user's machine.
- **`projects/`** — dev harness and engine stress tests; mirrors the desktop **single-file project** model.
- **`matemium/`** — dev/CI CLI today; sidecar IPC for production renders and lint/check.

---

## 2. Design principles

These are non-negotiable product rules. All new desktop, cloud, and engine work must respect them.

### 2.1 Code is the authoring surface

- End users work in a **project workspace** with a **single Python file** (`scenes.py`) that defines their animation.
- Authoring uses **`CanvasBuilder` + `CanvasScene`** — the same API documented in [`canvas/USAGE.md`](canvas/USAGE.md).
- Users do **not** write raw Manim. They write Matemium scene code; the engine compiles to an internal `SheetDSL` via `builder.build()`.

### 2.2 AI edits code, not JSON

- Third-party LLMs integrated via **chat APIs** return **natural language + code edits** (diffs / replace blocks), **not** Sheet DSL JSON or builder-op JSON.
- External providers are preferred by default. OpenRouter is the default provider because it gives users one independent account for many model families.
- Matemium does not provide pooled model API keys, prepaid in-app AI tokens, or Matemium-owned model quotas. Users bring their own API keys and can add/select multiple providers.
- The cloud is a **thin optional router/helper** (auth/profile sync, provider selection metadata, optional BYO request forwarding). It does not compile, preview, render animations, or own model spend.
- **Robustness parity:** AI and the human edit the **same file** and run through the **same** import → lint → render pipeline.

### 2.3 Authoring modes: script + project brief

- **v1 chat default:** one `scenes.py` per project. Maximizes reliability for API-only integrations (one render entrypoint, no cross-file import routing).
- **Visual multi-section UI** on top of `scenes.py` (see §5) — prettier editing without hiding that the renderable artifact is Python code.
- **Agent/project mode:** `scenes.py` remains the render entrypoint, `helpers.py` holds reusable Python computations, and `brief/` holds structured creative intent, narration, roadmap, and media references. See [`ai-agent-architecture.md`](ai-agent-architecture.md) §7.
- Agent mode unlocks the **tool loop** (view/edit/compile), Search/Replace patches, project-brief editing, and autonomous self-correction — not unconstrained repo sprawl.

**Note:** Later product decisions on sidecar bootstrapping, lazy loading of Manim/embeddings, first-run model downloads, and strict UX gating are documented in [`PRODUCT-ARCHITECTURE-DECISIONS.md`](PRODUCT-ARCHITECTURE-DECISIONS.md).

### 2.4 Local render only

- All Manim compilation and video encoding runs on the user's CPU/GPU.
- No cloud rendering, no render farms, no uploaded scene assets for compute.
- Cloud ops cost scales with optional auth/profile features, not render minutes, storage, or model resale.

### 2.7 Free Use And Source Availability

- Matemium is completely free to use.
- The source code is publicly available for inspection, personal use, education, and contribution to the official project.
- Private modifications are permitted.
- Redistribution, publication of derivative builds, commercial use, and operation of competing forks require written permission.

### 2.5 Engine stays generic

- Topic-specific patterns live in **project code** (`helpers.py` when reused), never in `canvas/`.
- No `canvas/extensions/` package tier (see [`architecture.md`](architecture.md) §6).

### 2.6 SheetDSL is internal IR only

- `SheetDSL` remains the compiled timeline inside `builder.build()`.
- It is **not** the product authoring format and **not** what AI emits over the network.
- Raw `SheetDSL` JSON IPC commands (`validate_dsl`, `render` with inline `dsl`) remain for **dev, tests, and fixtures** — not the primary desktop authoring path.

---

## 3. Product goals

### 3.1 What we are building

A desktop app where a user creates a **project**, edits **`scenes.py`** in a syntax-highlighted editor (with linters), chats with AI to refine the code, and renders a polished **9:16 math reel** locally — without installing Python or managing Manim themselves.

### 3.2 Primary goals

1. **Project workspaces** — create, open, save projects; each project has one canonical `scenes.py`, optional `helpers.py`, and a first-class `brief/` workspace.
2. **Code editor** — Python syntax highlighting, diagnostics (ruff / `py_compile`), section-aware navigation.
3. **AI chat canvas** — v1: user prompts; AI proposes edits to `scenes.py`; user reviews/applies diffs. **v2 agent:** autonomous tool loop (view/edit/compile + self-correction) — see [`ai-agent-architecture.md`](ai-agent-architecture.md).
4. **Zero cloud rendering** — sidecar runs all Manim/LaTeX/FFmpeg work locally.
5. **Preview-first UX** — lint/check before render; streamed progress during render; playback in-app.

**Live Preview uses manim-web:** The "Live Preview" bottom tab is powered by [manim-web](https://github.com/maloyan/manim-web) (browser-native Manim port using WebGL/Three.js + KaTeX for MathTex). The Python engine still supplies authoritative layout via the `get_preview_data` IPC (positions/sizes computed by `LayoutEngine` + `CanvasBuilder` on the exact same `scenes.py`). This was the design goal from the beginning: accurate Python measurement + faithful animated preview in the desktop without requiring a full video render for every change. The custom DOM measurement renderer is superseded by the manim-web player.

**Future direction (Phase 0+):** The preview will become a true 3D manim-web renderer. The sheet/tape will be treated as one special object (`TapeObject`) inside an infinite 3D world. When the camera targets a tape, the preview re-uses/enhances the high-fidelity sheet logic on that plane while still supporting full 3D camera motion and other objects. See `canvas/3D-model.md` and the 3D unification plan.
6. **Cross-platform shipping** — Windows (MSI/EXE), macOS (DMG), Linux (AppImage/DEB). One shared TS/Rust codebase; **per-platform PyInstaller sidecars** via CI matrix (sidecars cannot be cross-compiled).
7. **Free distribution** — no subscriptions, no paid tiers, no Matemium AI credits; users pay external providers directly when they choose cloud AI.

### 3.3 Non-goals (explicit)

- **No cloud video rendering** — ever.
- **No browser-only product** — Manim + LaTeX + FFmpeg require a native shell and sidecar.
- **No AI → Sheet DSL JSON** as the primary authoring path.
- **No raw Manim** as user output.
- **No unconstrained multi-file repos** in v1 API-chat mode.

---

## 4. Project workspace model

Each user project maps to a directory on disk (app data dir, not the dev repo):

```
~/Matemium/workspaces/<project-id>/
├── project.json       # app metadata: id, title, scene class, orientation, timestamps
├── scenes.py          # render entrypoint and visual timeline (required)
├── helpers.py         # reusable Python helpers imported by scenes.py
├── brief/
│   ├── passport.json  # structured creative/production identity
│   ├── description.md # human-readable project brief
│   ├── tape.md        # director's tape plan: beats, comments, camera/reveal notes
│   ├── roadmap.json   # phases, completion, current focus, blockers
│   └── narration.md   # voiceover, captions, timing and pronunciation notes
├── assets/
│   ├── images/
│   ├── video/
│   └── audio/
└── renders/           # app-managed output dirs
```

`authoring_mode`: `"single_file"` for the simplest path, `"project_brief"` when `helpers.py`, `brief/`, and media management are enabled. Templates live under [`shared/templates/`](shared/templates/). Historical `assets.py` workspaces should migrate to `helpers.py`; `assets` is reserved for real project/media assets and app-managed downloadable runtime assets.

### 4.1 Project brief file roles

| File | Owner | Purpose | UI treatment |
|------|-------|---------|--------------|
| `project.json` | App | Identity, scene class, orientation, timestamps | Settings form; not a general editor |
| `scenes.py` | Human + AI | Executable visual timeline | Primary code editor with section outline |
| `helpers.py` | Human + AI | Computations, LaTeX helpers, geometry/data builders | Secondary code editor |
| `brief/passport.json` | Human + AI | Topic, audience, difficulty, style, duration, language, constraints, learning goals | Form editor with JSON fallback |
| `brief/description.md` | Human + AI | Freeform project brief and intent | Markdown editor |
| `brief/tape.md` | Human + AI | Full tape plan with comments about what happens and how it appears in video | Markdown editor with beat navigation |
| `brief/roadmap.json` | AI-owned, human-readable | Phases, completion, current working point, blockers | Read-only production route; users steer changes through AI |
| `brief/narration.md` | Human + AI | Voiceover, captions, timing notes, pronunciation | Markdown/script editor |
| `assets/*` | Human + AI | User-provided images, video, audio | Asset browser with preview |

The `brief/` files are not rendered directly. They are persistent project memory for the user, the UI, and the AI agent. `scenes.py` is still the only required render entrypoint.

**Dev repo equivalent:**

```
projects/<slug>/scenes.py   →   matemium render <slug>
```

The sidecar sets `MATEMIUM_ROOT` (or equivalent) to the workspace root so `import helpers` and render match CLI behavior.

### 4.2 Required UI navigation model

The UI must make this structure feel like one coherent project, not a file tree dumped on the user:

- **Project sidebar:** the persistent left panel shows the current project structure as a navigable tree/outline, not just a project switcher. It must expose `scenes.py`, `helpers.py`, `brief/`, `assets/`, and `renders/` with clear icons, selection state, dirty state, validation badges, and collapsed/expanded folders.
- **Top-level sidebar groups:** Script, Helpers, Brief, Assets, Renders. Projects/workspace switching can live above this tree or in a compact header, but once a project is open the sidebar's main job is navigating that project's files and production state.
- **Script view:** `scenes.py` as the default first screen, with section outline, diagnostics, render controls, and AI patch review.
- **Helpers view:** `helpers.py` for advanced reusable code; visible but secondary.
- **Brief view:** tabs/indexes for Passport, Description, Tape, Roadmap, and Narration. Passport gets a friendly form, Markdown files get an editor with preview, and Roadmap is an AI-owned read-only production route with no raw JSON escape hatch.
- **Assets view:** source images, video, and audio grouped by type with thumbnails/previews and clear import/reference actions for `scenes.py`. Keep these under `assets/`; `<workspace>/media/` is reserved for generated Manim cache data.
- **Renders view:** app-managed render outputs, latest preview, export/cut artifacts, and render history.
- **AI context:** the agent can read and update the brief deliberately, but code changes still flow through `scenes.py`/`helpers.py` and compile verification.
- **Progress affordance:** `brief/roadmap.json` drives a visible current phase/current task indicator so the user always knows what the project is working on.

Navigation must be dense, predictable, and fast. Avoid marketing-style pages inside the workspace; the first screen is the usable script/project workspace.

The project sidebar should not behave like a raw OS file explorer. It is a curated production map:

```
Current Project
├── Script
│   └── scenes.py
├── Helpers
│   └── helpers.py
├── Brief
│   ├── Passport
│   ├── Description
│   ├── Tape
│   ├── Roadmap
│   └── Narration
├── Assets
│   ├── Images
│   ├── Video
│   └── Audio
└── Renders
    ├── Latest
    └── History
```

Selecting a sidebar item opens the correct purpose-built surface, not always a plain text editor. For example, Passport opens a form, Roadmap opens a checklist/phase view, Tape and Narration open Markdown/script editors, and Assets opens a browser with previews.

### 4.3 Recommended `scenes.py` structure

Split the lesson into **top-level `part_*` functions** plus a thin `CanvasScene` class:

```python
# ---DIV: Scene parts---
def part_intro(b: CanvasBuilder) -> None: ...
def part_graph(b: CanvasBuilder) -> None: ...

# ---DIV: Main scene---
class MyVideo(CanvasScene):
    def __init__(self, **kwargs):
        b = CanvasBuilder(title="MyVideo")
        part_intro(b)
        part_graph(b)
        super().__init__(dsl=b.build(), **kwargs)
```

Multiple `CanvasScene` subclasses in one file are allowed; the UI picks which scene to render.

---

## 5. Visual sections (one file, multi-pane UX)

The editor presents **collapsible section fences** while persisting **one valid Python file**.

### 5.1 Section markers

Place a comment immediately before each top-level `def` or `class`:

```python
# ---DIV: Intro---
def part_intro(b: CanvasBuilder) -> None:
    ...
```

- Markers are **comments only** — Python ignores them.
- The UI parses `# ---DIV: <title>---` (and/or AST top-level symbols) to build an outline and toggleable cards.
- Collapsing a section **folds** editor ranges; it does not delete text.

### 5.2 Editor modes

| Mode | v1 | Later |
|------|-----|-------|
| Single buffer + outline + fold fences | **Yes** | — |
| Virtual per-section panes stitched on save | — | Optional polish |

### 5.3 AI targeting

Chat context includes:

- Full `scenes.py` (bounded by single-file rule)
- Parsed **section map** (DIV titles + function names + line ranges)
- Last lint/render errors

The model patches **one file**, optionally scoped by section name in the user prompt.

---

## 6. System boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLOUD (thin)                                   │
│  Optional auth · profile sync · BYO provider helpers · text / code edits    │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTPS
                                    │ Request:  prompt + session + file context
                                    │ Response: assistant text + code patches
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DESKTOP APP (Tauri v2)                              │
│                                                                             │
│  ┌──────────────────┐    invoke/events    ┌──────────────────────────┐   │
│  │ TypeScript UI    │◄────────────────────►│ Rust core (orchestrator)  │   │
│  │ Code editor      │                     │ Projects · sidecar · FS   │   │
│  │ AI chat · preview│                     │ Diff apply · job dirs     │   │
│  └──────────────────┘                     └─────────────┬────────────┘   │
│                                                         │                   │
│                              stdin/stdout NDJSON        │                   │
│                                                         ▼                   │
│                        ┌────────────────────────────────────────────┐        │
│                        │ PyInstaller sidecar (matemium-sidecar)   │        │
│                        │ lint → import scenes.py → render → mp4 │        │
│                        └────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.1 Cloud middleware

| In scope | Out of scope |
|----------|--------------|
| User authentication | Video encoding |
| User-owned provider key selection metadata | Manim execution |
| Abuse/rate protection for Matemium endpoints | DSL validation / layout |
| Optional forwarding to third-party LLMs using the user's key | Storing rendered media long-term |
| OpenRouter OAuth callback/key exchange support | Selling model access or pooled API access |
| Returning **text + structured code edits** | Hosting LaTeX/FFmpeg |

**Chat pipeline (v1):**

1. Desktop sends user message + auth token + `scenes.py` snapshot (+ optional selection, section map, last errors).
2. Desktop/server selects the user's preferred provider and model. OpenRouter is the default external provider. System prompt includes Matemium `CanvasBuilder` API constraints ([`canvas/USAGE.md`](canvas/USAGE.md), [`shared/prompts/scene-authoring-system.txt`](shared/prompts/scene-authoring-system.txt)).
3. LLM returns assistant message + **edit blocks** (Search/Replace or unified diff).
4. Desktop shows diff; user applies to editor buffer; save writes `scenes.py`.

**Agent pipeline (v2):** context bundle → tool calls → local patch engine + sidecar compile → self-correction loop. System prompt: [`shared/prompts/agent-system.txt`](shared/prompts/agent-system.txt). Full spec: [`ai-agent-architecture.md`](ai-agent-architecture.md).

The cloud never sees the user's GPU output. It may see project **source code** the user sends for assistance (same trust model as Cursor/Copilot). Provider API keys should be stored locally whenever possible; if cloud storage is used for cross-device sync, keys must be encrypted and treated as user secrets.

### 6.2 Desktop client

| Layer | Technology | Role |
|-------|------------|------|
| UI | TypeScript (WebView) | Project list, Monaco editor, section outline, AI chat, diff review, video player |
| Shell | Tauri v2 (Rust) | Window, FS, project CRUD, sidecar lifecycle, secure IPC |
| Engine | Python sidecar | `lint_project`, `check_project`, `render_project`, progress events |

### 6.3 Repository engine (`canvas/`)

Deterministic compilation: same `scenes.py` → same video, whether run via CLI, sidecar, or tests.

| Entry | Use |
|-------|-----|
| **Desktop production** | `render_project` / `check_project` on workspace `scenes.py` |
| **Development** | `matemium render`, `projects/*/scenes.py`, pytest |
| **Dev / fixtures** | Inline `dsl` IPC (`validate_dsl`, `render`) for tests and engine debugging |

---

## 7. Developer design paradigm

```
TypeScript  ──(Tauri invoke)──►  Rust  ──(IPC)──►  Python sidecar
     ▲                              │                    │
     └──────── progress events ─────┴────────────────────┘
```

### 7.1 Rules

1. **TypeScript never imports Python** — UI talks only to Rust.
2. **Rust never embeds Manim** — all engine logic stays in the sidecar.
3. **Authoring artifact is `scenes.py`** — not inline DSL payloads from the UI.
4. **IPC uses JSON lines** for commands/events — not for animation authoring.
5. **Progress is streamed** — `lint_*`, `check_*`, `render_*` emit structured events.
6. **Lint before render** — `py_compile` / ruff + import check before Manim/LaTeX spend.
7. **Error feedback loop** — render stderr is available to AI chat as fix context.

### 7.2 Sidecar IPC — project commands (primary desktop path)

| Command | Input | Output |
|---------|-------|--------|
| `ping` | — | `{ ok, version, protocol, engine }` |
| `lint_project` | `{ workspace, path? }` | `{ diagnostics[] }` |
| `check_project` | `{ workspace, scene? }` | `{ ok, errors[], scene }` — import without full render |
| `list_scenes` | `{ workspace }` | `{ scenes[] }` |
| `render_project` | `{ workspace, scene?, quality, output_dir }` | `{ video, workspace, duration_estimate }` |
| `export_sheet` | `{ workspace, scene?, format }` | `{ path, format }` |
| `cut_reels` | `{ video, workspace, scene? }` | `{ reels[], manifest }` |
| `compile_preview`, `estimate_duration` | ... | Progress + preview assets / timing |
| `get_preview_data` | `{ projectId }` (via workspace) | `{ elements[], frame_width, frame_height, ... }` — layout snapshot for WYSIWYG + manim-web preview |

**Legacy / dev commands** (inline DSL, not desktop authoring):

| Command | Use |
|---------|-----|
| `validate_dsl`, `render` with `dsl` | Tests, fixtures, engine debugging |

Exact wire schema: [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md).

### 7.3 AI integration tiers

| Tier | Integration | Project shape |
|------|-------------|---------------|
| **v1 — Chat API** | Completions + optional Search/Replace diffs | **Single `scenes.py`** |
| **v2 — Agent** | Tool loop (`view_file`, `edit_file`, `compile_manim`) + self-correction | **`scenes.py` + `helpers.py` + `brief/`** |

Full agent spec: [`ai-agent-architecture.md`](ai-agent-architecture.md).

---

## 8. Data flow: edit to reel

```
User edits scenes.py (or accepts AI diff)
    │
    ▼
[TS UI] Save → [Rust] workspace/scenes.py
    │
    ├─► [Sidecar] lint_project / check_project  ──► diagnostics in editor
    │
    └─► [Sidecar] render_project
              │
              ├─ import scenes.py → CanvasScene
              ├─ builder.build() → SheetDSL (internal)
              ├─ CanvasScene → Manim render
              └─ optional ReelCutter
    │
    ▼
Local .mp4 → [TS UI playback / export]

Parallel chat path (v1):
User prompt → [Cloud LLM] → code patch → diff UI → scenes.py (same file)

Agent path (v2):
User prompt → [Context bundler] → [LLM tool loop] → patch engine → sidecar compile
              ↑___________________________________| (self-correction on stderr)
```

---

## 9. Cross-platform build model

Tauri delivers **one shared codebase** for Windows, macOS, and Linux. The PyInstaller sidecar does **not** follow that rule — it must be built **natively on each target OS**.

| What ships | Shared? | How |
|------------|---------|-----|
| TypeScript UI + Rust shell | Yes | Same `desktop/` tree; `cargo tauri build` on each runner |
| `matemium-sidecar` binary | **No** | PyInstaller on Windows / macOS / Linux separately |
| Final installer | Per OS | Tauri bundles only the matching `externalBin` triple |

```
desktop/src-tauri/binaries/
├── matemium-sidecar-x86_64-pc-windows-msvc.exe
├── matemium-sidecar-x86_64-apple-darwin
├── matemium-sidecar-aarch64-apple-darwin
└── matemium-sidecar-x86_64-unknown-linux-gnu
```

**CI/CD:** GitHub Actions (or equivalent) runs a **build matrix** — three virtual machines per release (Windows, macOS, Linux). You cannot produce a macOS `.dmg` from a Windows dev laptop. Linux CI exists ([`.github/workflows/build-linux.yml`](.github/workflows/build-linux.yml)); Windows and macOS workflows are still required for full ship.

**OS quirks for consistent UX:**

- **Window controls** — macOS traffic lights are top-left; Windows/Linux are top-right. Reserve title-bar padding in CSS; Tauri handles native chrome.
- **Paths** — use `PathBuf` / `os.path.join` / `pathlib.Path`; never hardcode `\` or `/`. Agent tools use logical filenames; Rust resolves workspace roots per platform.

Full build guide: [`desktop/targets/README.md`](desktop/targets/README.md).

## 10. Build phases

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **P0 — Document** | This file + cross-links | done |
| **P1 — Sidecar** | `matemium-sidecar`, `matemium/ipc/` | done (DSL commands); project commands planned |
| **P2 — Tauri scaffold** | `src-tauri/`, sidecar lifecycle, `invoke` bridge | pending |
| **P3 — UI shell** | Project list, Monaco editor, section outline, AI chat, diff apply | pending |
| **P4 — PyInstaller** | Per-platform sidecar binaries | pending |
| **P5 — Cloud client** | Auth + chat API stub (mockable offline) | pending |
| **P6 — Ship** | Code signing, auto-update, store packages | pending |
| **P7 — CI matrix** | Windows + macOS + Linux release workflows | Linux done; Win/Mac pending |

---

## 11. What stays the same

From [`architecture.md`](architecture.md):

- Sheet-first camera on the XY plane at `z = 0`
- `SheetDSL` as compiled IR inside `builder.build()`
- CSS-like `style={}` and flex layout
- `MobjectRegistry` for persistent re-animation
- Portrait-first 9:16 output with reel cutting
- Two layers: `canvas/` (engine) + project code (lessons)

---

## 12. Success criteria

1. A user can create a project, edit `scenes.py` (with AI chat), and render a reel **without installing Python**.
2. AI edits and manual edits use the **same file** and **same render pipeline**.
3. Cloud bill scales with **auth + chat**, not render minutes.
4. Sidecar renders `projects/demo` scenes with parity to `matemium render demo`.
5. Section fences make long `scenes.py` files navigable without splitting files (v1).
6. TypeScript ↔ Rust ↔ Python boundary has no leaks in code review.

---

## 13. Related documents

| Document | Scope |
|----------|-------|
| [`architecture.md`](architecture.md) | Engine design, §8 desktop summary |
| [`project-spec.md`](project-spec.md) | Module map, feature status |
| [`canvas/USAGE.md`](canvas/USAGE.md) | `CanvasBuilder` API — human + AI system prompts |
| [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md) | Sidecar wire protocol |
| [`ai-agent-architecture.md`](ai-agent-architecture.md) | Autonomous agent: tools, patches, self-correction, TinyTeX |
| [`desktop/targets/README.md`](desktop/targets/README.md) | Cross-platform builds, CI matrix, sidecar triples |
| [`README.md`](README.md) | Repo overview and dev quick start |
