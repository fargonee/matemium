# Implementing the Product Architecture Decisions

**Date:** 2026-07-02  
**Status:** Implementation guide (authoritative steps)  
**Related (read first):**  
- `PRODUCT-ARCHITECTURE-DECISIONS.md` (single source of truth for decisions)  
- `desktop-architecture.md`  
- `ai-agent-architecture.md`  
- `STRUCTURE.md`  
- `matemium/ipc/PROTOCOL.md`  
- `desktop/packaging/README.md`

This document turns the high-level decisions from `PRODUCT-ARCHITECTURE-DECISIONS.md` into **concrete, ordered steps** that can be executed by engineers. It assumes the current baseline (working Tauri desktop + PyInstaller sidecar MVP from COMPLETE_LINUX_UBUNTU_APP_TODO.md and verify phases).

**Core shift targeted:**
- Eager full-engine sidecar → minimal control-plane sidecar + lazy registry.
- All heavy assets (TinyTeX, Jina embeddings, vector store) downloaded on first run.
- Strict capability gate: no creation/AI/render until `FULLY_READY`.
- Local-first vector intelligence (LanceDB + `jina-embeddings-v2-base-code` ONNX int8).
- Thin public gallery via YouTube metadata only.
- Rust owns downloads & readiness UI; Python owns lazy engines + logic.

---

## 0. Preparation & Baseline Audit

**Current state snapshot (as of writing):**
- Sidecar (`matemium/sidecar.py` + `ipc/server.py` + `ipc/handlers.py`) imports canvas/render/workspace_project at module load time → full Manim loaded eagerly on spawn.
- PyInstaller spec (`desktop/packaging/matemium-sidecar.spec`) eagerly collects `manim`, `canvas`, full submodules and data.
- Desktop UI (`desktop/app/src/App.tsx` and children) allows project creation, editor, chat, render, and preview immediately on launch.
- No download manager in Rust/TS.
- No `get_status` / loading phase events.
- TinyTeX is system-dependent (pending first-run bootstrap per `project-spec.md`).
- No LanceDB / Jina / embeddings code in tree.
- Gallery is absent or minimal; publishing not implemented.
- MCP not present.

**Actions:**
1. Create a fresh branch: `git checkout -b feat/pad-implementation`.
2. Run baseline verification:
   ```bash
   cd desktop
   cargo tauri dev   # quick smoke (from desktop/)
   # In another shell:
   ./desktop/scripts/verify-sidecar-binary.sh
   ./desktop/scripts/verify-phase6.sh || true
   ```
3. Audit current imports in sidecar path:
   ```bash
   grep -r "from canvas\|import manim\|from manim" matemium/ canvas/ --include="*.py" | head -30
   ```
4. Read current sidecar entry points and packaging:
   - `matemium/sidecar.py`
   - `matemium/ipc/{server,handlers,protocol,events}.py`
   - `desktop/packaging/matemium-sidecar.spec`
   - `desktop/src-tauri/src/sidecar.rs`, `commands.rs`, `lib.rs`
5. Inventory app data paths used today vs. target (see PAD §7).

**Deliverable:** A short `current-state-audit.md` (or just notes) capturing file sizes of current sidecar, import timing, and UI entry points that will be gated.

---

## 1. Minimal Control-Plane Sidecar + Lazy Loading (PAD §5 + §6)

**Decision recap:** Sidecar binary loads only IPC + bootstrap at startup. Heavy deps (Manim, embeddings, vector DB, full agent) imported **on first use**. Use Lazy Registry / Deferred Singleton pattern.

**Target loading phases (IPC events):**
- `CORE_READY`
- `ENGINE_LOADING` (Manim / canvas)
- `EMBEDDING_READY`
- `INTELLIGENCE_READY` (vector store + retriever)
- `FULLY_READY`

### Steps

1. **Introduce central lazy module**  
   Create `matemium/lazy.py` (or `matemium/_lazy_registry.py`):
   ```python
   from __future__ import annotations
   import threading
   from typing import Any

   _lock = threading.Lock()
   _manim_engine: Any = None
   _jina_embedder: Any = None
   _vector_store: Any = None
   # ... other singletons

   def get_manim_engine():
       global _manim_engine
       if _manim_engine is None:
           with _lock:
               if _manim_engine is None:
                   import manim  # heavy
                   from canvas import CanvasScene, ...  # etc.
                   _manim_engine = ...  # configured instance or module
       return _manim_engine

   def get_embedder():
       ...

   def get_vector_store():
       ...
   ```
   Export public getters: `get_canvas_builder`, `get_render_functions`, etc.

