# Matemium Sidecar IPC Protocol

**Version:** 1.0
**Last updated:** 2026-07-27 (reflects current sidecar commands + engine actions)
**Transport:** newline-delimited JSON on stdin (requests) and stdout (responses + events)

The Tauri Rust shell spawns `matemium-sidecar` as a child process. All engine work flows through this protocol — the TypeScript UI never talks to Python directly.

**Product authoring path:** desktop saves `scenes.py`, `helpers.py`, and `brief/` to a project workspace; sidecar **imports and renders project code** via `lint_project`, `check_project`, `list_scenes`, `render_project`. **Legacy path:** inline `dsl` payloads remain for tests and engine debugging.

**Agent mode:** the LLM tool `compile_manim` maps to `check_project` + `render_project` on the sidecar. The desktop orchestrator runs the tool loop; see [`ai-agent-architecture.md`](../../ai-agent-architecture.md).

**MCP mode (Phase 9+):** Run with `--mcp` to expose tools/resources over stdio MCP (for local clients/agents). Tools: view_file, edit_file, compile_manim, retrieve. See `matemium/mcp_server.py`.

## Envelope types

### Request (desktop → sidecar)

```json
{"type":"request","id":"req-1","command":"ping","params":{}}
```

### Response (sidecar → desktop)

```json
{"type":"response","id":"req-1","ok":true,"result":{"version":"0.1.0"}}
```

```json
{"type":"response","id":"req-1","ok":false,"error":{"code":"INVALID_DSL","message":"..."}}
```

### Event (sidecar → desktop, streamed during long operations)

```json
{"type":"event","event":"render_progress","data":{"pct":0.42,"message":"..."}}
```

Events may arrive **between** the request write and the matching response line. The desktop client must read stdout continuously.

## Commands

### Project commands (desktop product)

| Command | Required params | Result |
|---------|-----------------|--------|
| `get_status` | — | Lightweight status: `{ phase, engine_loaded, core_ready, version, ... }`. Does **not** load heavy engines. |
| `configure_assets` | e.g. `{"tinytex_dir": "..."}` | `{ok, configured: [...]}`. Light (no engine). Allows Rust to tell sidecar asset locations early. |
| `update_llm_config` | `use_local_llm`, `model_path` | `{ok, configured: [...]}`. Light (no engine). Tells the sidecar whether to use a local GGUF LLM and maps its local path. |
| `retrieve` | `{"query": "...", "workspace"?, "top_k"?: 8, "files"?: [...]}` | `{query, results: [{file, chunk, score, type}], top_k}`. Uses vector RAG if INTELLIGENCE_READY, else keyword fallback. |
| `lint_project` | `workspace` | `{ ok, diagnostics[], workspace }` |
| `check_project` | `workspace`, (`scene`?) | `{ ok, errors[], warnings[], scene, timeline_length?, title? }` |
| `list_scenes` | `workspace` | `{ scenes[], workspace }` |
| `list_tapes` | `workspace`, (`scene`?) | `{ tapes[], default_tape_id, scene, workspace }` |
| `render_project` | `workspace`, (`scene`?, `quality`, `output_dir`) | `{ video, workspace, scene, duration_estimate }` |
| `export_project_tape` | `workspace`, `tape_id`, (`scene`?, `format`?, `high_res_height`?, `output_dir`?) | `{ path, format, tape_id, pixel_width, pixel_height, size_bytes }` |
| `get_preview_data` | `{ projectId }` (maps to workspace + optional scene) | `{ elements: PreviewElement[], frame_width, frame_height, title?, orientation? }` — drives the manim-web live preview with authoritative layout |

Optional: `path` — alternate scenes file relative to workspace (default `scenes.py`).

`check_project` imports a scene without runtime raising so it can return
structured `SheetDSL.validate()` diagnostics. Production construction and
rendering remain strict by default. Diagnostics include registered content
schemas, semantic-part targets, state patches, and morph targets.

`workspace` is the project root containing `scenes.py`, optional `helpers.py`, and `brief/`. Sidecar sets `MATEMIUM_ROOT` to this path while importing. In PyInstaller builds, `MATEMIUM_ROOT` is the **user project workspace**, not the frozen executable directory — see path detection in [`ai-agent-architecture.md`](../../ai-agent-architecture.md) §8.C.

**Events:** `lint_started`, `lint_complete`, `check_complete`, plus render events on `render_project`.

### Legacy / dev commands (inline DSL)

| Command | Required params | Result |
|---------|-----------------|--------|
| `ping` | — | `{ ok, version, protocol, engine }` |
| `validate_dsl` | `dsl` | `{ valid, errors[], warnings[], duration_estimate? }` |
| `estimate_duration` | `dsl` | `{ duration_estimate }` |
| `compile_preview` | `dsl` | `{ duration_estimate, sheet_png, workspace }` |
| `render` | `dsl` | `{ video, workspace, duration_estimate }` |
| `export_sheet` | `dsl` **or** `workspace` + (`scene`?) | `{ path, format, workspace }` |
| `cut_reels` | `video`, (`workspace`+`scene` or `dsl` or `manifest`) | `{ reels[], workspace, manifest }` |
| `shutdown` | — | `{ shutdown: true }` — exits loop |

