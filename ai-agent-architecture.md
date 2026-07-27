# Matemium AI Agent Architecture

**Status:** Product-boundary reference updated for the target autonomous runtime (2026-07-18). The current XML/regex ReAct loop is a legacy prototype, not the completed architecture.

**Audience:** Desktop shell, cloud router, sidecar, and AI integration authors.

**PAD Phase 10:** Packaging/CI/docs complete; MCP (phase 9) and RAG (phase 6) integrated into agent tools. See [`PRODUCT-ARCHITECTURE-IMPLEMENTATION.md`](PRODUCT-ARCHITECTURE-IMPLEMENTATION.md).

This document records product placement and trust boundaries: local tool execution, Search/Replace patches, the bounded project workspace, sidecar validation, and context sources. The normative runtime behavior—state, planning, recovery, completion gates, accounting, and evaluation—is defined in [`agentic_ai_goal.md`](agentic_ai_goal.md).

The production agent is a persistent state machine. A model response without tool calls is a finish proposal, not evidence of completion. Prompt instructions do not replace orchestrator-enforced policy.

The agent also follows the project-management contract in [`project-manager-architecture.md`](project-manager-architecture.md): it owns Passport discovery, structured preference questions, proactive production planning, and the Roadmap that is read-only to users.

The normative production sequence and its mute, TTS, and custom-audio branches are defined in [`product-production-lifecycle.md`](product-production-lifecycle.md). The bounded tool policy includes the lifecycle's separate tape-content, orchestration, narration/audio, transcript, and timestamp artifacts.

**Product decisions** (vector DB/RAG, lazy loading, first-run downloads, Jina embeddings, strict UX gating, thin YouTube publishing, local+hosted MCP, minimal control-plane sidecar) are documented in [`PRODUCT-ARCHITECTURE-DECISIONS.md`](PRODUCT-ARCHITECTURE-DECISIONS.md).

**Related:** [`desktop-architecture.md`](desktop-architecture.md) (product boundaries), [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md) (sidecar wire format), [`shared/prompts/agent-system.txt`](shared/prompts/agent-system.txt) (agent system prompt), [`PRODUCT-ARCHITECTURE-DECISIONS.md`](PRODUCT-ARCHITECTURE-DECISIONS.md) (latest product architecture).

---

## 1. Strategic shift

| Before (v1 chat canvas) | After (agent mode) |
|---------------------------|-------------------|
| LLM returns prose + optional diff blocks | LLM **calls tools** to inspect, edit, and compile |
| User applies diffs manually | Backend applies **Search/Replace patches** to editor state |
| User triggers render | Agent calls **`compile_manim`** and reads stderr |
| Single-turn chat | **Stateful plan/execute/verify loop** with honest terminal outcomes |
| One `scenes.py` buffer | Bounded **project workspace**: `scenes.py` + `helpers.py` + `brief/` |

The cloud remains a **thin optional LLM helper/router** for user-owned provider keys and profile sync. The desktop owns file state, patch application, sidecar lifecycle, and render feedback. **No cloud rendering, no Matemium-owned model quota.**

---

## 2. Agent tool surface (function calling)

The LLM receives structured tools—not raw shell access. Cloud models use provider-native function calling. Local models use a grammar/schema-constrained adapter normalized to the same internal request type. Regex-extracted XML is not a production wire contract. A framework may implement orchestration, but Matemium's state and tool contracts remain framework-independent.

Every result uses the typed envelope specified in [`agentic_ai_goal.md`](agentic_ai_goal.md): status, stable code, summary, structured data, evidence, retry hint, and truncation state. Executors must not flatten failures into ordinary strings.

### 2.1 Core tools

| Tool | Purpose | Backend mapping |
|------|---------|-----------------|
| `view_file(filename)` | Return current project file so the agent has context | Read workspace buffer (`scenes.py`, `helpers.py`, or approved `brief/*`) |
| `edit_file(filename, instructions, patches)` | Apply localized edits | Parse Search/Replace blocks → update editor buffer |
| `compile_manim(filename, scene_name, quality)` | Verify animation compiles | Sidecar `check_project` + `render_project` (or preview quality) |

**Allowed `filename` values (strict):** `scenes.py`, `helpers.py`, `brief/passport.json`, `brief/description.md`, safe `brief/tapes/<slug>.md` files, `brief/orchestration.md`, `brief/roadmap.json`, `brief/tts-narration.md`, `brief/tts-narration-style.md`, `brief/audio-description.md`, `brief/custom-narration.md`, `brief/transcript.md`, and `brief/timestamps.json`. Media generation, transcription, and assembly use dedicated tools rather than arbitrary file writes.

### 2.2 Tool schemas (reference)