2. **Make sidecar entry + server minimal**  
   - `matemium/sidecar.py`: keep `ensure_on_path`, parser, `run_server`. **Do not** import handlers at top if possible (use lazy dispatch).
   - `matemium/ipc/server.py`: keep very thin.
   - `matemium/ipc/handlers.py`: 
     - Remove top-level `from canvas import ...`, `from ..render import ...`, etc.
     - Move all heavy imports inside the individual handler functions or inside a `dispatch` that calls lazy getters.
     - Update `dispatch` to call lazy versions for `lint_project`, `check_project`, `render_project`, etc.
   - Update `matemium/workspace_project.py`, `render.py`, etc. to expose lazy-friendly entry points or accept that they will only be reached after lazy trigger.

3. **Add status / load commands to protocol**  
   Extend `matemium/ipc/PROTOCOL.md` and implement:
   - `get_status` → `{ status: "CORE_READY" | "ENGINE_LOADING" | ..., phases: {...}, ready_for: [...] }`
   - Optional `trigger_load` (for explicit "start intelligence" action).
   Add new events: `status_update`, `loading_phase`.

4. **Update PyInstaller spec for control-plane**  
   In `desktop/packaging/matemium-sidecar.spec`:
   - Remove or conditionalize `collect_submodules("manim")`, full canvas collection for the frozen bundle.
   - Keep only core bootstrap, ipc, paths, protocol, lazy module.
   - Heavy packages become **optional runtime imports** (they will be present in the Python env at build time for discovery, but PyInstaller should use `--exclude-module` or hooks to avoid baking everything into the onefile).
   - Add notes / hooks for on-demand collection if needed later.
   - Result target: dramatically smaller sidecar binary footprint (control plane only).

5. **Update sidecar startup & PATH injection**  
   Move `ensure_on_path` + any TinyTeX PATH injection into a post-CORE bootstrap that is still cheap.
   Inject TinyTeX only when engine is first requested.

6. **Add progress emission for loading**  
   Sidecar should emit events over existing NDJSON when lazy loads begin/complete.

**Verification:**
- Run sidecar: `echo '{"type":"request","id":"1","command":"ping","params":{}}' | python -m matemium.sidecar` — should start instantly with **no** Manim import (use `python -X importtime ...` or profiler to confirm).
- `get_status` returns `CORE_READY` before any heavy action.
- Calling `render_project` triggers `ENGINE_LOADING` → success.
- Sidecar binary size decreases (measure before/after).

**Files touched:**
- `matemium/lazy.py` (new)
- `matemium/sidecar.py`, `ipc/server.py`, `ipc/handlers.py`
- `matemium/workspace_project.py`, `render.py` (refactor imports)
- `desktop/packaging/matemium-sidecar.spec`
- `matemium/ipc/PROTOCOL.md`

---

## 2. Asset & Model Download Lifecycle (PAD §7 + §8)

**Decision:** Rust/Tauri owns downloading, storing, verifying models & data packages. Python sidecar only consumes paths.

**Assets to manage (initial set):**
- TinyTeX micro-distribution (~80-120 MB zipped)
- `jina-embeddings-v2-base-code` ONNX int8 quantized model + runtime
- Future: vector DB data or index seeds, manifest updates

**Platforms paths (user-writable):**
- Linux: `~/.local/share/Matemium/...`
- macOS: `~/Library/Application Support/Matemium/...`
- Windows: `%LOCALAPPDATA%\Matemium\...`

### Steps

1. **Design asset manifest**  
   Create `shared/assets/manifest.json` (or served from server) with entries:
   ```json
   {
     "version": "2026-07-02",
     "assets": [
       {"id": "tinytex-linux", "url": "...", "sha256": "...", "size": 95000000, "extract": true},
       {"id": "jina-onnx-int8", "url": "...", "sha256": "...", ...}
     ]
   }
   ```
   App checks on launch / periodically. Decoupled from desktop version.

2. **Rust asset manager**  
   In `desktop/src-tauri/`:
   - New module `assets.rs` (or extend `workspace.rs` / new `downloads.rs`).
   - Commands: `get_asset_status`, `start_asset_download`, `pause_download`, `verify_assets`.
   - Use `tauri_plugin_http` or `reqwest` + progress events emitted to frontend (`tauri::emit`).
   - Download to temp, verify SHA256 + optional signature, atomic move to final AppData location.
   - Store local state (JSON or sqlite) of downloaded + verified versions.