### Common optional params

| Param | Applies to | Description |
|-------|------------|-------------|
| `output_dir` | render, export, preview, cut | Tauri-managed job directory |
| `job_id` | render, export, preview | Fallback id under `outputs/desktop/<id>/` |
| `quality` | render, preview, export | `fast_preview` \| `preview` \| `draft` \| `low` \| `medium` \| `high` \| `final` |
| `strict` | `validate_dsl` | Reject legacy dev-only timeline types (default `true`) |

Current inline DSL recognizes `DataPath`, `DataPlot`, and `Diagram` elements,
plus `StateTransition` and `ElementMorph` timeline actions. They round-trip
through normal DSL dictionaries/JSON. Product authors should still create them
through `CanvasBuilder` in `scenes.py`.

## Event types

| Event | When | Data |
|-------|------|------|
| `loading_phase` | Engine lazy load transitions (Phase 1+) | `{ phase: "ENGINE_LOADING" | "ENGINE_READY" | ..., message? }` |
| `compile_started` | DSL accepted | `element_count` |
| `layout_done` | Timeline parsed | `duration_estimate` |
| `render_started` | Manim render begins | `quality` |
| `render_progress` | Lifecycle updates | `pct`, `message`, optional `job_id`, `section`, `frame`, `total_frames` |
| `render_complete` | MP4 written | `video` |
| `lint_started`, `lint_complete`, `check_complete` | As used by project commands | See handlers |
| `error` | Failure | `code`, `message` |

**Async UI rule:** long renders must not block the Tauri window. Desktop triggers render via a non-blocking invoke; Rust reads stdout continuously and emits Tauri events from `render_progress` payloads. See [`ai-agent-architecture.md`](../../ai-agent-architecture.md) §8.B.

Example streamed progress (agent / preview matrix):

```json
{"type":"event","event":"render_progress","data":{"job_id":"job-abc","section":"part_intro","frame":120,"total_frames":300,"pct":0.4,"message":"rendering..."}}
```

## Example session

```
→ {"type":"request","id":"1","command":"ping","params":{}}
← {"type":"response","id":"1","ok":true,"result":{"ok":true,"version":"0.1.0","protocol":"1.0","engine":"matemium"}}

→ {"type":"request","id":"2","command":"validate_dsl","params":{"dsl":{...}}}
← {"type":"response","id":"2","ok":true,"result":{"valid":true,"errors":[],"warnings":[],"duration_estimate":12.5,"timeline_length":4}}

→ {"type":"request","id":"3","command":"render","params":{"dsl":{...},"quality":"preview","output_dir":"/tmp/matemium-job-abc"}}
← {"type":"event","event":"compile_started","data":{"element_count":4}}
← {"type":"event","event":"layout_done","data":{"duration_estimate":12.5}}
← {"type":"event","event":"render_started","data":{"quality":"preview"}}
← {"type":"event","event":"render_progress","data":{"pct":0.05,"message":"starting manim render"}}
← {"type":"event","event":"render_progress","data":{"pct":1.0,"message":"render complete"}}
← {"type":"event","event":"render_complete","data":{"video":"/tmp/.../CanvasScene.mp4"}}
← {"type":"response","id":"3","ok":true,"result":{"video":"...","workspace":"...","duration_estimate":12.5}}
```

## Sample DSL

See [`fixtures/minimal_sheet.dsl.json`](../../fixtures/minimal_sheet.dsl.json).

## Running locally

```bash
python -m matemium.sidecar
# or after pip install:
matemium-sidecar
```

Pipe requests:

```bash
echo '{"type":"request","id":"1","command":"ping","params":{}}' | python -m matemium.sidecar
```

## Tauri integration notes

- Register the PyInstaller binary as a Tauri `externalBin` named `matemium-sidecar`.
- Spawn with `current_dir` set to the job workspace.
- Set `MATEMIUM_WORKSPACE` if not passing `output_dir` per request.
- Read stdout in a dedicated thread; parse lines by `type` field.
- Write requests to stdin with trailing newline; flush after each line.
- Engine logs may use stderr — do not parse stderr as protocol traffic.
- **LaTeX:** inject local TinyTeX `bin` into `PATH` at sidecar startup before Manim renders (see [`ai-agent-architecture.md`](../../ai-agent-architecture.md) §8.A).

## Agent tool mapping

| LLM tool | Sidecar command(s) | Executor |
|----------|-------------------|----------|
| `view_file` | — (desktop reads workspace FS / editor buffer) | Rust |
| `edit_file` | — (desktop patch engine applies SEARCH/REPLACE) | Rust |
| `compile_manim` | `check_project` then `render_project` | Sidecar |

On `compile_manim` failure, return stderr/traceback as the tool result so the agent self-correction loop can retry `edit_file`.
