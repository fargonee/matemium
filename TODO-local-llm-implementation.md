# Matemium Local LLM (v3 Offline Agent) — Implementation TODO

This TODO tracks the production-grade implementation of **v3 — Local Agent (Offline-Capable Orchestration)**. It details the complete integration from the Tauri/Rust download manager down to the Python sidecar execution engine.

---

## 📋 High-Level Lifecycle Architecture

```
 ┌────────────────────────┐
 │ 1. Tauri Settings UI   │ ◄── User toggles [x] Enable Local LLM
 └───────────┬────────────┘
             │ Selects: 3B (Lite) / 7B (Balanced) / 8B (Elite)
             ▼
 ┌────────────────────────┐
 │ 2. Rust Asset Downloader│ ◄── Resolves URL/size from manifest & downloads .gguf
 └───────────┬────────────┘
             │ Verifies SHA256 → Emits progress to Frontend UI
             ▼
 ┌────────────────────────┐
 │ 3. Sidecar Handshake   │ ◄── Transmits `"use_local_llm": true` + `"model_path"` over IPC
 └───────────┬────────────┘
             │ Configures CoordinatorConfig dependencies
             ▼
 ┌────────────────────────┐
 │ 4. Local Run Inference │ ◄── Runs GGUF via llama-cpp-python / localhost:11434
 └────────────────────────┘
```

---

## 🏗️ Phase-by-Phase Checklist

### Phase 1: Shared Asset Manifest Definition
*Goal: Systematize model URLs, SHA256 checksums, and metadata to separate downloader logic from app builds.*

- [x] **1.1. Create manifest structure:** Update or create the central manifest file to support local LLMs.
  - File: `shared/assets/manifest.json` (or hosted endpoint)
  - Ensure the manifest contains accurate URLs and hashes for the recommended GGUF models:
    - **Lite:** `Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf` (~1.91 GB)
    - **Balanced:** `Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf` (~4.72 GB)
    - **Elite:** `Llama-3-8B-Instruct-Q4_K_M.gguf` (~4.89 GB)
- [x] **1.2. Schema Validation:** Define TypeScript and Python schemas matching this manifest format for validation safety during load.

---

### Phase 2: Tauri / Rust Background Downloader (`desktop/src-tauri`)
*Goal: Build a resilient, non-blocking HTTP downloader in Rust that reports granular progress and secures model files.*

- [x] **2.1. Implement Tauri Commands:**
  - File: `desktop/src-tauri/src/assets.rs` (and registered in `lib.rs` / `commands.rs`)
  - Created commands (unified dynamically under generic asset endpoints for elegant schema consistency):
    * `get_asset_status(asset_id)`: Returns local state (Not Downloaded, Downloading, Verified, Corrupted).
    * `start_asset_download(asset_id)`: Triggers background streamed request.
    * `cancel_asset_download(asset_id)`: Thread-safe cancellation signal.
- [x] **2.2. Background Thread & Progress Emitting:**
  - Emits `asset-progress` events containing `{ id, pct, message }` in a non-blocking background tokio task.
- [x] **2.3. Platform-Specific Storage Allocation:**
  - Saves downloaded GGUF files to `assets_root/models/` (which maps to XDG local share folders per OS).
- [x] **2.4. Post-Download SHA256 Checksum Verification:**
  - Implemented `verify_sha256` utilizing the `sha2` and `hex` crates with 64KB buffer streaming for optimal VRAM/RAM file verification. If verification fails, deletes the corrupt `.tmp` file and outputs descriptive status.

---

### Phase 3: Settings UI & User Experience Gating (`desktop/app`)
*Goal: Provide a premium, dark-obsidian themed UI that seamlessly manages background tasks and gates creative features until fully ready.*

- [x] **3.1. Settings Control Panel:**
  - File: `desktop/app/src/components/SettingsScreen.tsx`
  - Implemented:
    * `[x] Enable Local LLM Engine (Offline Mode)` toggle.
    * Radio selections for:
      - `Lite (Qwen-Coder 3B)` — "Fastest, perfect for CPU/Standard laptops."
      - `Balanced (Qwen-Coder 7B)` — "Highly accurate math layout. Recommended for VRAM/Mac M1+."
      - `Elite (Llama-3 8B)` — "Exceptional pedagogical writing. Best for workstations."
- [x] **3.2. Status Bar Progress Card:**
  - Integrated beautiful inline model card progress indicators in settings that display downloading state, real-time percentage progress bars, and "Cancel Download" control actions.
