# Development setup

This is the clean-machine setup for the Matemium monorepo. The supported
development baseline is Python 3.12, Node.js 22, and the stable Rust toolchain.

## Dependency sources of truth

| Layer | Manifest | Reproducible lock/install file |
|---|---|---|
| Engine and desktop sidecar | `pyproject.toml` | `uv.lock` |
| Cloud server | `server/pyproject.toml` | `server/uv.lock` |
| Desktop UI | `desktop/app/package.json` | `desktop/app/package-lock.json` |
| Website | `website/package.json` | `website/package-lock.json` |
| Documentation site | `docs/package.json` | `docs/pnpm-lock.yaml` |
| Tauri shell | `desktop/src-tauri/Cargo.toml` | `desktop/src-tauri/Cargo.lock` |

The root `.python-version`, `.nvmrc`, and `rust-toolchain.toml` select the
expected language toolchains. `requirements.txt`, `requirements-dev.txt`, and
`requirements-desktop.txt` are pip-compatible entry points; `uv.lock` is the
fully pinned Python resolution used for repeatable development installs.

## Native prerequisites

All platforms need Git, Python 3.12, Node.js 22, Rust via rustup, FFmpeg, and a
LaTeX distribution that provides `pdflatex` and `dvisvgm`. Install Tauri CLI v2:

```bash
cargo install tauri-cli --version "^2.0.0" --locked
```

Platform-specific requirements:

- Ubuntu/Debian: WebKitGTK 4.1, GTK 3, AppIndicator, Cairo, Pango, build tools,
  FFmpeg, and TeX Live. The repository setup script installs the complete list.
- macOS: Xcode Command Line Tools, FFmpeg, Cairo/Pango/pkg-config, and MacTeX.
  Homebrew packages: `brew install ffmpeg cairo pango pkg-config`; install
  MacTeX separately and ensure its binaries are on `PATH`.
- Windows: Visual Studio Build Tools with **Desktop development with C++**,
  WebView2, FFmpeg, and MiKTeX. Use the MSVC Rust toolchain. Git Bash is needed
  for the repository's `.sh` packaging helpers.

Tauri maintains the detailed native prerequisite list at
<https://v2.tauri.app/start/prerequisites/>. Manim maintains its platform notes
at <https://docs.manim.community/en/stable/installation.html>.

## Full desktop checkout

Clone the repository, then install the pinned Python and Node dependencies:

```bash
git clone https://github.com/fargonee/matemium.git
cd matemium

uv sync --python 3.12 --extra dev --extra intelligence --frozen
npm ci --prefix desktop/app
```

If `uv` is not installed, install it from <https://docs.astral.sh/uv/>. A pip
fallback is available, but resolves compatible versions instead of the exact
lock:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-desktop.txt
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

The Tauri app requires a sidecar compiled on the same operating system and CPU
architecture. Generate it before the first desktop run:

```bash
./desktop/scripts/setup-aider-runtime.sh
./desktop/scripts/build-sidecar.sh
cd desktop
cargo tauri dev
```

On Ubuntu/Debian, the automated equivalent is:

```bash
./desktop/scripts/setup-ubuntu-dev.sh --all
./desktop/scripts/build-sidecar.sh
cd desktop && cargo tauri dev
```

The website may run simultaneously on port 5173; the desktop UI uses port 1420.

## Other development layers

Engine only:

```bash
uv sync --python 3.12 --extra dev --frozen
uv run pytest
```

Cloud server:

```bash
cd server
uv sync --python 3.12 --extra dev --frozen
cp .env.example .env
uv run python -m matemium_server
```

Website:

```bash
npm ci --prefix website
cp website/.env.example website/.env
npm run dev --prefix website
```

Documentation site:

```bash
corepack enable
pnpm --dir docs install --frozen-lockfile
pnpm --dir docs dev
```

## Verification

Run the checks relevant to the layer being changed:

```bash
uv lock --check
uv run pytest
npm run build --prefix desktop/app
cargo test --manifest-path desktop/src-tauri/Cargo.toml
```

Ubuntu/Debian contributors can additionally run
`./desktop/scripts/verify-phase0.sh` to check native programs and local
environments.
