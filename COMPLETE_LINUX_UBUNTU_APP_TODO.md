# Complete Linux / Ubuntu App — Master TODO

**Goal:** Ship a **working Matemium Canvas desktop application on Ubuntu** that a non-developer can install, create a project, edit `scenes.py`, chat with AI (stub or real server), lint/check, render a video locally, and play back the MP4 — **without installing Python or Manim manually**.

**Definition of done (Ubuntu):**

- [x] `.deb` and `.AppImage` build artifacts produced (`./desktop/scripts/build-linux.sh`)
- [x] App desktop entry + icon in bundle (`.deb` / `.AppImage`; clean VM install → Phase 8 deferred)
- [x] User can create/open/delete a project workspace
- [x] Monaco editor saves `scenes.py`
- [x] Lint + check + render work via the bundled sidecar
- [x] Rendered MP4 plays inside the app (`convertFileSrc` + asset protocol)
- [x] Chat panel talks to `server/` (local stub or deployed API; `auth_login` + `cloud_chat`)
- [x] No terminal required for normal use (GUI app)

**Related docs:** [`STRUCTURE.md`](STRUCTURE.md) · [`desktop-architecture.md`](desktop-architecture.md) · [`desktop/targets/README.md`](desktop/targets/README.md) · [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md)

**Target triple:** `x86_64-unknown-linux-gnu`  
**Primary dev OS:** Ubuntu 22.04 or 24.04 (amd64)

---

## Current baseline (already in repo)

| Item | Status |
|------|--------|
| Engine (`canvas/`, `matemium/`) | ✅ |
| CLI `matemium render` | ✅ |
| Sidecar IPC — `ping`, legacy `dsl` commands | ✅ |
| Sidecar IPC — `lint_project`, `render_project`, … | ✅ |
| Phase 0 scripts (`setup-ubuntu-dev.sh`, `verify-phase0.sh`) | ✅ |
| `server/` FastAPI stub | ✅ |
| `desktop/app/` | ✅ Vite + React + Monaco MVP |
| Phase 6 auth + chat | ✅ `auth_login`, Settings token, `verify-phase6.sh` |
| Phase 7 build script | ✅ `build-linux.sh` → `.deb` + `.AppImage` |
| Phase 9 CI | ✅ `.github/workflows/build-linux.yml` |
| `desktop/src-tauri/` | ✅ Tauri v2 scaffold + sidecar `externalBin` |
| PyInstaller Linux binary | ✅ `dist/matemium-sidecar` (~127MB) |
| Tauri `.deb` / `.AppImage` | ✅ `cargo tauri build` on Ubuntu |

---

## Phase 0 — Ubuntu development machine setup

**Status:** Automated scripts in repo — run once on the machine that **builds** the app.

```bash
# One-shot (apt + Python venvs; add --all for Rust + Node + Tauri CLI)
./desktop/scripts/setup-ubuntu-dev.sh --all

# Verify everything before starting Phase 2
./desktop/scripts/verify-phase0.sh
```

| Step | Script / manual | Required before |
|------|-----------------|-----------------|
| 0.1–0.6 below | `setup-ubuntu-dev.sh` | Phase 1+ engine work |
| 0.2 + 0.4 Rust/Tauri | `--with-rust` or `--all` | Phase 3 |
| 0.3 Node | `--with-node` or `--all` | Phase 5 |
| Verification | `verify-phase0.sh` | Each phase gate |

### 0.1 Base system packages

```bash
sudo apt update
sudo apt install -y \
  build-essential curl git pkg-config \
  libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev \
  webkit2gtk-4.1-dev \
  python3 python3-venv python3-pip \
  ffmpeg \
  texlive-latex-extra texlive-fonts-extra texlive-science \
  cm-super dvipng dvisvgm
```

- [x] All packages install without error (`setup-ubuntu-dev.sh` or manual apt below)
- [x] `ffmpeg -version` works
- [x] `pdflatex --version` works (Manim needs LaTeX for math)
- [x] `verify-phase0.sh` reports 0.1 OK

