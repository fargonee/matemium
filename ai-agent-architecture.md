# Matemium AI Agent Architecture

**Status:** Authoritative (2026-06-26)  
**Audience:** Desktop shell, cloud router, sidecar, and AI integration authors.

This document records how Matemium upgrades from a **standard chat canvas** (LLM returns markdown code blocks the user copies) to an **autonomous, file-aware AI coding agent** — similar to Cursor or Claude Code — specialized for Manim/Matemium scene authoring.

**Related:** [`desktop-architecture.md`](desktop-architecture.md) (product boundaries), [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md) (sidecar wire format), [`shared/prompts/agent-system.txt`](shared/prompts/agent-system.txt) (agent system prompt).

---

## 1. Strategic shift

| Before (v1 chat canvas) | After (agent mode) |
|---------------------------|-------------------|
| LLM returns prose + optional diff blocks | LLM **calls tools** to inspect, edit, and compile |
| User applies diffs manually | Backend applies **Search/Replace patches** to editor state |
| User triggers render | Agent calls **`compile_manim`** and reads stderr |
| Single-turn chat | **Self-correction loop** until compile succeeds |
| One `scenes.py` buffer | Strict **two-file boundary**: `scenes.py` + `assets.py` |

The cloud remains a **thin LLM router** (auth, billing, entitlements). The desktop owns file state, patch application, sidecar lifecycle, and render feedback. **No cloud rendering.**

---

## 2. Agent tool surface (function calling)

The LLM receives structured tools — not raw shell access. Wrap backend Python/Rust functions as OpenAI-compatible function definitions. Frameworks like LangGraph or LangChain may orchestrate the loop; the wire contract is what matters.

### 2.1 Core tools

| Tool | Purpose | Backend mapping |
|------|---------|-----------------|
| `view_file(filename)` | Return current code so the agent has context | Read workspace buffer (`scenes.py` or `assets.py`) |
| `edit_file(filename, instructions, patches)` | Apply localized edits | Parse Search/Replace blocks → update editor buffer |
| `compile_manim(filename, scene_name, quality)` | Verify animation compiles | Sidecar `check_project` + `render_project` (or preview quality) |

**Allowed `filename` values (strict):** `scenes.py`, `assets.py` only. No other paths.

### 2.2 Tool schemas (reference)

```json
{
  "name": "view_file",
  "parameters": {
    "type": "object",
    "properties": {
      "filename": { "type": "string", "enum": ["scenes.py", "assets.py"] }
    },
    "required": ["filename"]
  }
}
```

```json
{
  "name": "edit_file",
  "parameters": {
    "type": "object",
    "properties": {
      "filename": { "type": "string", "enum": ["scenes.py", "assets.py"] },
      "instructions": { "type": "string", "description": "One-line summary of the edit intent" },
      "patches": {
        "type": "string",
        "description": "One or more SEARCH/REPLACE blocks (see §4)"
      }
    },
    "required": ["filename", "patches"]
  }
}
```

```json
{
  "name": "compile_manim",
  "parameters": {
    "type": "object",
    "properties": {
      "filename": { "type": "string", "enum": ["scenes.py"] },
      "scene_name": { "type": "string" },
      "quality": {
        "type": "string",
        "enum": ["preview", "draft", "low", "medium", "high", "final"],
        "default": "preview"
      }
    },
    "required": ["filename", "scene_name"]
  }
}
```

`compile_manim` always targets `scenes.py` — the entry file the sidecar imports. `assets.py` is imported by `scenes.py` when needed.

### 2.3 Who executes tools

| Tool | Executor | Notes |
|------|----------|-------|
| `view_file` | Desktop (Rust) | Reads saved workspace files; includes unsaved buffer if newer |
| `edit_file` | Desktop (Rust) | Patch engine applies blocks; pushes update to Monaco |
| `compile_manim` | Sidecar (Python) | Async IPC; streams progress events (§8.B) |

The cloud LLM **proposes** tool calls. The desktop **executes** them and returns tool results to the agent loop (local orchestrator or cloud round-trip).

---

## 3. Context engine (smart context gathering)

On every user prompt, the frontend bundles what the user sees so the agent does not hallucinate file state.

### 3.1 Context bundle

| Field | Source | Example |
|-------|--------|---------|
| `scenes.py` | Editor buffer (saved or dirty) | Full file text |
| `assets.py` | Secondary drawer buffer | Full file text (empty template if new project) |
| `active_file` | Focused editor pane | `"scenes.py"` |
| `cursor` | Monaco caret | `{ "line": 42, "column": 8 }` |
| `selection` | Highlighted range | `{ "start_line": 14, "end_line": 22, "text": "..." }` |
| `section_map` | Parsed `# ---DIV: ...---` fences | `[{ "title": "Intro", "symbol": "part_intro", "start_line": 12, "end_line": 28 }]` |
| `scene_class` | `project.json` | `"MyScene"` |
| `last_lint` | Sidecar `lint_project` | `{ "diagnostics": [...] }` |
| `last_compile` | Sidecar `check_project` / `render_project` | `{ "ok": false, "stderr": "...", "traceback": "..." }` |

