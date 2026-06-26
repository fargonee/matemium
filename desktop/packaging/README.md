# Matemium Sidecar Packaging (PyInstaller)

Freezes `matemium-sidecar` — the local Manim compilation engine for the desktop app.

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

The sidecar binary **does not** include FFmpeg or LaTeX. The host system (or `.deb` `Depends:`) must provide:

| Tool | Used for |
|------|----------|
| `ffmpeg` | Video encoding |
| `pdflatex` + TeX Live packages | Math typesetting (`texlive-latex-extra`, `texlive-fonts-extra`, `texlive-science`, `cm-super`, `dvipng`, `dvisvgm`) |

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