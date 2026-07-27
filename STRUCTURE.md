# Matemium Monorepo Structure

**Status:** Authoritative (2026-07-27)

Three deployable products + one engine share one repository with **strict publish isolation**.

## Publish boundaries (important)

| Target           | Build context / entry            | What it must contain (nothing else)                  | Trigger                     |
|------------------|----------------------------------|------------------------------------------------------|-----------------------------|
| Cloudflare Pages | `website/` only                  | Built static assets from `website/dist`              | Cloudflare dashboard Git integration (or CI) |
| Northflank/PaaS  | `server/Dockerfile` + context `server/` | Only `matemium_server/` + its pyproject               | Docker build on platform    |
| Desktop apps     | `desktop/` + sidecar from root engine | Tauri bundle + platform `matemium-sidecar` binary only | `desktop/scripts/build-*.sh` + CI |
| Engine package   | Root `pyproject.toml` (wheel)    | `canvas/` + `matemium/` only                         | `pip wheel` / hatch         |

**Key safeguards:**
- Root `.dockerignore` — prevents node_modules, target/, outputs/, website/, server/, desktop/ junk from entering the engine Docker image.
- `server/.dockerignore` + explicit build context.
- GitHub workflow only uploads `website/dist`.
- Tauri `externalBin` + Vite `outDir` scoped inside `desktop/`.
- Python sdist trimmed (see pyproject.toml).

Boundaries are also enforced at runtime: engine never imports server code, server never imports canvas, desktop talks over IPC + HTTPS only.

Three deployable products share one repository. Boundaries are strict — no cross-layer imports at build time.

```
math/  (repository root)
│
├── ENGINE — local compilation (Python)
│   ├── canvas/                 Manim compiler core
│   ├── matemium/               CLI + sidecar IPC
│   ├── projects/               Dev harness scenes
│   ├── pyproject.toml          Engine package
│   └── scripts/                Dev / legacy scripts
│
├── SERVER — cloud middleware (isolated publish)
│   └── server/
│       ├── Dockerfile          For Northflank / PaaS (build context = server/)
│       ├── pyproject.toml      Separate package
│       └── matemium_server/
│
├── WEBSITE — frontend (isolated publish)
│   └── website/                Vite React app → Cloudflare Pages
│       └── (node build only; never mixed into other publishes)
│
├── DESKTOP — desktop app (isolated bundles)
│   └── desktop/
│       ├── app/                UI (Vite)
│       ├── src-tauri/          Rust + externalBin sidecar
│       ├── packaging/          PyInstaller spec
│       └── scripts/            Build helpers
│
├── DOCS — public Astro/Starlight documentation
│   └── docs/
│
├── SHARED — contracts, templates, and agent prompts (no product runtime code)
│   └── shared/
│
├── .dockerignore               Critical: keeps each Docker context lean
├── .gitignore                  Separates build outputs per layer
│
├── fixtures/ / tests/          Engine only
├── outputs/                    Local renders (gitignored)
│
└── root-level specifications and guides
    ├── AUTHORING_API.md        Current public authoring contract and schemas
    ├── INTRODUCTION.md         Project overview (start here)
    ├── STRUCTURE.md            This file
    ├── desktop-architecture.md Product goals & boundaries
    ├── ai-agent-architecture.md Autonomous agent: tools, patches, self-correction
    ├── PRODUCT-ARCHITECTURE-DECISIONS.md Latest decisions: vector/RAG, lazy sidecar, downloads, gating, YouTube publishing
    ├── PRODUCT-ARCHITECTURE-IMPLEMENTATION.md Step-by-step guide to realize the decisions above in code and packaging (all PAD-0 through PAD-10 implemented)
    ├── architecture.md         Engine design spec
    └── project-spec.md         Feature status
```

## Layer responsibilities