### 0.2 Rust toolchain

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustup default stable
rustc --version
```

- [x] Rust stable installed

### 0.3 Node.js 20+

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node --version   # v20+
npm --version
```

- [x] Node 20+ installed

### 0.4 Tauri CLI v2

```bash
cargo install tauri-cli --version "^2.0.0" --locked
cargo tauri --version
```

- [x] `cargo tauri` runs

### 0.5 Clone repo + engine venv

```bash
cd ~/Documents/PROJECTS/math   # or your clone path
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install pyinstaller ruff

./matemium.sh demo -q preview   # optional: verify engine renders on this machine
pytest tests/ -q
```

- [x] Engine tests pass (`verify-phase0.sh` runs pytest)
- [x] Sidecar `ping` works (`verify-phase0.sh`)
- [x] Optional: demo render produces MP4 under `outputs/demo/` (needs ffmpeg)

### 0.6 Server dev (parallel track)

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m matemium_server &
curl -s http://127.0.0.1:8080/health | jq .
```

- [x] Server health returns `ok`
- [x] Chat stub returns assistant + `code_edit`
- [x] `verify-phase0.sh` exits 0 (required gate before Phase 2)

**Phase 0 checklist (summary):**

- [x] `./desktop/scripts/setup-ubuntu-dev.sh` (or `--all` before Tauri/UI)
- [x] `./desktop/scripts/verify-phase0.sh` → exit 0

---

## Phase 1 — Engine: workspace-aware sidecar commands

The Ubuntu app authors via **`scenes.py` in user workspaces**, not inline DSL JSON. Implement these **before** PyInstaller — easier to debug in a venv.

### 1.1 Workspace project loader

**Files to add/change:**

- [x] `matemium/workspace_project.py` — load `scenes.py` from arbitrary `workspace` path (not only `projects/<slug>`)
- [x] Set `MATEMIUM_ROOT` = workspace path while importing
- [x] Support `workspace/scenes.py` with one or more `CanvasScene` subclasses (mirror `matemium/projects.py` logic)

**Acceptance:**

- [x] Given `/tmp/test-ws/scenes.py` copied from `projects/demo/scenes.py`, loader returns scene class list
- [x] Unit test in `tests/test_workspace_project.py`

### 1.2 IPC handlers

**Files to change:**

- [x] `matemium/ipc/handlers.py` — add handlers
- [x] `matemium/ipc/PROTOCOL.md` — mark commands as implemented

| Command | Implementation notes |
|---------|---------------------|
| `list_scenes` | `inspect` module for `CanvasScene` subclasses in `scenes.py` |
| `lint_project` | `ruff check` + `py_compile` on `scenes.py`; return `{line, col, message, severity}` |
| `check_project` | Import scene class, instantiate, verify `dsl` attribute — no Manim render |
| `render_project` | `load_scene_class` → `render_scene_class()` with `output_dir` from params |
| `export_sheet` | Extend to accept `workspace` + `scene` (not only inline `dsl`) |

**Acceptance:**

```bash
# Manual IPC test (from repo root, venv active)
WS=$(mktemp -d)
cp projects/demo/scenes.py "$WS/"
echo "{\"type\":\"request\",\"id\":\"1\",\"command\":\"list_scenes\",\"params\":{\"workspace\":\"$WS\"}}" \
  | python -m matemium.sidecar

echo "{\"type\":\"request\",\"id\":\"2\",\"command\":\"check_project\",\"params\":{\"workspace\":\"$WS\",\"scene\":\"PortraitDemo\"}}" \
  | python -m matemium.sidecar

echo "{\"type\":\"request\",\"id\":\"3\",\"command\":\"render_project\",\"params\":{\"workspace\":\"$WS\",\"scene\":\"PortraitDemo\",\"quality\":\"preview\",\"output_dir\":\"$WS/out\"}}" \
  | python -m matemium.sidecar