3. **Expose paths to Python**  
   Add IPC command (or augment `ping`/`get_status`) that returns asset root paths:
   ```json
   {"tinytex_bin_dir": "...", "embeddings_model_dir": "...", "vector_db_dir": "..."}
   ```
   Sidecar uses these when lazy-loading.

4. **Integrate with existing sidecar launch**  
   - Rust spawns sidecar **only after** core assets are present (or allows spawn early but blocks gated operations).
   - Pass asset paths via env vars or first `get_status` result.

5. **Resume / error handling**  
   Support resumable downloads (HTTP range or library support). On checksum fail: Rust deletes + retries or surfaces clear error.

**Verification:**
- Fresh install triggers download of listed assets with progress %.
- AppData dir populated correctly per platform.
- Checksum mismatch triggers re-download flow.
- Sidecar can locate assets and use them (e.g. LaTeX works without system texlive after bootstrap).

**Files touched:**
- `shared/assets/` (new, or under `shared/schemas/`)
- `desktop/src-tauri/src/{assets.rs, commands.rs, lib.rs}`
- `desktop/app/src/api/tauri.ts` + new hooks/components for progress
- `matemium/paths.py` or new `matemium/assets.py` (consumption)
- Packaging scripts for initial TinyTeX bundle creation (see PAD §8.A)

---

## 3. First-Run Experience & Loading Screen (PAD §8)

**Decision:** ~50 MB installer. Sleek dark "obsidian" loading screen with neon cyan progress bar. "Local Code Intelligence Engine is securely downloading…". Background downloads while browsing public content.

### Steps

1. **Tauri splash / initial window**  
   Use Tauri `splashscreen` plugin or custom initial HTML/TSX screen shown before main app content.
   - Dark theme (obsidian black + neon cyan accents).
   - Progress bar driven by asset download + loading phase events.
   - Text + estimated time or current phase.

2. **Frontend readiness state**  
   In `desktop/app/src/`:
   - New store/hook: `useAppReadiness()` tracking `coreReady`, `engineReady`, `intelligenceReady`, `fullyReady`.
   - On app start: call `get_status` (or new `get_readiness`) repeatedly until `FULLY_READY`.
   - Show loading overlay / dedicated screen while not ready.
   - Allow "Explore public gallery & features" navigation while blocked.

3. **Installer size target**  
   - Keep sidecar minimal (see §1).
   - Assets **not** inside installer.
   - Audit current `.deb`/`.AppImage`/MSI size; document how to keep under ~50 MB for base.

**Verification:**
- Clean install → immediate beautiful loading screen.
- User can browse gallery content during download.
- Progress is accurate and resumable.
- Once `FULLY_READY`, full UI unlocks without restart.

---

## 4. Strict User Experience Gating (PAD §9)

**Hard rule:** No creation, editing, AI chat, or rendering until `FULLY_READY`.

**Allowed pre-ready:**
- Browse public/community animations (YouTube embeds)
- Feature banners, marketing, discovery content

### Steps

1. **Rust/TS state machine**  
   - Rust holds authoritative `ReadinessState`.
   - Expose via `invoke("get_readiness")` and events.
   - On `get_status` or readiness change, push to frontend.

2. **UI enforcement** (multiple surfaces):
   - `ProjectsLanding.tsx` / create button: disabled or hidden + tooltip "Waiting for Local Intelligence Engine...".
   - `ChatPanel.tsx`: disabled / read-only view until ready.
   - Editor panes: view-only or blocked.
   - Render button / shortcuts: blocked.
   - Sidebar navigation between "public" tabs vs. "workspace" tabs.
   - Global banner or toast: "Downloading dependencies (X%) – you can explore the gallery meanwhile."

3. **Backend command guards**  
   In Rust commands (`commands.rs`): before executing `create_project`, `save_scenes`, `sidecar_*` render/chat, check readiness. Return specific error code `APP_NOT_READY` if blocked. Frontend shows friendly message.

4. **Gallery must work early**  
   - Public gallery data fetched from server (metadata only + YouTube IDs) — **no sidecar dependency**.
   - YouTube embeds / players must function in the loading screen or a "Community" tab.

**Verification:**
- On a machine with no assets: app launches, shows gallery + banners, blocks all workspace actions.
- After downloads complete + engines load: full functionality appears (or button enables).
- Attempting blocked actions in UI or via direct invoke is rejected cleanly.

**Files touched:**
- `desktop/app/src/App.tsx`, all main components, new `ReadinessGate.tsx`
- `desktop/src-tauri/src/{commands.rs, state.rs, lib.rs}`
- `desktop/app/src/api/types.ts` + tauri.ts

---

## 5. Local Vector Database, Embeddings & RAG (PAD §2 + §3)

