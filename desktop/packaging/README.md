# Matemium Sidecar Packaging (PyInstaller)

Freezes `matemium-sidecar` — the local Manim compilation engine for the desktop app.

**Phase 10 update:** Asset manifest (`shared/assets/manifest.json`) is runtime data (downloaded/updated separate from binary). Sidecar binary remains minimal control-plane. See root `PRODUCT-ARCHITECTURE-IMPLEMENTATION.md` §11 for CI, size guards, feature flags (lite vs intelligence).

## Cross-compilation: not supported

PyInstaller produces a **native binary for the OS it runs on**. You cannot build the Linux sidecar on Windows (or vice versa). Each release requires:

1. Run `build-sidecar.sh` **on the target OS** (or on the matching GitHub Actions runner).
2. Copy the output to `desktop/src-tauri/binaries/matemium-sidecar-<target-triple>`.
3. Run `cargo tauri build` on that same host.

See [`../targets/README.md`](../targets/README.md) for the full CI/CD matrix and `externalBin` layout.

## Build

```bash
# From repository root (engine venv active or auto-detected)
./desktop/scripts/build-sidecar.sh
```

The Aider-backed agent runtime is a separate uv-managed Python environment. It
is intentionally not installed into Matemium's engine venv, so the engine can
move independently of Aider's Python support window.

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]' pyinstaller
./desktop/scripts/setup-aider-runtime.sh
```

The setup script provisions `aider-chat` with uv using Python 3.12 by default
and writes it to `.aider-runtime` for dev builds. The sidecar can also
self-provision the runtime into `MATEMIUM_AIDER_RUNTIME_DIR` when a bundled or
system `uv` executable is available. Release installers must therefore ship `uv`
beside the app or preinstall the runtime under the app data directory at
`bin/aider-runtime`. End users must not be asked to run setup scripts.

Local autonomous edits do not require a user-managed Ollama install. The
sidecar starts Matemium's OpenAI-compatible local provider on loopback and
serves the selected downloaded GGUF model to Aider as `openai/matemium-local`.

Artifacts:

| Path | Purpose |
|------|---------|
| `dist/matemium-sidecar` | Frozen binary (this directory's parent = repo root) |
| `desktop/src-tauri/binaries/matemium-sidecar-x86_64-unknown-linux-gnu` | Tauri `externalBin` (Linux amd64) |

Verify:

```bash
./desktop/scripts/verify-sidecar-binary.sh
```

## Runtime dependencies (not bundled in v1)

**FFmpeg** is still required from the host (for final video encoding).

**LaTeX** is a host prerequisite for the launch release. The Debian package
declares the needed TeX Live packages; AppImage, Windows, and macOS users install
TeX separately as documented in [`../../RELEASING.md`](../../RELEASING.md).
The sidecar still recognizes a TinyTeX installation in the Matemium data
directory, but the app does not automatically download one in this release.

| Tool | Used for |
|------|----------|
| `ffmpeg` | Video encoding |
| `pdflatex` + dvisvgm (TinyTeX or system) | Math typesetting |

`lint_project` optionally calls `ruff` if installed on PATH; otherwise syntax check via `py_compile` only.

## Spec file

[`matemium-sidecar.spec`](matemium-sidecar.spec) — entry `matemium/sidecar.py`, bundles `canvas/`, `matemium/`, Manim data files.

## Platform triples (Tauri `externalBin`)

| OS | Binary name |
|----|-------------|
| Linux amd64 | `matemium-sidecar-x86_64-unknown-linux-gnu` |
| macOS Intel | `matemium-sidecar-x86_64-apple-darwin` |
| macOS ARM | `matemium-sidecar-aarch64-apple-darwin` |
| Windows | `matemium-sidecar-x86_64-pc-windows-msvc.exe` |

**Build on each target platform only.** CI matrix details: [`../targets/README.md`](../targets/README.md) § CI/CD matrix.