```

- [x] `list_scenes` returns `PortraitDemo`, etc.
- [x] `check_project` returns `ok: true`
- [x] `render_project` returns `video` path to an existing `.mp4` (run `pytest -m slow`)
- [x] Progress events emitted on stdout during render
- [x] Tests in `tests/test_sidecar_project_ipc.py`

### 1.3 Default project template for desktop

- [x] `shared/templates/scenes.py` — minimal `CanvasBuilder` + `# ---DIV: ...---` example
- [x] `shared/schemas/project.schema.json` already exists — validate `project.json` against it in Rust later

---

## Phase 2 — PyInstaller Linux sidecar binary

Bundle the engine so end users do not need Python.

### 2.1 Harden the spec

**File:** `desktop/packaging/matemium-sidecar.spec`

- [x] Add all `canvas/`, `matemium/` hidden imports + `manimpango` dynamic libs
- [x] Bundle Manim data files (`collect_data_files("manim")`)
- [x] Document that **LaTeX + FFmpeg are runtime deps** — [`desktop/packaging/README.md`](desktop/packaging/README.md)
- [x] Entry point: [`desktop/packaging/sidecar_entry.py`](desktop/packaging/sidecar_entry.py)

```bash
source .venv/bin/activate
./desktop/scripts/build-sidecar.sh
./dist/matemium-sidecar --version   # add if missing: prints version and exits
```

- [x] Binary runs `ping` IPC:

```bash
echo '{"type":"request","id":"1","command":"ping","params":{}}' | ./dist/matemium-sidecar
```

- [x] Binary runs `render_project` against a test workspace (with system FFmpeg + LaTeX installed)

### 2.2 Install sidecar into Tauri binaries dir

```bash
mkdir -p desktop/src-tauri/binaries
cp dist/matemium-sidecar desktop/src-tauri/binaries/matemium-sidecar-x86_64-unknown-linux-gnu
chmod +x desktop/src-tauri/binaries/matemium-sidecar-x86_64-unknown-linux-gnu
```

- [x] Binary name matches Tauri `externalBin` triple convention (`build-sidecar.sh` copies automatically)

---

## Phase 3 — Tauri v2 scaffold (Linux)

**Gate:** `./desktop/scripts/verify-phase3.sh`

### 3.1 Initialize Tauri in `desktop/src-tauri/`

If `Cargo.toml` does not exist yet:

```bash
cd desktop
# If app/ is empty, scaffold frontend first (Phase 4.1), then:
cd src-tauri
cargo init --name matemium-desktop
cargo tauri init \
  --app-name Matemium \
  --window-title "Matemium Canvas" \
  --frontend-dist ../app/dist \
  --dev-url http://localhost:5173
```

- [x] `desktop/src-tauri/Cargo.toml` exists
- [x] `desktop/src-tauri/tauri.conf.json` exists
- [x] `cargo tauri dev` launches a window (placeholder `app/dist/index.html`)

### 3.2 `tauri.conf.json` — Linux + sidecar

- [x] Set `identifier`: `app.matemium.canvas`
- [x] Set `productName`: `Matemium`
- [x] Configure `bundle`:

```json
{
  "bundle": {
    "active": true,
    "targets": ["deb", "appimage"],
    "externalBin": ["binaries/matemium-sidecar"],
    "linux": {
      "deb": {
        "depends": ["ffmpeg", "texlive-latex-extra", "texlive-fonts-extra", "texlive-science", "cm-super", "dvipng", "dvisvgm"]
      }
    }
  }
}
```

- [x] `cargo tauri build` produces `.deb` and `.AppImage` (verify: `./desktop/scripts/verify-phase3.sh`)

### 3.3 Linux system deps for `tauri build`

```bash
sudo apt install -y \
  libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
```

- [x] `cargo tauri build` compiles without missing `-dev` package errors

---

## Phase 4 — Rust shell (orchestration)

**Gate:** `./desktop/scripts/verify-phase4.sh`

### 4.1 Module layout

Create under `desktop/src-tauri/src/`:

| Module | Responsibility |
|--------|----------------|
| `sidecar.rs` | Spawn `matemium-sidecar`, stdin write, stdout reader thread |
| `protocol.rs` | Parse NDJSON `type: request/response/event` |
| `workspace.rs` | App data dir: `~/.local/share/matemium/workspaces/<id>/` |
| `projects.rs` | CRUD `project.json` + `scenes.py` |
| `commands.rs` | Tauri `#[tauri::command]` handlers |
| `cloud.rs` | HTTP client to server (`reqwest`) |

- [x] Each module compiles
- [x] App state holds optional sidecar child process (one daemon per app session)

### 4.2 Sidecar lifecycle

- [x] On first engine request: spawn `externalBin` sidecar with `current_dir` = app data root
- [x] Set env: `MATEMIUM_ROOT=<app-data>` at spawn; `workspace` passed per IPC request
- [x] Dedicated thread reads stdout line-by-line; emits Tauri events `sidecar-event`
- [x] Requests: assign UUID `id`, write JSON line + `\n` to stdin, flush
- [x] Map response `id` → pending oneshot channel (or mutex map)
- [x] On app exit: send `shutdown` command; kill process if hung

**Acceptance:**

- [x] `invoke('sidecar_ping')` returns version from real sidecar binary
- [x] Integration test: `tests/sidecar_integration.rs` + `verify-phase4.sh`

### 4.3 Project workspace commands (Rust)

Expose to TypeScript:

| Tauri command | Behavior |
|---------------|----------|
| `project_list` | List workspaces with `project.json` |
| `project_create` | New UUID dir, write template `scenes.py` + `project.json` |
| `project_open` | Return paths + file contents |
| `project_save` | Write `scenes.py` buffer to disk |
| `project_delete` | Remove workspace dir |
| `sidecar_lint` | IPC `lint_project` |
| `sidecar_check` | IPC `check_project` |
| `sidecar_list_scenes` | IPC `list_scenes` |
| `sidecar_render` | IPC `render_project` |
| `cloud_chat` | POST to `server/v1/chat/completions` |

- [x] All commands registered in `lib.rs` (+ `settings_get` / `settings_set`)
- [x] Capabilities / permissions: `shell:allow-execute` for `matemium-sidecar` sidecar

### 4.4 App data paths (Linux)

| Path | Purpose |
|------|---------|
| `~/.local/share/matemium/workspaces/<id>/` | User projects |
| `~/.local/share/matemium/workspaces/<id>/scenes.py` | Authoring file |
| `~/.local/share/matemium/workspaces/<id>/project.json` | Metadata |
| `~/.local/share/matemium/workspaces/<id>/renders/` | MP4 outputs |
| `~/.config/matemium/settings.json` | Server URL, API token |

- [x] Paths created on first launch (`AppPaths::ensure` in setup)
- [x] No writes outside app data without user picker (future export)

---

## Phase 5 — TypeScript frontend (MVP)

**Gate:** `./desktop/scripts/verify-phase5.sh`

### 5.1 Scaffold

```bash
cd desktop/app
npm create vite@latest . -- --template react-ts
npm install
npm install @tauri-apps/api @monaco-editor/react
```

- [x] `npm run dev` serves UI
- [x] `cargo tauri dev` from `desktop/src-tauri` shows UI in window

### 5.2 Minimum screens

| Screen | Features |
|--------|----------|
| **Project list** | Create / open / delete; calls `project_*` |
| **Editor** | Monaco, Python mode, saves `scenes.py` |
| **Toolbar** | Lint, Check, Render (quality: preview/low) |
| **Scene picker** | Dropdown from `sidecar_list_scenes` |
| **Output** | Log panel for sidecar events + stderr tail |
| **Player** | `<video>` bound to returned MP4 path (Tauri convertFileSrc) |
| **Chat** | Input + history; `cloud_chat`; show diff + Apply button |

- [x] Section outline: parse `# ---DIV:` comments client-side
- [x] Settings: server base URL (default `http://127.0.0.1:8080`)

### 5.3 Error UX

