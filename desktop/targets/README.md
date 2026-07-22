# Desktop Build Targets

One Tauri codebase in [`../`](../) produces installers for all platforms. CI uses a **build matrix** — you do not maintain separate app repos per OS.

## Cross-compilation reality (authoritative)

**The TypeScript and Rust shell are cross-platform. The PyInstaller sidecar is not.**

Because Matemium relies on a local Python rendering engine frozen with PyInstaller, **cross-compilation of the engine is a myth**. A Windows `.exe` cannot run a Linux binary; an Intel Mac binary runs slowly (or via Rosetta) on Apple Silicon. You cannot click "Build" on a Windows laptop and produce a working macOS `.dmg`.

| Layer | Shared across OS? | Build per target? |
|-------|-------------------|-------------------|
| TypeScript UI (`desktop/app/`) | Yes (~99%) | No — Vite bundles once per Tauri build |
| Rust shell (`desktop/src-tauri/`) | Yes (~99%) | Compiled natively on each CI runner |
| **PyInstaller sidecar** | Source yes, **binary no** | **Yes — mandatory on each OS** |

**Rule:** Never assume one PyInstaller artifact ships everywhere. Tauri's **platform-specific sidecars** (`externalBin`) solve runtime selection; CI solves producing each binary.

## Shared codebase, targeted binaries

Tauri automatically packages and invokes **only the matching sidecar** when building an installer for a given OS. The repo holds all platform binaries under one folder; each release build uses exactly one.

```
desktop/src-tauri/
├── src/                    # Shared Rust orchestrator
├── tauri.conf.json         # Shared Tauri config (externalBin entry)
└── binaries/               # Platform-specific sidecars (not cross-compiled)
    ├── matemium-sidecar-x86_64-pc-windows-msvc.exe   # Windows engine
    ├── matemium-sidecar-x86_64-apple-darwin          # Intel Mac engine
    ├── matemium-sidecar-aarch64-apple-darwin         # Apple Silicon M1/M2/M3 engine
    └── matemium-sidecar-x86_64-unknown-linux-gnu     # Linux engine
```

`tauri.conf.json` registers the logical name:

```json
{ "bundle": { "externalBin": ["binaries/matemium-sidecar"] } }
```

At build time, Tauri renames `matemium-sidecar` to `matemium-sidecar-<target-triple>` for the active platform. At runtime, it spawns the binary that matches the user's OS and CPU architecture.

## CI/CD matrix (required for all three installers)

Production releases need **three separate build hosts** — typically a GitHub Actions matrix. Pushing to `main` should spin up parallel runners:

| Runner | Sidecar build | Tauri bundle | Output |
|--------|---------------|--------------|--------|
| **Windows** (`windows-latest`) | PyInstaller → `.exe` | Sign + bundle | `.msi` / `.exe` installer |
| **macOS** (`macos-latest`) | PyInstaller → Mach-O (ARM + Intel as needed) | Codesign + notarize | `.dmg` / `.app` |
| **Linux** (`ubuntu-24.04`) | PyInstaller → ELF | Bundle | `.AppImage` / `.deb` |

Each job runs the same high-level steps:

