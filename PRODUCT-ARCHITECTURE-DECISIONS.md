# Matemium Product Architecture Decisions

**Date:** 2026-07-02  
**Status:** Authoritative – captures all key decisions from agentic AI through desktop productization.  
**Audience:** Engineers, product, and anyone implementing the transition from prototype to consumer-grade desktop app.  
**Related:** `ai-agent-architecture.md`, `desktop-architecture.md`, `architecture.md`, `INTRODUCTION.md`, `project-spec.md`, `STRUCTURE.md`

This document is now the single source of truth for product-level architecture. The older docs have been updated with references to prevent inconsistency.

This document records the shift from a lightweight research-oriented agent system to a production desktop application that must feel instant on first launch while delivering powerful local AI capabilities.

## 1. Core Philosophy & Product Constraints

- **Local-first, zero cloud rendering.** All video generation, Manim execution, and heavy computation happens on the user’s machine via the sidecar.
- **Tiny first-run experience.** Target ~50 MB installer. Users should not be blocked by large upfront downloads in the installer itself.
- **Strict capability gating.** Users cannot perform any creation, editing, AI-assisted authoring, or rendering work until *all* working dependencies (TinyTeX + embeddings + lazy engines) are present and ready.
- **Value during wait time.** The only allowed activities before full readiness are:
  - Browsing public/community animations
  - Exploring feature banners and marketing content
- **Intelligence as optional, versioned data package.** The “Local Code Intelligence Engine” is not baked into the app binary forever.

## 2. Vector Database & RAG

**Decision:** Full vector database and its management lives **entirely on the user’s machine**, inside the Python sidecar.

- **Storage:** Embedded vector database (recommended: LanceDB for its local-first, serverless characteristics).
- **Scope:** Per-workspace or user-level indexes of `scenes.py`, `assets.py`, past patches, error/fix pairs, and math patterns.
- **Purpose:** Dramatically reduce token usage by replacing full-file context shipping with targeted retrieval. Support the Engineer phase with relevant prior code.
- **Fallback:** Always provide a zero-dependency keyword + section-based retriever when the vector engine is unavailable or disabled.
- **Why not cloud:** Privacy, cost, and offline capability. Aligns with “no cloud rendering” principle.

## 3. Embeddings Model

**Chosen model:** `jina-embeddings-v2-base-code` (ONNX int8 quantized version).

- **Rationale:** Code-specific (excellent for Python/Manim authoring), efficient when quantized.
- **Distribution:** **Not bundled** in the installer or sidecar binary.
- **Delivery:** First-run (and update) download managed by Rust/Tauri layer.
- **Lazy loading:** The embedding runtime and model are loaded into memory only when the intelligence features are first requested.

## 4. MCP (Model Context Protocol)

**Decision:** Support **both** local and hosted MCP.

- **Local MCP:** Runs inside the Python sidecar. Exposes grounded tools and resources:
  - `view_file`, `edit_file`, `compile_manim`
  - Vector-retrieved resources (code chunks, past successful patterns)
  - File system and render-related capabilities
- **Hosted MCP:** Runs on Matemium servers. Provides non-grounded augmentation (shared patterns, community indexes, higher-level orchestration, possibly better models for certain phases).
- **Future direction:** The internal agent loop may evolve to act as an MCP client. Local MCP is the source of truth for anything that touches the user’s workspace.

## 5. Sidecar Architecture – Minimal Control Plane

**Decision:** The PyInstaller sidecar binary is a **lightweight control plane**.

- Only the IPC server, protocol handling, and minimal bootstrap code are loaded at startup.
- Zero heavy imports (`manim`, embeddings runtime, vector DB, etc.) at the top level of `matemium/sidecar.py` or entry points.
- One single sidecar process (spawning multiple processes adds too much IPC and state complexity).

## 6. Lazy Loading Strategy

**Pattern:** Lazy Registry / Deferred Singleton.

```python
# Example pattern (to be implemented in a central lazy module)
_manim_engine = None
_jina_embedder = None
_vector_store = None

def get_manim_engine():
    global _manim_engine
    if _manim_engine is None:
        import manim  # only now
        _manim_engine = ...
    return _manim_engine
```

- All heavy dependencies (Manim, embeddings, vector DB, full agent modules) are imported **on first use** after the application has launched.
- Loading is triggered by user actions (first render request, first agent turn, first index build).
- Progress must be surfaced to the UI.

**Loading Phases (sent as status events over IPC):**
- `CORE_READY`
- `ENGINE_LOADING` (Manim / canvas)
- `EMBEDDING_READY`
- `INTELLIGENCE_READY` (vector store + retriever)
- `FULLY_READY`

## 7. Asset & Model Lifecycle (Download & Management)

**Division of responsibility (industry-standard split):**

| Responsibility       | Owner          | Reason |
|----------------------|----------------|--------|
| Downloading models & data packages | Rust / Tauri   | Native progress UI, resume, pause, checksum verification before handing path to Python |
| Storing & verifying files | Rust / Tauri   | Security (SHA256 + signed manifest), proper AppData paths |
| Using / loading the assets | Python sidecar | Domain logic lives here |