### 3.2 Selection hint for the model

When the user highlights code, inject a human-readable scope line into the user message:

```
The user has highlighted lines 14–22 in scenes.py (function part_intro).
```

### 3.3 Error-first priority

If `last_compile.ok === false`, the context bundle **must** include the full traceback/stderr before the user's new instruction. The agent fixes compile errors before making unrelated edits.

---

## 4. Search & Replace patch protocol

Do **not** let the LLM rewrite entire 300-line files for small tweaks. Force localized edits in a strict, parseable format (Aider-style).

### 4.1 Block format

````
<<<<<<< SEARCH
        circle = Circle(color=BLUE)
        self.play(Create(circle))
=======
        circle = Circle(color=RED)
        square = Square(color=BLUE).next_to(circle, RIGHT)
        self.play(Create(circle), FadeIn(square))
>>>>>>> REPLACE
````

For Matemium authoring, patches target `CanvasBuilder` calls inside `part_*` functions — not raw Manim.

### 4.2 Patch engine rules

1. **Exact match** — SEARCH text must match the buffer byte-for-byte (including indentation).
2. **Unique match** — if SEARCH appears more than once, reject and return `AMBIGUOUS_PATCH` to the agent.
3. **Multiple blocks** — apply in order; each block is independent.
4. **No full-file rewrites** — reject `edit_file` payloads that omit SEARCH/REPLACE markers unless `force_full_file` is explicitly enabled for new projects only.
5. **Instant UI sync** — after apply, push the updated buffer to Monaco before the next tool call.

### 4.3 Tool result on failure

```json
{
  "ok": false,
  "error": "PATCH_NOT_FOUND",
  "message": "SEARCH block did not match scenes.py",
  "hint": "Call view_file and retry with more surrounding context lines"
}
```

---

## 5. Self-correction loop

Manim/Matemium code fails often (syntax, stale APIs, LaTeX errors). The agent architecture handles this autonomously.

```
[User Prompt]
      │
      ▼
[Context Bundler]
      │
      ▼
[LLM: edit_file / compile_manim]
      │
      ▼
[Patch Engine] ──► [Sidecar compile]
      │                    │
      │              [stderr/traceback?]
      │                 /        \
      │              (yes)        (no)
      │               /              \
      ▼              ▼                ▼
[Feed error back to LLM]      [Show video + final reply]
      │
      └──► (retry edit_file → compile_manim, max N attempts)
```

### 5.1 Loop policy

| Parameter | Default | Notes |
|-----------|---------|-------|
| `max_compile_retries` | 5 | Per user turn |
| `retry_quality` | `preview` | Fast feedback; upgrade to `medium` on success if user requested final |
| `stop_condition` | `compile_manim` returns `ok: true` | Agent may respond to user only after verified compile |

### 5.2 `compile_manim` tool result

Success:

```json
{
  "ok": true,
  "video": "/path/to/MyScene.mp4",
  "duration_estimate": 12.5,
  "scene": "MyScene"
}
```

Failure:

```json
{
  "ok": false,
  "code": "COMPILE_ERROR",
  "stderr": "...",
  "traceback": "Traceback (most recent call last):\n  File ...",
  "lint_diagnostics": []
}
```

The orchestrator appends the failure payload as the tool result; the LLM analyzes traceback and issues another `edit_file`.

---

## 6. Agent lifecycle (single request)

```
+------------------+
|    User Input    |
+--------+---------+
         |
         v
+-------------------------------------------------------------+
| Context Bundler: editor text + selection + last errors      |
+--------+----------------------------------------------------+
         |
         v
+-------------------------------------------------------------+
| LLM Agent: selects tool (view_file / edit_file / compile)   |
+--------+----------------------------------------------------+
         |
         v
+-------------------------------------------------------------+
| Patch Engine: applies Search/Replace to editor buffer       |
+--------+----------------------------------------------------+
         |
         v
+-------------------------------------------------------------+
| Manim Tool: sidecar render + capture logs/video             |
+--------+----------------------------------------------------+
         |
    [Has Error?]
     /        \
  (Yes)       (No)
   /            \
  v              v
+-----------------------+   +-----------------------+
| Feed traceback to LLM |   | Render video in UI    |
| for hot-fix           |   | + assistant message   |
+-----------------------+   +-----------------------+
```

---

## 7. Two-file project boundary (`scenes.py` + `assets.py`)

Agent mode enforces a **strict two-file workspace**. This is the commercial sweet spot for Matemium desktop — not the dev-repo `helpers.py` pattern.

