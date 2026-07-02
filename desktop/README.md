# Matemium Desktop Application

Cross-platform Tauri v2 app — **one shared codebase** for the UI and Rust shell; **per-platform PyInstaller sidecars** built via a CI matrix (sidecars cannot be cross-compiled). See [`targets/README.md`](targets/README.md).

## Layout

```
desktop/
├── app/                TypeScript UI — editor, AI chat, preview
├── src-tauri/          Rust shell — sidecar lifecycle, workspaces, invoke bridge
├── packaging/          PyInstaller spec for matemium-sidecar binary
├── scripts/            Build helpers
└── targets/            Per-OS artifact notes
```

## Related layers (outside `desktop/`)

| Layer | Path |
|-------|------|
| Engine | [`canvas/`](../canvas/), [`matemium/`](../matemium/) — see [`engine/README.md`](../engine/README.md) |
| Cloud API | [`server/`](../server/) |
| Contracts | [`shared/`](../shared/) |

## Design summary

- **One `scenes.py` per project** (v1) — `CanvasBuilder` + `CanvasScene`
- **Code editor** with Python syntax highlighting and linters
- **AI chat** — mini-Cursor; patches `scenes.py` via cloud chat API
- **Local render only** — sidecar imports project code and runs Manim

See [`desktop-architecture.md`](../desktop-architecture.md).

## Build phases

| Phase | Status | Artifact |
|-------|--------|----------|
| P0 — Document | done | `desktop-architecture.md`, `STRUCTURE.md` |
| P1 — Sidecar IPC | **done** | Project commands + `workspace_project.py` |
| P2 — PyInstaller | **done** | `dist/matemium-sidecar` + Tauri `binaries/` |
| P3 — Tauri scaffold | **done** | `src-tauri/` + `.deb` / `.AppImage` |
| P4 — Rust shell | **done** | sidecar IPC, project CRUD, `cloud_chat` |
| P5 — UI shell | **done** | Vite + React + Monaco MVP |
| P6 — Cloud client + auth | **done** | `auth_login` + `cloud_chat` → [`server/`](../server/) |
| P7 — Linux ship | **done** | `build-linux.sh` → `.deb` / `.AppImage`; CI in [`.github/workflows/build-linux.yml`](../.github/workflows/build-linux.yml) |
| P8 — CI matrix (Win/Mac) | done | Windows + macOS GitHub Actions workflows + native sidecars for all platforms (see `.github/workflows/build-*.yml`) |
| **P9-P10 (PAD 8-10)** | **done** | Publishing+Gallery, MCP+Agent, full Packaging/CI/cross-platform + docs refresh (root `PRODUCT-ARCHITECTURE-IMPLEMENTATION.md`) |

## Phase 0 — Ubuntu dev setup (do this first)

```bash
./desktop/scripts/setup-ubuntu-dev.sh --all   # apt + venvs + Rust + Node
./desktop/scripts/verify-phase0.sh            # must pass before Phase 2+
```

See [`COMPLETE_LINUX_UBUNTU_APP_TODO.md`](../COMPLETE_LINUX_UBUNTU_APP_TODO.md) Phase 0.

## Quick test — sidecar (from repo root)

```bash
echo '{"type":"request","id":"1","command":"ping","params":{}}' | python -m matemium.sidecar
```

## Running the desktop app in dev mode

**Important:** `cargo tauri dev` must be started while your shell is in the `desktop/` folder (your prompt should end in `/desktop$`, **not** `/desktop/app$`).

```bash
cd desktop
cargo tauri dev
```

If you are deep inside `app/` or elsewhere, you can also do:

```bash
cargo tauri dev --manifest-path desktop/src-tauri/Cargo.toml
```

(You only need to `npm install` inside `desktop/app` once.)

## Ship on Ubuntu

```bash
./desktop/scripts/build-linux.sh
sudo dpkg -i desktop/src-tauri/target/release/bundle/deb/Matemium_*.deb
sudo apt -f install -y   # ffmpeg (+ TinyTeX delivered as first-run asset by the app)
```

**Full checklist:** [`COMPLETE_LINUX_UBUNTU_APP_TODO.md`](../COMPLETE_LINUX_UBUNTU_APP_TODO.md) — Phases 0–7 and 9 complete; Phase 8 (clean VM validation) deferred until a fresh Ubuntu 24.04 image is available.