**Key rules:**
- Models and data packages (TinyTeX, Jina ONNX int8, future fine-tunes) live in user-writable locations:
  - Windows: `%LOCALAPPDATA%\Matemium\...`
  - macOS: `~/Library/Application Support/Matemium/...`
  - Linux: `~/.local/share/Matemium/...` or XDG
- Never ship model weights inside the installer or PyInstaller binary.
- Versioning via cloud JSON manifest. App checks manifest on launch.
- Decoupled from app version → ability to push improved embeddings without forcing a full desktop update.
- Integrity: Rust verifies checksum/signature. On mismatch, Python sidecar should raise a clear error so Rust can delete and re-download.

## 8. First-Run & Installer Experience

- Target installer size: ~50 MB.
- On first launch: show a sleek dark “obsidian” loading screen with neon cyan progress bar.
- Message example: “Local Code Intelligence Engine is securely downloading…”
- Background downloads happen while user can still explore public content and banners.
- Downloads are resumable and report clear progress.

## 9. User Experience Gating (Strict Gate)

**Hard rule:** No creation work is possible until the app reaches `FULLY_READY`.

**Allowed in pre-ready state:**
- Browsing public animations (YouTube embeds)
- Exploring feature banners and product discovery content

**Blocked until ready:**
- Creating/editing projects
- AI chat / agent (Director, Engineer, etc.)
- Rendering
- Local workspace operations that require engines

The gate is enforced in the Tauri layer and reflected in all UI surfaces.

## 10. Public Gallery & Thin Publishing

**Decision:** Publishing is intentionally thin. No video storage on Matemium servers.

- Finished videos are published to the **official Matemium YouTube channel**.
- Desktop app plays and displays videos using YouTube embeds/players.
- Server only stores **metadata**:
  - `youtube_id`
  - `title`, `description`, `tags`
  - `author` / attribution info
  - `published_at`, `featured`, etc.
- No MP4 files, no large media blobs.

**Publishing flow (high level):**
1. User completes a render while in `READY` state.
2. “Publish to Community” action appears.
3. User submits metadata.
4. Submission goes to server (thin metadata record).
5. Video is uploaded to official channel (manual or automated via YouTube API + review).
6. Server updates the record with the final `youtube_id`.
7. The video appears in public gallery for all users.

**Gallery characteristics:**
- Works completely before any local heavy dependencies are ready.
- Powered by server metadata API + YouTube playback.
- Search, filter, featured content supported.

## 11. Agent Loop & Tool Calling

- Original multi-phase lifecycle (`LifecycleCoordinator`) remains.
- Tool surface (`view_file`, `edit_file`, `compile_manim`) is now also exposed through local MCP when ready.
- RAG / retrieval is injected as a dependency (similar to existing `patch_fn`, `compile_fn`).
- Self-correction loop only uses full intelligence features when `EMBEDDING_READY` / `INTELLIGENCE_READY`.
- Context bundling will evolve to use retrieved chunks instead of full files where possible.

## 12. Rust ↔ Python Communication

- Primary channel remains NDJSON over stdio (existing IPC protocol).
- Extended with status events for loading phases.
- Rust owns:
  - Downloads
  - Readiness state
  - Public gallery data fetching
  - File system access for user workspaces
- Python owns:
  - Lazy engines
  - Agent logic
  - Vector operations
  - Local MCP server
- A small set of new commands (`get_status`, possibly `trigger_load`) will be added.

## 13. Build, Packaging & Distribution

- PyInstaller spec and hooks will be updated for a minimal control-plane sidecar.
- Heavy data (models) moved to first-run download path.
- Two conceptual builds or feature flags may be considered later (lite vs full intelligence).
- Manifest + asset versioning is independent of the desktop release cycle.

## 14. Open / Future Decisions

- Exact moderation/approval workflow for YouTube publishing.
- Whether to wire YouTube Data API automation early or start manual.
- Depth of local MCP server exposure (tools vs resources vs prompts).
- Memory/CPU budgeting when running embeddings + Manim in the same process.
- Offline behavior and caching strategy for public gallery metadata.
- How hosted MCP will consume or surface local capabilities.
- Future model fine-tunes (e.g., “Math-focused Jina”) and their manifest entries.

## Summary Table of Major Shifts

| Area                    | Before (Prototype)              | After (Product)                              |
|-------------------------|---------------------------------|----------------------------------------------|
| Vector DB               | None                            | Fully local in sidecar (LanceDB + Jina)     |
| Embeddings              | N/A                             | jina-embeddings-v2-base-code ONNX int8      |
| Model delivery          | Bundled or none                 | First-run download (Rust)                   |
| Sidecar                 | Eager full engine               | Minimal control plane + lazy registry       |
| Public content          | None                            | YouTube + thin metadata                     |
| Publishing              | N/A                             | Official channel, metadata only             |
| User gating             | Everything available early      | Strict gate — only gallery + banners        |
| MCP                     | Not used                        | Local + hosted                              |
| Context strategy        | Full file shipping              | Retrieval-first + lazy loading              |

This document should be treated as the single source of truth for these product architecture choices until superseded by a newer version.

**To apply these decisions in code:** follow the concrete steps, phases, file lists and verification guidance in [`PRODUCT-ARCHITECTURE-IMPLEMENTATION.md`](PRODUCT-ARCHITECTURE-IMPLEMENTATION.md).

---

*Last updated during the design conversation of 2026-07-02.*