| Layer | Deployed as | Computes | Talks to |
|-------|-------------|----------|----------|
| **Engine** | PyInstaller binary inside desktop | Manim render, lint, import | Desktop via stdin/stdout IPC |
| **Server** | Container / serverless API | Auth, entitlements, LLM proxy | Desktop via HTTPS (chat + tokens) |
| **Desktop** | MSI / DMG / AppImage / DEB | UI only | Engine (IPC) + Server (HTTPS) |

## What stays at repo root (and why)

`canvas/`, `matemium/`, and `projects/` remain at the **repository root** so that:

- `pip install -e .` and `import canvas` keep working without path hacks
- Existing tests, CLI, and Docker flows stay stable
- PyInstaller `pathex` points at repo root

The `engine/README.md` file documents this layer without moving packages.

## Desktop — one codebase, three OS targets

Tauri builds **platform-specific installers from the same `desktop/` tree**. The TypeScript and Rust layers are shared; the **PyInstaller sidecar cannot be cross-compiled** — each OS needs its own native `matemium-sidecar-<triple>` binary, produced on a matching CI runner.

| OS | Artifact | Sidecar triple | Build host |
|----|----------|----------------|------------|
| Windows | MSI / EXE (WebView2) | `x86_64-pc-windows-msvc` | `windows-latest` |
| macOS | DMG (ARM / Intel) | `aarch64-apple-darwin`, `x86_64-apple-darwin` | `macos-latest` |
| Linux | AppImage / DEB | `x86_64-unknown-linux-gnu` | `ubuntu-24.04` |

Release pipeline: **GitHub Actions CI matrix** (three runners per tag). Linux workflow: [`.github/workflows/build-linux.yml`](.github/workflows/build-linux.yml).

See [`desktop/targets/README.md`](desktop/targets/README.md) for cross-compilation rules, `binaries/` layout, path handling, and window-control UX notes.

## Communication boundaries

```
┌─────────────┐   HTTPS (chat, auth)    ┌─────────────┐
│   Desktop   │ ───────────────────────►│   Server    │
│  app + tauri│                         │   (cloud)   │
└──────┬──────┘                         └─────────────┘
       │ NDJSON stdin/stdout
       ▼
┌─────────────┐
│   Engine    │
│  (sidecar)  │
└─────────────┘
```

- **Desktop ↔ Server:** JSON over HTTPS. Chat returns text + code edits — not Sheet DSL JSON.
- **Desktop ↔ Engine:** NDJSON IPC — see [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md).
- **Server ↔ Engine:** No connection. Ever.

## Quick start by role

| Role | Directory | Command |
|------|-----------|---------|
| Engine dev | repo root | `./matemium.sh demo` |
| Sidecar IPC | repo root | `python -m matemium.sidecar` |
| Server dev | `server/` | `pip install -e . && python -m matemium_server` |
| Desktop dev | `desktop/` | See [`desktop/README.md`](desktop/README.md) |
| **Ubuntu app (full)** | — | [`COMPLETE_LINUX_UBUNTU_APP_TODO.md`](COMPLETE_LINUX_UBUNTU_APP_TODO.md) |
| **Ubuntu dev setup** | `desktop/scripts/` | `setup-ubuntu-dev.sh` → `verify-phase0.sh` |

## Related documents

- Project introduction: [`INTRODUCTION.md`](INTRODUCTION.md)
- Product architecture: [`desktop-architecture.md`](desktop-architecture.md)
- AI agent architecture: [`ai-agent-architecture.md`](ai-agent-architecture.md)
- Latest product & intelligence decisions: [`PRODUCT-ARCHITECTURE-DECISIONS.md`](PRODUCT-ARCHITECTURE-DECISIONS.md)
- How to apply them: [`PRODUCT-ARCHITECTURE-IMPLEMENTATION.md`](PRODUCT-ARCHITECTURE-IMPLEMENTATION.md) (phases 0-10 complete)
- Engine spec: [`architecture.md`](architecture.md)
- Current authoring API: [`AUTHORING_API.md`](AUTHORING_API.md)
- Public documentation source: [`docs/README.md`](docs/README.md)
- Status tracker: [`project-spec.md`](project-spec.md)