**Decision:** Full vector DB (LanceDB recommended) lives inside the Python sidecar on user's machine. Embeddings: `jina-embeddings-v2-base-code` ONNX int8 (downloaded, not bundled). Fallback keyword retriever always available.

### Steps

1. **Add dependencies (sidecar build time)**  
   - Add `lancedb`, `pyarrow`, `onnxruntime` (or ONNX-specific) to relevant requirements / `pyproject.toml`.
   - Do **not** force them into the frozen minimal sidecar binary unless lazy-loaded.

2. **Implement retriever module**  
   Create `matemium/agent/rag.py` (or `matemium/intelligence/retriever.py`):
   - `class VectorRetriever`
   - Lazy init using paths from Rust.
   - Index per-workspace or global: `scenes.py`, `assets.py`, past patches, error/fix pairs, math patterns.
   - Methods: `retrieve(query: str, top_k=8) -> list[chunks]`
   - Fallback: simple keyword + section-based (parse `# ---DIV:` + function names) when vector engine disabled or not ready.

3. **Integrate into agent loop**  
   - Update `matemium/agent/` (coordinator, writer, etc.) to accept optional `retriever`.
   - In context bundling (desktop side) or agent prompt construction: prefer retrieved chunks over full file when `INTELLIGENCE_READY`.
   - Self-correction only uses full RAG after `EMBEDDING_READY`.

4. **Build / update indexes**  
   - Trigger index build on first `INTELLIGENCE_READY` or project save.
   - Provide maintenance commands (`rebuild_index`, `status`).

5. **Security / size**  
   - Store indexes under user AppData (never in git).
   - Quantized model only.

**Verification:**
- After intelligence ready, `view_file` context can be augmented with retrieved relevant code chunks.
- Token usage for AI calls drops for large scenes (measure).
- Fallback retriever works even if LanceDB or model missing.

**Files touched:**
- New `matemium/intelligence/` (or under `agent/`)
- Agent files, context bundler (desktop + shared prompts)
- `shared/prompts/`
- Requirements / packaging hooks

---

## 6. TinyTeX First-Run Bootstrap (completes PAD §8.A + pending item)

**Status today:** System TeX Live assumed. Decision: ship stripped TinyTeX.

### Steps

1. **Bundle creation** (offline or CI step)
   - Script to download + prune TinyTeX for each platform.
   - Install required packages once: `tlmgr install amsmath amssymb ... physics`
   - Zip the resulting portable tree.

2. **Download + unpack in Rust asset manager** (see §2)
   - Treat TinyTeX like the embeddings model.

3. **PATH injection in sidecar (lazy)**
   - Implement `inject_local_latex_env` (code already sketched in `ai-agent-architecture.md` §8.A).
   - Call it inside `get_manim_engine()` or the first time `ENGINE_LOADING` occurs.
   - Update `matemium/paths.py` or new `matemium/latex.py`.

4. **Update docs & packaging notes**
   - Remove or qualify "user must have texlive" in READMEs.
   - Add to verify scripts.

**Verification:**
- Fresh Linux container / VM with no TeX → install app → render succeeds using bundled TinyTeX.
- LaTeX errors still surface correctly for agent self-correction.

---

## 7. MCP Support (Local + Hosted) (PAD §4 + §11)

**Decision:** Support both. Local MCP inside Python sidecar is source of truth for user workspace. Expose `view_file`, `edit_file`, `compile_manim` + vector resources.

### Steps (can be later phase)

1. Implement a lightweight MCP server inside sidecar (or separate process on localhost) using the existing tool surface.
2. Define MCP tools/resources matching the agent tool schemas in `ai-agent-architecture.md`.
3. Wire desktop (or future local agent) as MCP client when intelligence is ready.
4. For hosted: keep current cloud routing; document how hosted MCP can reference local capabilities safely.

**Verification:** Tools discoverable and callable via MCP inspector or internal client.

---

## 8. Thin Publishing & Public Gallery (PAD §10)

**Decision:** No video storage on servers. Publish metadata + final upload to official Matemium YouTube channel. Gallery powered by YouTube embeds + server metadata API. Must work before local engines ready.

### Steps

1. **Server changes** (in `server/matemium_server/`)
   - New models/endpoints: `POST /publish`, `GET /gallery`, `GET /gallery/{id}`.
   - Store only: `youtube_id`, title, desc, tags, author, timestamps, featured, etc.
   - No MP4 blobs.