### 7.1 File roles

| File | Role | UI surface |
|------|------|------------|
| **`scenes.py`** | **The Timeline** — `# ---DIV: ---` section markers, `part_*` functions, `CanvasScene` class, readable `CanvasBuilder` layout | Main **Visual Script Workspace** (section cards) |
| **`assets.py`** | **The Engine Room** — raw computations, coordinate arrays, custom LaTeX groupings, heavy 3D mesh definitions, reusable data helpers | Secondary **Advanced Assets Drawer** |

```python
# scenes.py — visual narrative only
from assets import parabola_samples, matrix_tex

def part_graph(b: CanvasBuilder) -> None:
    xs, ys = parabola_samples(a=1, b=-2, c=1)
    b.add_math(matrix_tex)
    ...
```

```python
# assets.py — computations and data (no CanvasScene)
def parabola_samples(a: float, b: float, c: float, *, n: int = 50):
    ...

def matrix_tex() -> str:
    return r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}"
```

### 7.2 Why two files (not unlimited)

| Benefit | Explanation |
|---------|-------------|
| **Separation of concerns** | Visual timeline vs. math engine room |
| **UI sync** | Predictable dual-pane layout — no tab explosion |
| **Agent reliability** | Two targets reduce import loops and duplicate utility files |
| **Token economics** | Context payload stays small and predictable for cloud routing |

### 7.3 Agent constraints

- **Never** create `utils.py`, `helpers.py`, or additional modules in desktop workspaces.
- **Never** `view_file` or `edit_file` paths outside the two-file enum.
- Imports in `scenes.py` may reference `assets` only (plus `canvas`).

**Dev repo note:** `projects/<name>/helpers.py` remains valid for engine development and parity tests. Desktop product workspaces use `assets.py` as the second file name.

### 7.4 Workspace layout (agent mode)

```
~/Matemium/workspaces/<project-id>/
├── scenes.py          # Timeline (required)
├── assets.py          # Engine room (required in agent mode; may be minimal)
├── project.json       # metadata; authoring_mode: "two_file"
└── renders/           # app-managed output dirs
```

Templates: [`shared/templates/scenes.py`](shared/templates/scenes.py), [`shared/templates/assets.py`](shared/templates/assets.py).

---

## 8. Critical integration points

Three configurations are required for production reliability.

### 8.A LaTeX — TinyTeX (not full TeX Live)

Manim depends on LaTeX for `add_math`. Full MiKTeX/MacTeX installs are multi-gigabyte and unsuitable for bundling.

**Decision:** Bundle a **stripped TinyTeX micro-distribution** (~80–120 MB zipped) — not browser MathJax SVG substitutes. TinyTeX gives vector-precise math identical to standard Manim.

| Dimension | Rating | Reality |
|-----------|--------|---------|
| Setup complexity | Moderate (3/5) | PATH injection at sidecar startup |
| Asset size | Low impact | ~80–120 MB per platform |
| Runtime reliability | Maximum (5/5) | Native `latex` / `dvisvgm` pipeline |
| Offline autonomy | Complete (5/5) | Aligns with zero cloud rendering |

**Do not** package full LaTeX inside the sidecar. **Do not** rewrite Manim's math pipeline to MathJax for production.

#### TinyTeX install locations

Unpack on first run into the app data directory:

| OS | Path |
|----|------|
| Windows | `%APPDATA%\Matemium\bin\tinytex\` |
| macOS | `~/Library/Application Support/Matemium/bin/tinytex/` |
| Linux | `~/.local/share/Matemium/bin/tinytex/` (or XDG data dir) |

Reference: [TinyTeX](https://yihui.org/tinytex/).

#### PATH injection (sidecar startup)

Before any Manim compile, prepend TinyTeX binaries to `PATH`:

```python
import os
import sys

def inject_local_latex_env(app_data_bin_dir: str) -> None:
    if sys.platform == "win32":
        tex_bin = os.path.join(app_data_bin_dir, "tinytex", "bin", "windows")
    elif sys.platform == "darwin":
        tex_bin = os.path.join(app_data_bin_dir, "tinytex", "bin", "universal-darwin")
    else:
        tex_bin = os.path.join(app_data_bin_dir, "tinytex", "bin", "x86_64-linux")

    if os.path.exists(tex_bin):
        os.environ["PATH"] = tex_bin + os.pathsep + os.environ["PATH"]