```json
{
  "name": "view_file",
  "parameters": {
    "type": "object",
    "properties": {
      "filename": {
        "type": "string",
        "description": "An approved static project file or safe brief/tapes/<slug>.md path"
      }
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
      "filename": {
        "type": "string",
        "description": "An approved static project file or safe brief/tapes/<slug>.md path"
      },
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

`compile_manim` always targets `scenes.py` — the entry file the sidecar imports. `helpers.py` is imported by `scenes.py` when reusable computations, LaTeX helpers, geometry builders, or media-reference helpers are needed.

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
| `helpers.py` | Secondary code buffer | Full file text (empty/minimal template if new project) |
| `brief/*` | Project brief bundle | Passport, description, tape plan, roadmap, narration |
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

## 5. Stateful execution and recovery

Manim/Matemium code fails often (syntax, stale APIs, LaTeX errors). Recovery occurs inside a checkpointed run with an explicit plan, classified errors, independent budgets, stall detection, and completion gates.

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
      └──► (classify → revise plan → bounded recovery → verify)
```

### 5.1 Loop policy

| Parameter | Default | Notes |
|-----------|---------|-------|
| `max_compile_retries` | 5 | Per user turn |
| `retry_quality` | `preview` | Fast feedback; upgrade to `medium` on success if user requested final |
| `stop_condition` | Applicable completion gates pass | Compile alone does not prove semantic or visual correctness |

Retries are keyed by failure signature, not only by a global counter. Repeating an equivalent action with an unchanged observation counts as a stall. The runtime terminates as `blocked`, `failed`, or `cancelled` when appropriate; it must not turn exhaustion into success.

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

## 6. Agent lifecycle (persistent run)

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

## 7. Bounded project workspace (`scenes.py` + `helpers.py` + `brief/`)

Agent mode enforces a **bounded project workspace**. It is richer than the old two-file model, but still intentionally constrained: one render entrypoint, one Python support file, structured brief files, media folders, and app-managed renders. The agent must not turn a user project into an open-ended repository.

### 7.1 File roles

The target file roles and path-specific artifacts are defined by [`product-production-lifecycle.md`](product-production-lifecycle.md).

| File | Role | UI surface |
|------|------|------------|
| **`scenes.py`** | **The Timeline** — `# ---DIV: ---` section markers, `part_*` functions, `CanvasScene` class, readable `CanvasBuilder` layout | Main **Visual Script Workspace** (section cards) |
| **`helpers.py`** | **The Helper Room** — raw computations, coordinate arrays, custom LaTeX groupings, reusable geometry/data helpers | Secondary code drawer |
| **`brief/passport.json`** | Structured creative/production identity: topic, audience, difficulty, style, duration, language, constraints, learning goals | Form editor with JSON fallback |
| **`brief/description.md`** | Human-readable project brief and intent | Markdown editor |
| **`brief/tapes/*.md`** | Exact visible subject/reasoning content for one or more tapes | Markdown editor with tape and beat navigation |
| **`brief/orchestration.md`** | 3D world, camera, tape choreography, reveals, transformations, transitions, and pacing intent | Markdown editor with beat references |
| **`brief/roadmap.json`** | Phases, completion, current working point, blockers | AI-owned file shown as a read-only route in desktop; keep JSON valid and update progress only from supported project evidence |
| **Path-specific narration/audio files** | TTS narration/style or custom-audio description/narration, plus verified transcript/timestamps where required | Phase-aware Markdown, script, and timeline editors |
| **`media/images`, `media/video`, `media/audio`** | User-provided media referenced by project code or brief | Media browser with previews |

```python
# scenes.py — visual narrative only
from helpers import parabola_samples, matrix_tex

def part_graph(b: CanvasBuilder) -> None:
    xs, ys = parabola_samples(a=1, b=-2, c=1)
    b.add_math(matrix_tex)
    ...
```

```python
# helpers.py — computations and data (no CanvasScene)
def parabola_samples(a: float, b: float, c: float, *, n: int = 50):
    ...

def matrix_tex() -> str:
    return r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}"
```

### 7.2 Why bounded files (not unlimited)

| Benefit | Explanation |
|---------|-------------|
| **Separation of concerns** | Visual timeline, reusable Python, and creative/production intent have different homes |
| **UI sync** | Predictable navigation: Script, Helpers, Brief, Media, Renders |
| **Agent reliability** | Approved targets reduce import loops and duplicate utility files |
| **Token economics** | Context payload stays bounded and purpose-specific for cloud routing |
| **Persistent intent** | Brief files preserve the user's creative decisions beyond the latest code buffer |

### 7.3 Agent constraints

- **Never** create `utils.py`, extra Python modules, arbitrary nested source folders, or hidden scratch files in desktop workspaces.
- **Never** `view_file` or `edit_file` paths outside the approved enum.
- Imports in `scenes.py` may reference `helpers` only (plus `canvas` and standard/library dependencies already available to the engine).
- `brief/*.json` edits must keep valid JSON. The UI should provide structured form/checklist editing first and raw JSON fallback second.
- `brief/*.md` edits should preserve human-readable structure; do not replace project memory with opaque generated blobs.
- Media files are managed through dedicated UI/tooling. Code and brief files reference media by stable relative paths under `media/`.

**Migration note:** Historical desktop workspaces and docs used `assets.py` for helper code. New workspaces use `helpers.py`; `assets` is reserved for real media/project assets and app-level downloadable runtime assets.

### 7.4 Workspace layout (agent mode)

```
~/Matemium/workspaces/<project-id>/
├── project.json
├── scenes.py
├── helpers.py
├── brief/
│   ├── passport.json
│   ├── description.md
│   ├── tapes/*.md
│   ├── orchestration.md
│   ├── roadmap.json
│   └── path-specific narration/audio/transcript/timestamp files
├── media/
│   ├── images/
│   ├── video/
│   └── audio/
└── renders/
```

Templates live under [`shared/templates/`](shared/templates/); legacy `brief/tape.md` and `brief/narration.md` are migrated without deleting the source documents.

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

**Cross-platform paths:** Windows uses backslashes (`C:\Users\...\Matemium`); macOS and Linux use forward slashes. Agent `edit_file` targets approved logical filenames only (`scenes.py`, `helpers.py`, and `brief/*`). The Rust orchestrator joins paths with `PathBuf`; the sidecar uses `os.path.join` / `pathlib.Path`. Never hardcode directory separators in tools or prompts.

---

## 9. AI integration tiers (updated)

| Tier | Mode | Project shape | User experience |
|------|------|---------------|-----------------|
| **v1 — Chat API** | Completions + optional diff blocks | Single `scenes.py` | User reviews/applies patches |
| **v2 — Agent (Cloud)** | Tool loop + self-correction | **`scenes.py` + `helpers.py` + `brief/`** | Agent edits code/brief, compiles, fixes autonomously via cloud router |
| **v3 — Local Agent** | Same tools, local model | Bounded project workspace | Offline-capable local orchestration using GGUF models (3B / 7B) |

v1 remains supported for simple chat. **v2 (external provider via BYO/OpenRouter)** is preferred by default, while **v3 (Local)** remains available for offline/user-controlled workflows. See `PRODUCT-ARCHITECTURE-DECISIONS.md` Sections 4A and 15 for the OpenRouter OAuth flow, user-owned provider policy, local GGUF model specifications, lazy download sizes, and runtime sidecar handshake.

---

## 10. Cloud router responsibilities (agent mode)

| In scope | Out of scope |
|----------|--------------|
| Optional auth, provider preferences, endpoint abuse protection | File I/O, patch apply, render |
| Forwarding tool-call messages to user-selected LLM provider | Running Manim |
| Returning assistant messages + tool calls | Storing rendered video |

The desktop orchestrator runs the tool loop:

1. Send context bundle + user message to cloud.
2. Receive tool calls (`edit_file`, `compile_manim`, ...).
3. Execute locally; append tool results.
4. Classify failures, revise the plan, and recover within the run budgets.
5. Apply the relevant completion gates, including render and visual evidence when required.
6. Show the final assistant message and verification manifest only after the verifier authorizes completion.

---

## 11. System prompt

The agent system prompt lives at [`shared/prompts/agent-system.txt`](shared/prompts/agent-system.txt). It instructs the model to:

1. Review user request and file context.
2. Use `edit_file` with Search/Replace blocks — never rewrite whole files.
3. Call the relevant validation tools after changes.
4. On failure, classify the diagnostic, revise the plan, and recover within policy budgets.
5. Submit a finish proposal; the orchestrator—not the prompt—enforces completion gates.

The current prompt is a legacy authoring prompt and must be replaced by role-specific prompts using the structured model protocol. It must not request or stream private chain-of-thought.

v1 chat authoring prompt (no tools): [`shared/prompts/scene-authoring-system.txt`](shared/prompts/scene-authoring-system.txt).

---

## 12. Implementation phases

The authoritative, gated migration plan is [`TODO-react-agentic-ai-transition.md`](TODO-react-agentic-ai-transition.md). Its major stages are:

| Phase | Deliverable |
|-------|-------------|
| **0** | Baseline, benchmark tasks, and measurable acceptance thresholds |
| **1–2** | Durable run state machine and structured cloud/local model gateway |
| **3–4** | Typed safe tools, mutation journal, planner, policy, and recovery engine |
| **5–6** | Verification controller, completion manifest, compact context, and memory |
| **7** | Per-call accounting, versioned streaming, cancellation, resume, and approvals |
| **8** | Optional scoped delegation, enabled only when benchmarks justify it |
| **9** | End-to-end evaluation, shadow deployment, gated rollout, and rollback |

Earlier patch, context, render, workspace, and TinyTeX work remains enabling infrastructure; it does not by itself constitute a production autonomous agent.

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