- [x] Lint diagnostics → Monaco markers
- [x] Render failure → show last 50 lines of sidecar stderr in panel
- [x] "Copy errors to chat" button for AI fix loop

**Acceptance (dev mode on Ubuntu):**

- [x] Create project → edit code → check → render preview → video plays (manual via `cargo tauri dev`)
- [x] Chat stub returns suggestion; Apply updates editor buffer

---

## Phase 6 — Server integration

**Gate:** `./desktop/scripts/verify-phase6.sh`

### 6.1 Desktop → server

- [x] `cloud.rs` + TS settings for base URL
- [x] Auth: `auth_login` → store token from `/v1/auth/token` in settings (dev stub OK)
- [x] Chat: send `messages`, `scenes_excerpt` (editor content), `project_id`
- [x] Apply `code_edit.full_file` or search/replace to editor

### 6.2 Deploy server (optional for local-only MVP)

For Ubuntu-only testing, **local stub is enough**:

```bash
cd server && source .venv/bin/activate && python -m matemium_server
```

- [x] Desktop settings point to `http://127.0.0.1:8080`
- [x] Production deploy (Fly.io / Railway) documented in [`server/README.md`](server/README.md)

---

## Phase 7 — Production Linux build

### 7.1 Full build script

Create `desktop/scripts/build-linux.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# 1. Engine venv + sidecar
source .venv/bin/activate
./desktop/scripts/build-sidecar.sh
cp dist/matemium-sidecar \
  desktop/src-tauri/binaries/matemium-sidecar-x86_64-unknown-linux-gnu

# 2. Frontend
cd desktop/app && npm ci && npm run build

# 3. Tauri bundle
cd ../src-tauri && cargo tauri build
```

- [x] Script executable: `chmod +x desktop/scripts/build-linux.sh`
- [x] Produces artifacts under `desktop/src-tauri/target/release/bundle/`

### 7.2 Expected artifacts

| Artifact | Path (typical) |
|----------|----------------|
| `.deb` | `target/release/bundle/deb/Matemium_*.deb` |
| `.AppImage` | `target/release/bundle/appimage/Matemium_*.AppImage` |

- [x] Install `.deb`: `sudo dpkg -i Matemium_*.deb && sudo apt -f install` (artifacts built; clean VM → Phase 8)
- [x] Or run `.AppImage`: `chmod +x Matemium_*.AppImage && ./Matemium_*.AppImage`

### 7.3 Desktop entry

- [x] App appears in GNOME/KDE app menu as "Matemium" (`.desktop` in deb bundle)
- [x] Icon set in `desktop/src-tauri/icons/`

---

## Phase 8 — Clean Ubuntu VM validation

> **Deferred** — requires a fresh Ubuntu 24.04 VM (not this dev host). Artifacts and dev-machine verification complete in Phases 0–7; run this checklist on a clean VM before public release.

**Use a fresh Ubuntu 24.04 VM** (or `distrobox`/`chroot`) — not your dev machine.

### 8.1 Install from package

```bash
sudo dpkg -i Matemium_0.1.0_amd64.deb
sudo apt -f install -y   # pulls ffmpeg, texlive deps from deb depends
```

- [ ] App launches from menu
- [x] No `python3` required in PATH for the app itself (bundled PyInstaller sidecar via `externalBin`; VM re-check in 8.3)

### 8.2 Runtime dependency strategy (pick one)

**Option A — deb dependencies (recommended v1)**  
LaTeX + FFmpeg installed via `.deb` `Depends:` — larger install, reliable renders.

- [x] Document ~500MB–1GB apt install for TeX Live ([`desktop/targets/README.md`](desktop/targets/README.md))
- [ ] First render succeeds on clean VM

**Option B — bundled TeX (v2)**  
Bundle minimal TeX + FFmpeg inside AppImage — complex, larger binary.

- [x] Spike task only; defer unless Option A is unacceptable (Option A chosen; Option B deferred)

### 8.3 End-to-end user script (VM)

> Run on a fresh Ubuntu 24.04 VM after `dpkg -i` — all steps below remain unchecked until then.

Manual test checklist:

1. [ ] Launch Matemium
2. [ ] Create project "Quadratic"
3. [ ] Editor contains template `scenes.py`
4. [ ] Click **Check** → success
5. [ ] Click **Render (preview)** → progress events appear
6. [ ] Wait for completion (< 5 min on VM)
7. [ ] Video plays in app
8. [ ] Open chat → ask "add a heading" → apply edit → re-render

### 8.4 Record blockers

| Issue | Fix |
|-------|-----|
| Sidecar not found | Check `externalBin` name + triple suffix |
| `WebKit` errors | Install `libwebkit2gtk-4.1-0` |
| LaTeX not found | Add apt depends or bundle |
| Blank window | Check `frontendDist` path in `tauri.conf.json` |
| Permission denied on workspace | Fix Tauri FS scope / app data path |

---

## Phase 9 — CI (GitHub Actions)

**Gate:** `.github/workflows/build-linux.yml`

- [x] `runs-on: ubuntu-24.04`
- [x] Install apt deps (Phase 0.1 + webkit dev)
- [x] `pip install -e ".[dev]"` + PyInstaller
- [x] `npm ci` + `npm run build` in `desktop/app`
- [x] `cargo tauri build`
- [x] Upload `.deb` + `.AppImage` as artifacts

- [x] Workflow defined for `main` (passes when pushed to GitHub Actions)

---

## Phase 10 — Polish (post-MVP)

> **Deferred** — post-MVP polish; not required for the first working Ubuntu app.

Not required for first working Ubuntu app, but plan them:

- [ ] Code signing / AppImage `runtime` consistency
- [ ] Auto-update (Tauri updater)
- [ ] `ruff format` on save
- [ ] Section fence UI (collapsible `# ---DIV:`)
- [ ] Reel cutter UI (`cut_reels` IPC)
- [ ] Flatpak as alternative to deb
- [ ] aarch64 Linux (ARM) build — separate triple

---

## Suggested work order (critical path)

```
Phase 0 ─► Phase 1 (sidecar project commands) ─► Phase 2 (PyInstaller)
                    │
                    ▼
Phase 3 (Tauri init) ─► Phase 4 (Rust IPC) ─► Phase 5 (TS MVP)
                    │
                    ▼
Phase 6 (server wire) ─► Phase 7 (build script) ─► Phase 8 (clean VM test)
                    │
                    ▼
              Phase 9 (CI)
```

**Parallel tracks:**

- Server hardening (Phase 6) can proceed alongside Phase 4–5
- UI polish (Phase 10) after Phase 8 passes

---

## Quick reference commands (Ubuntu)

```bash
# Dev loop (after Phases 3–5)
cd server && source .venv/bin/activate && python -m matemium_server &
cd desktop/src-tauri && cargo tauri dev

# Sidecar-only debug
echo '{"type":"request","id":"1","command":"ping","params":{}}' | python -m matemium.sidecar

# Production build
./desktop/scripts/build-linux.sh

# Install
sudo dpkg -i desktop/src-tauri/target/release/bundle/deb/*.deb
```

---

## File checklist (create when missing)

| Path | Phase |
|------|-------|
| `matemium/workspace_project.py` | 1 |
| `tests/test_sidecar_project_ipc.py` | 1 |
| `shared/templates/scenes.py` | 1 |
| `desktop/src-tauri/Cargo.toml` | 3 |
| `desktop/src-tauri/tauri.conf.json` | 3 |
| `desktop/src-tauri/src/sidecar.rs` | 4 |
| `desktop/src-tauri/src/protocol.rs` | 4 |
| `desktop/src-tauri/src/workspace.rs` | 4 |
| `desktop/src-tauri/src/commands.rs` | 4 |
| `desktop/app/package.json` | 5 |
| `desktop/scripts/build-linux.sh` | 7 |
| `.github/workflows/build-linux.yml` | 9 |

---

*Last updated: 2026-06-23 — Phases 0–7 and 9 complete on dev machine; Phase 8 (clean VM) and Phase 10 deferred.*