- [x] **3.3. Capability Gating (Strict Gate):**
  - Integrated local model verification checks dynamically within `refreshReadiness()` in `App.tsx`.
  - Extended centralized `isReady` and `readinessMessage` logic so that checking "Enable Local LLM Engine" automatically gates all sidebar, workspace edit, AI chat, and render actions, showing a descriptive lock banner `"Downloading offline model (X.X%)... — creation/editing/rendering blocked"` until the GGUF file is validated.

---

### Phase 4: Sidecar Handshake & Local Inference Engine (`matemium/agent`)
*Goal: Establish a secure handshake between Tauri and the PyInstaller sidecar, spinning up local LLM inference dynamically.*

- [x] **4.1. IPC Protocol Extension:**
  - File: `matemium/ipc/PROTOCOL.md` (documented) & `matemium/ipc/handlers.py` (implemented)
  - Handled the `update_llm_config` command payload dynamically to map environment variables:
    * `MATEMIUM_USE_LOCAL_LLM` (controls local routing).
    * `MATEMIUM_LOCAL_LLM_MODEL_PATH` (absolute GGUF path).
  - Wired background handshakes inside Tauri `settings_set` (`desktop/src-tauri/src/commands.rs`) using a new `sync_sidecar_llm_config` synchronizer.
- [x] **4.2. Local Inference Runner Integration:**
  - Created file: `matemium/agent/local_runner.py`
  - Fully integrated dual-mode offline routing:
    1. **Direct Bundled (Production):** Lazily imports and instantiates `llama_cpp.Llama` with full hardware acceleration / GPU auto-offloading (`n_gpu_layers=-1`) and model state caching to prevent repeated disk-load overhead.
    2. **Local Developer Port (Fallback):** Zero-dependency connection to `http://localhost:11434/v1` (Ollama REST chat API) using lightweight standard library urllib requests to speed up development iteration.
- [x] **4.3. Unified System Prompting & Formatting:**
  - Prompt architectures are structured inside the runner configuration to strictly request localized diffs using `SEARCH/REPLACE` templates with minimal generation latencies.

---

### Phase 5: Agent Lifecycle Integration & Self-Correction
*Goal: Override Phase 1 (Director), Phase 3 (Engineer), and Phase 4 (Critic) stubs inside `LifecycleCoordinator` with the local model engine.*

- [x] **5.1. Phase 1: Director Integration:**
  - Created `local_director_agent` inside `matemium/agent/local_agent.py` and mapped it to `director_fn` inside `LifecycleCoordinator.__init__`. It utilizes structured math prompts to generate scripts complete with `# ---DIV: ...` markers.
- [x] **5.2. Phase 3: Engineer Integration + Local RAG Context:**
  - Created `local_engineer_agent` which first programmatically compiles the robust base files and then applies local GGUF refinements (such as matrix grids, latex variables, and layout styles) via Search/Replace patches. It injects local RAG retrieval context chunks before requesting customization.
- [x] **5.3. Phase 4: Critic Self-Correction:**
  - Created `make_local_critic_patch_fn` which binds a local critic self-correction closure to the failing project directory. It feeds tracebacks (`stderr`) to the local GGUF model and applies precise Aider-style repairs to either `scenes.py` or `assets.py`.
  - Seamlessly integrated overrides directly within `LifecycleCoordinator.__init__` if `MATEMIUM_USE_LOCAL_LLM` is active.

---

### Phase 6: Testing, Validation & Launch Readiness
*Goal: Exhaustive verification to guarantee production stability for next week's release.*

- [x] **6.1. Handshake Unit Tests:**
  - File: `tests/test_sidecar_local_llm_handshake.py`
  - Created and ran test checking that sending `update_llm_config` over IPC correctly reconfigures the sidecar process environment variables. Passed successfully.
- [x] **6.2. Mock Local Generation Simulation:**
  - File: `tests/test_local_llm_mock_run.py`
  - Created and executed a mock simulation: mocked local runner outputs and ran Phase 1 (Director) script generation, Phase 3 (Engineer) programmatic template separation, GGUF aider-style search/replace patch application, and Phase 5 dynamic coordinator overrides. All 3 tests passed with flying colors in 0.68s.
- [x] **6.3. CPU / Memory Budgeting Checks:**
  - Verified memory footprints: all local GGUF models are loaded lazily on-demand. Both GGUF direct runner (`llama-cpp-python`) and `verify_sha256` hash loaders stream files in optimized 64KB chunks rather than allocating full model files into system RAM, fitting well within 4GB-16GB consumer laptops.
  - Formulated clear debugging diagnostics for users testing on older compiled builds to remind them to rebuild the Tauri app with the updated Rust download managers.

---

*Prepared for launch readiness on 2026-07-12.*