2. **Desktop "Publish" flow**
   - After successful local render in `FULLY_READY` state: "Publish to Community" button.
   - Form for metadata.
   - Submit → server record (pending youtube_id).
   - (Later) YouTube upload (manual or Data API + moderation).
   - Poll or webhook to fill `youtube_id`.

3. **Gallery UI**
   - Dedicated tab or landing section.
   - Fetch from server.
   - Render using YouTube player embeds (works pre-ready).
   - Search, filters, featured.

4. **Offline / caching**
   - Cache last gallery metadata locally.

**Verification:**
- A rendered reel can be "published".
- Gallery visible and playable immediately on first launch (before any downloads).
- No large media uploaded to Matemium infra.

---

## 9. Agent Loop & Context Updates (PAD §11 + ai-agent-architecture)

- Inject retrieval when available.
- Add readiness checks before using intelligence features.
- Extend context bundler to include `intelligence_status`.
- Update system prompt (`shared/prompts/agent-system.txt`) to prefer retrieved context.

**Files:** agent coordinator/writer, desktop context bundling logic, prompts.

---

## 10. IPC Protocol Extensions + Rust ↔ Python

Add to `matemium/ipc/PROTOCOL.md`:
- `get_status`
- New events: `loading_phase`, `asset_progress`, `intelligence_status`
- Possibly `get_asset_paths`

Rust sidecar manager may need light updates to surface new events cleanly.

Desktop should listen for these and drive readiness + progress UI.

---

## 11. Packaging, Build & Distribution Updates (PAD §13)

1. Update all `build-*.sh`, `verify-*.sh`, PyInstaller hooks.
2. New verify script: `verify-pad-readiness.sh` or extend phases.
3. Document asset manifest update process separate from app releases.
4. Consider feature flags (lite vs intelligence) later.
5. CI: ensure asset download tests or smoke in packaged binary.
6. Update `.github/workflows/*` if new deps or packaging steps.
7. Installer size guardrails in build scripts.

---

## 12. Phased Roadmap (Recommended Order)

**PAD-0: Audit & Scaffolding** (this doc + audit)
**PAD-1: Lazy Sidecar Control Plane** (core, handlers, lazy.py, PROTOCOL, minimal PyInstaller)
**PAD-2: TinyTeX Bootstrap** (asset paths + injection)
**PAD-3: Rust Download Manager + First Assets** (TinyTeX + manifest)
**PAD-4: Loading Phases + Status IPC + Basic Gating**
**PAD-5: Obsidian Loading Screen + Public Gallery Skeleton**
**PAD-6: Embeddings + LanceDB + Fallback Retriever + RAG integration**
**PAD-7: Full Strict Gating + Polish**
**PAD-8: Publishing + YouTube flow + Gallery**
**PAD-9: MCP surfaces + Agent enhancements**
**PAD-10: Packaging / CI / cross-platform + docs refresh + release**

Run targeted verify scripts after each major PAD phase. Consider adding automated integration tests that boot a "clean" sidecar and assert no heavy imports until triggered.

---

## 13. Cross-Cutting Work & Risks

- **Memory/CPU:** Running Manim + embeddings in same process (PAD §14). Profile early.
- **Error UX:** Clear messages when downloads fail or integrity broken.
- **Offline:** Gallery caching, graceful degradation when no net.
- **Update story:** How do we push new embeddings model without full desktop update? (manifest + Rust downloader)
- **Tests:** Add unit tests for lazy getters, retriever fallback, patch application under readiness.
- **Docs:** After implementation, update `desktop-architecture.md`, `ai-agent-architecture.md`, `README.md`, `project-spec.md`, `STRUCTURE.md` with "Implemented (see `PRODUCT-ARCHITECTURE-IMPLEMENTATION.md`)" notes.
- **Security:** Signature verification on assets, safe PATH injection, sandboxing of sidecar where possible.

---

## 14. Final Definition of Done (for the PAD spec)

- Installer remains ~50 MB range (assets separate).
- Fresh launch on clean machine shows loading + gallery only.
- After downloads + lazy loads → `FULLY_READY` and all creation features available.
- Sidecar spawns fast; heavy engines load on demand only.
- Vector retrieval demonstrably used by agent (or retriever API).
- TinyTeX works from downloaded bundle.
- Publish flow produces YouTube-playable entry via metadata only.
- All new behavior covered by updated tests and verify scripts.

---

Treat `PRODUCT-ARCHITECTURE-DECISIONS.md` as the "why" and this file as the "how, step-by-step".

Last updated: 2026-07-02 (initial implementation plan).

**Next action after reading:** Pick PAD-1 and begin with lazy sidecar work. Update this file with progress as milestones are reached.