1. `pip install -e ".[dev]"` + PyInstaller
2. `./desktop/scripts/build-sidecar.sh` (on that runner's OS)
3. Copy artifact to `desktop/src-tauri/binaries/matemium-sidecar-<triple>`
4. `cargo tauri build`
5. Upload platform installer as a CI artifact (or attach to a GitHub Release)

**Current CI:** Full matrix implemented.
- [`.github/workflows/build-linux.yml`](../../.github/workflows/build-linux.yml)
- [`.github/workflows/build-windows.yml`](../../.github/workflows/build-windows.yml)
- [`.github/workflows/build-macos.yml`](../../.github/workflows/build-macos.yml) (both Apple Silicon + Intel)

Implemented matrix (see workflows):

```yaml
# Linux, Windows x64, macOS arm64 + x64
```

**Local dev:** use `cargo tauri dev` on your host OS only — no cross-compile needed for day-to-day work.

## Minor OS differences (frontend + backend)

Keep UX consistent; account for these two platform quirks:

### Window controls

Close, minimize, and maximize live **top-right** on Windows/Linux and **top-left** on macOS. Tauri handles native chrome, but **CSS layout must reserve padding** for the title-bar region on all platforms (e.g. draggable title strip, avoid placing primary actions under traffic lights on macOS).

### File system paths

| OS | Example workspace root |
|----|------------------------|
| Windows | `C:\Users\Name\AppData\Roaming\Matemium\workspaces\` |
| macOS | `/Users/Name/Library/Application Support/Matemium/workspaces/` |
| Linux | `~/.local/share/matemium/workspaces/` |

**Never hardcode `/` or `\`.** Use path-joining APIs everywhere files are read or written:

| Layer | API |
|-------|-----|
| Rust (Tauri) | `std::path::PathBuf`, `tauri::path::BaseDirectory` |
| Python (sidecar) | `os.path.join`, `pathlib.Path` |
| TypeScript (display only) | Paths from Rust invoke results — do not construct OS paths in the UI |

Agent workspace tools operate on approved logical paths such as `scenes.py`, `helpers.py`, and `brief/tape.md`; the Rust orchestrator resolves them against the workspace root with `PathBuf`.

## Summary

Tauri fulfills the cross-platform product goal with **one shared frontend + shell codebase** and **per-platform PyInstaller sidecars** built by an **automated multi-platform CI pipeline**. That combination delivers native, high-performance installers on Windows, macOS, and Linux without maintaining separate app repositories.

---

## Artifacts

| Platform | Triple | Output | Runtime dep |
|----------|--------|--------|-------------|
| **Windows** | `x86_64-pc-windows-msvc` | `.msi` / `.exe` | WebView2 |
| **macOS** | `aarch64-apple-darwin` + `x86_64-apple-darwin` | `.dmg` (universal) | — |
| **Linux** | `x86_64-unknown-linux-gnu` | `.AppImage` / `.deb` | WebKitGTK |

## Prerequisites

| Tool | Windows | macOS | Linux |
|------|---------|-------|-------|
| Rust | rustup | rustup | rustup |
| Node.js | 20+ | 20+ | 20+ |
| Tauri CLI | `cargo install tauri-cli` | same | same |
| Engine sidecar | PyInstaller build → `src-tauri/binaries/` | same | same |

## Build flow (per platform)

1. Build engine sidecar: [`../scripts/build-sidecar.sh`](../scripts/build-sidecar.sh)
2. Copy binary to `src-tauri/binaries/matemium-sidecar-<triple>`
3. `cd desktop/app && npm install && npm run build`
4. `cd desktop/src-tauri && cargo tauri build`

Tauri renames `externalBin` entries to include the target triple automatically.

## Sidecar binary naming

```
desktop/src-tauri/binaries/
├── matemium-sidecar-x86_64-pc-windows-msvc.exe
├── matemium-sidecar-x86_64-apple-darwin
├── matemium-sidecar-aarch64-apple-darwin
└── matemium-sidecar-x86_64-unknown-linux-gnu
```

## Linux runtime dependencies (Option A — deb `Depends:`)

The `.deb` declares apt dependencies for FFmpeg and TeX Live. On a clean Ubuntu 24.04 VM, `sudo apt -f install` after `dpkg -i` pulls roughly **500MB–1GB** of packages (TeX Live is the bulk). The bundled **matemium-sidecar** PyInstaller binary runs Manim locally — **no `python3` in PATH** is required for normal app use.

| Package group | Purpose |
|---------------|---------|
| `ffmpeg` | Video encoding |
| `texlive-latex-extra`, `texlive-fonts-extra`, `texlive-science`, `cm-super`, `dvipng`, `dvisvgm` | Manim math/LaTeX |
| `libwebkit2gtk-4.1-0` | Tauri WebView (usually preinstalled on desktop Ubuntu) |

Post-install validation checklist: [`COMPLETE_LINUX_UBUNTU_APP_TODO.md`](../../COMPLETE_LINUX_UBUNTU_APP_TODO.md) Phase 8.

## Complete Ubuntu build guide

Step-by-step checklist from dev machine setup through `.deb` / `.AppImage` on a clean VM:

**[`COMPLETE_LINUX_UBUNTU_APP_TODO.md`](../../COMPLETE_LINUX_UBUNTU_APP_TODO.md)**

---

## Multi-platform CI (implemented)

All three platforms now have dedicated workflows:
- `build-linux.yml`
- `build-windows.yml`
- `build-macos.yml` (builds both `aarch64-apple-darwin` and `x86_64-apple-darwin`)

**Release process (all platforms):**
- Push a tag `vX.Y.Z` → all full builds run in parallel.
- Artifacts are attached to the same GitHub Release.
- Lightweight verification runs on every PR / main push that touches desktop/engine code.

## Code signing & notarization (required for clean distribution)

Unsigned builds are produced automatically. For professional "live" distribution:

### macOS (strongly recommended)
Store these GitHub repository secrets:
- `APPLE_CERTIFICATE` — base64 of your `.p12` Developer ID Application certificate
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_ID` (Apple ID email)
- `APPLE_PASSWORD` (app-specific password)
- `APPLE_TEAM_ID`

The macOS workflow automatically attempts `codesign` + `notarytool submit` + `stapler` when the secrets exist.

### Windows
Optional but highly recommended to avoid SmartScreen warnings:
- Use a code signing certificate.
- Current Windows workflow produces unsigned `.exe`/`.msi`. You can extend the workflow with `signtool` using a secret-stored certificate (or switch to Azure Trusted Signing).

Without signing you can still distribute, but users on macOS may see security prompts, and Windows users may see "Windows protected your PC".

## Runtime dependencies on end-user machines

The sidecar freezes the Python engine but **does not** bundle ffmpeg or a TeX distribution.

| Platform | Required user install (first run or documented) |
|----------|------------------------------------------------|
| Linux    | Handled via `.deb` `Depends:` (apt will pull ~500MB–1GB) |
| macOS    | MacTeX or BasicTeX + `ffmpeg` (via brew) |
| Windows  | MiKTeX or TeX Live + `ffmpeg` |

The app will guide users or fail gracefully on first render if missing.

## Adding more architectures later

Easy to extend:
- Linux aarch64 → add `ubuntu-24.04-arm` runner + triple
- Windows arm64 → emerging support
- macOS universal → advanced (can be added on top of current native builds)

The current matrix + per-platform sidecar approach is the robust, future-proof foundation.