```

#### Required LaTeX packages (pre-install in CI)

Run once when building the master TinyTeX bundle:

```bash
tlmgr install amsmath amssymb dsfont ragged2e setspace physics
```

#### Self-correction + LaTeX errors

When `compile_manim` fails on LaTeX, stderr contains the TeX compiler traceback. The agent loop feeds that exact output back to the LLM — enabling automatic correction of malformed matrix or equation strings without user intervention.

### 8.B Asynchronous IPC (non-blocking UI)

Manim renders take seconds to minutes. **Never** block the Tauri window on a synchronous render invoke.

**Pattern:**

1. Frontend: `invoke("start_render", { workspace, scene, quality })` — returns immediately with `job_id`.
2. Rust spawns sidecar `render_project`; dedicated thread reads stdout.
3. Sidecar streams NDJSON **events**; Rust forwards via `tauri::Emit`.
4. Frontend `listen("render_progress", ...)` updates progress UI.

Example event payload:

```json
{
  "event": "render_progress",
  "payload": {
    "job_id": "job-abc",
    "section": "part_intro",
    "frame": 120,
    "total_frames": 300,
    "pct": 0.4,
    "message": "rendering..."
  }
}
```

See [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md) for canonical event types.

### 8.C Cross-platform workspace pathing

PyInstaller unpacks to a temp directory at runtime. Hardcoded paths like `./canvas/scene.py` break in production.

**Rule:** Use runtime path detection in all sidecar workspace code:

```python
import os
import sys

def get_workspace_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))
```

User project workspaces are separate from the sidecar binary path — passed per-request as `workspace` in IPC. `MATEMIUM_ROOT` is set to the **project workspace**, not the executable directory.

**Cross-platform paths:** Windows uses backslashes (`C:\Users\...\Matemium`); macOS and Linux use forward slashes. Agent `edit_file` targets logical filenames only (`scenes.py`, `assets.py`). The Rust orchestrator joins paths with `PathBuf`; the sidecar uses `os.path.join` / `pathlib.Path`. Never hardcode directory separators in tools or prompts.

---

## 9. AI integration tiers (updated)

| Tier | Mode | Project shape | User experience |
|------|------|---------------|-----------------|
| **v1 — Chat API** | Completions + optional diff blocks | Single `scenes.py` | User reviews/applies patches |
| **v2 — Agent** | Tool loop + self-correction | **`scenes.py` + `assets.py` only** | Agent edits, compiles, fixes autonomously |
| **v3 — Local agent** (future) | Same tools, local model | Two-file | Offline-capable orchestration |

v1 remains supported for simple chat. **v2 is the target architecture** described in this document.

---

## 10. Cloud router responsibilities (agent mode)

| In scope | Out of scope |
|----------|--------------|
| Auth, billing, rate limits | File I/O, patch apply, render |
| Forwarding tool-call messages to LLM | Running Manim |
| Returning assistant messages + tool calls | Storing rendered video |

The desktop orchestrator runs the tool loop:

1. Send context bundle + user message to cloud.
2. Receive tool calls (`edit_file`, `compile_manim`, ...).
3. Execute locally; append tool results.
4. Repeat until compile succeeds or retry budget exhausted.
5. Show final assistant message + video preview.

---

## 11. System prompt

The agent system prompt lives at [`shared/prompts/agent-system.txt`](shared/prompts/agent-system.txt). It instructs the model to:

1. Review user request and file context.
2. Use `edit_file` with Search/Replace blocks — never rewrite whole files.
3. Call `compile_manim` to verify changes.
4. On compile failure, analyze traceback, fix via `edit_file`, re-compile.
5. Respond to the user only after a successful compile (or explicit retry exhaustion).

v1 chat authoring prompt (no tools): [`shared/prompts/scene-authoring-system.txt`](shared/prompts/scene-authoring-system.txt).

---

## 12. Implementation phases

| Phase | Deliverable | Depends on |
|-------|-------------|------------|
| **A1 — Patch engine** | Rust Search/Replace parser + Monaco sync | — |
| **A2 — Context bundler** | Selection, section map, last errors in chat payload | A1 |
| **A3 — Tool loop orchestrator** | Desktop executes tool calls; cloud round-trip | A1, A2 |
| **A4 — Async render bridge** | `start_render` + streamed events | Existing sidecar IPC |
| **A5 — Two-file workspace** | `assets.py` template + drawer UI | A1 |
| **A6 — TinyTeX bootstrap** | First-run install + PATH injection | Sidecar packaging |
| **A7 — Agent system prompt** | Deploy `agent-system.txt` to cloud router | A3 |

---

## 13. Related documents

| Document | Scope |
|----------|-------|
| [`desktop-architecture.md`](desktop-architecture.md) | Product goals, boundaries, workspace model |
| [`architecture.md`](architecture.md) | Engine design; §8 desktop summary |
| [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md) | Sidecar commands and events |
| [`server/README.md`](server/README.md) | Cloud chat + agent message routing |
| [`shared/schemas/chat-completion.schema.json`](shared/schemas/chat-completion.schema.json) | Chat API response shape |
| [`shared/schemas/project.schema.json`](shared/schemas/project.schema.json) | `project.json` including `authoring_mode` |