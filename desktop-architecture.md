# Matemium Desktop — Product Architecture & Goals

**Status:** Authoritative (2026-06-26)  
**Audience:** All contributors — engine, desktop shell, cloud middleware, and AI integration authors.

This document records the **strategic pivot** to a **commercial/freemium desktop application** where users author animations as **Python project code** assisted by an **AI chat** — not as cloud-generated JSON specs. Engine internals remain in [`architecture.md`](architecture.md); feature status in [`project-spec.md`](project-spec.md).

---

## 1. Strategic pivot

| Before | After |
|--------|-------|
| Open-source developer CLI + Python library | Commercial/freemium **desktop application** |
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
- The cloud is a **thin chat router** (auth, billing, entitlements). It does not compile, preview, or render animations.
- **Robustness parity:** AI and the human edit the **same file** and run through the **same** import → lint → render pipeline.

### 2.3 Authoring modes: single file (v1) → two file (agent)

- **v1 chat default:** one `scenes.py` per project. Maximizes reliability for API-only integrations (one buffer, no cross-file import routing).
- **Visual multi-section UI** on top of the single file (see §5) — prettier editing without multi-file complexity.
- **v2 agent mode:** strict **two-file boundary** — `scenes.py` (visual timeline) + `assets.py` (computations and data). See [`ai-agent-architecture.md`](ai-agent-architecture.md) §7.
- Agent mode unlocks the **tool loop** (view/edit/compile), Search/Replace patches, and autonomous self-correction — not optional multi-file sprawl.

### 2.4 Local render only

- All Manim compilation and video encoding runs on the user's CPU/GPU.
- No cloud rendering, no render farms, no uploaded scene assets for compute.
- Cloud ops cost scales with **auth + chat API calls**, not render minutes or storage.

### 2.5 Engine stays generic

- Topic-specific patterns live in **project code** (or later `helpers.py`), never in `canvas/`.
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

1. **Project workspaces** — create, open, save projects; each project has one canonical `scenes.py` (v1).
2. **Code editor** — Python syntax highlighting, diagnostics (ruff / `py_compile`), section-aware navigation.
3. **AI chat canvas** — v1: user prompts; AI proposes edits to `scenes.py`; user reviews/applies diffs. **v2 agent:** autonomous tool loop (view/edit/compile + self-correction) — see [`ai-agent-architecture.md`](ai-agent-architecture.md).
4. **Zero cloud rendering** — sidecar runs all Manim/LaTeX/FFmpeg work locally.
5. **Preview-first UX** — lint/check before render; streamed progress during render; playback in-app.
6. **Cross-platform shipping** — Windows (MSI/EXE), macOS (DMG), Linux (AppImage/DEB). One shared TS/Rust codebase; **per-platform PyInstaller sidecars** via CI matrix (sidecars cannot be cross-compiled).
7. **Freemium monetization** — cloud handles auth, entitlements, billing; meter chat (and optionally renders).

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
├── scenes.py          # visual timeline (required)
├── assets.py          # engine room — agent mode only (v2)
├── project.json       # title, scene class, authoring_mode
└── (renders via sidecar → app-managed output dirs)
```

`authoring_mode`: `"single_file"` (v1 chat) or `"two_file"` (v2 agent). Templates: [`shared/templates/scenes.py`](shared/templates/scenes.py), [`shared/templates/assets.py`](shared/templates/assets.py).

**Dev repo equivalent:**

```
projects/<slug>/scenes.py   →   matemium render <slug>
```

The sidecar sets `MATEMIUM_ROOT` (or equivalent) to the workspace root so `import` and render match CLI behavior.

### 4.1 Recommended `scenes.py` structure

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
│  Auth · Billing · Entitlements · Chat LLM routing · text / code edits only  │
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
| Subscription / credit entitlements | Manim execution |
| Rate limiting per plan | DSL validation / layout |
| Forwarding chat to third-party LLMs | Storing rendered media long-term |
| Returning **text + structured code edits** | Hosting LaTeX/FFmpeg |

**Chat pipeline (v1):**

1. Desktop sends user message + auth token + `scenes.py` snapshot (+ optional selection, section map, last errors).
2. Cloud selects model; system prompt includes Matemium `CanvasBuilder` API constraints ([`canvas/USAGE.md`](canvas/USAGE.md), [`shared/prompts/scene-authoring-system.txt`](shared/prompts/scene-authoring-system.txt)).
3. LLM returns assistant message + **edit blocks** (Search/Replace or unified diff).
4. Desktop shows diff; user applies to editor buffer; save writes `scenes.py`.

**Agent pipeline (v2):** context bundle → tool calls → local patch engine + sidecar compile → self-correction loop. System prompt: [`shared/prompts/agent-system.txt`](shared/prompts/agent-system.txt). Full spec: [`ai-agent-architecture.md`](ai-agent-architecture.md).

The cloud never sees the user's GPU output. It may see project **source code** the user sends for assistance (same trust model as Cursor/Copilot).

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

**Legacy / dev commands** (inline DSL, not desktop authoring):

| Command | Use |
|---------|-----|
| `validate_dsl`, `render` with `dsl` | Tests, fixtures, engine debugging |

Exact wire schema: [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md).

### 7.3 AI integration tiers

| Tier | Integration | Project shape |
|------|-------------|---------------|
| **v1 — Chat API** | Completions + optional Search/Replace diffs | **Single `scenes.py`** |
| **v2 — Agent** | Tool loop (`view_file`, `edit_file`, `compile_manim`) + self-correction | **`scenes.py` + `assets.py` only** |

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