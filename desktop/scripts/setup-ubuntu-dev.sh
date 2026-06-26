#!/usr/bin/env bash
# Phase 0 — Ubuntu development machine setup for Matemium desktop builds.
# See: COMPLETE_LINUX_UBUNTU_APP_TODO.md
#
# Usage:
#   ./desktop/scripts/setup-ubuntu-dev.sh              # apt + python venvs only
#   ./desktop/scripts/setup-ubuntu-dev.sh --with-rust   # also install rustup
#   ./desktop/scripts/setup-ubuntu-dev.sh --with-node   # also install Node 20 via nodesource
#   ./desktop/scripts/setup-ubuntu-dev.sh --all         # everything above
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WITH_RUST=false
WITH_NODE=false
SKIP_APT=false

for arg in "$@"; do
  case "$arg" in
    --with-rust) WITH_RUST=true ;;
    --with-node) WITH_NODE=true ;;
    --all) WITH_RUST=true; WITH_NODE=true ;;
    --skip-apt) SKIP_APT=true ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)"
      exit 1
      ;;
  esac
done

echo "==> Matemium Phase 0 setup (repo: $ROOT)"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "ERROR: apt-get not found. This script targets Ubuntu/Debian."
  exit 1
fi

if [[ "$SKIP_APT" == false ]]; then
  echo "==> 0.1 Installing apt packages (sudo required)"
  sudo apt update
  sudo apt install -y \
    build-essential curl git pkg-config \
    libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev \
    libwebkit2gtk-4.1-dev \
    libcairo2-dev libpango1.0-dev \
    python3 python3-venv python3-pip \
    ffmpeg \
    texlive-latex-extra texlive-fonts-extra texlive-science \
    cm-super dvipng dvisvgm \
    jq
  echo "    ffmpeg: $(ffmpeg -version 2>&1 | head -1)"
  echo "    pdflatex: $(pdflatex --version 2>&1 | head -1)"
fi

if [[ "$WITH_RUST" == true ]]; then
  echo "==> 0.2 Installing Rust (rustup)"
  if command -v rustc >/dev/null 2>&1; then
    echo "    rustc already installed: $(rustc --version)"
  else
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
    # shellcheck disable=SC1091
    source "$HOME/.cargo/env"
    rustc --version
  fi
  if ! command -v cargo-tauri >/dev/null 2>&1 && ! cargo tauri --version >/dev/null 2>&1; then
    echo "==> 0.4 Installing Tauri CLI v2"
    cargo install tauri-cli --version "^2.0.0" --locked
  fi
  cargo tauri --version
fi

if [[ "$WITH_NODE" == true ]]; then
  echo "==> 0.3 Installing Node.js 20"
  if command -v node >/dev/null 2>&1 && [[ "$(node -p 'process.versions.node.split(".")[0]')" -ge 20 ]]; then
    echo "    node already installed: $(node --version)"
  else
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
    node --version
    npm --version
  fi
fi

echo "==> 0.5 Engine virtualenv ($ROOT/.venv)"
if [[ ! -d "$ROOT/.venv" ]]; then
  python3 -m venv "$ROOT/.venv"
fi
"$ROOT/.venv/bin/pip" install --upgrade pip -q
"$ROOT/.venv/bin/pip" install -e "$ROOT/.[dev]" pyinstaller ruff -q
echo "    matemium: $("$ROOT/.venv/bin/matemium" --version 2>/dev/null || true)"

echo "==> 0.6 Server virtualenv ($ROOT/server/.venv)"
if [[ ! -d "$ROOT/server/.venv" ]]; then
  python3 -m venv "$ROOT/server/.venv"
fi
"$ROOT/server/.venv/bin/pip" install --upgrade pip -q
"$ROOT/server/.venv/bin/pip" install -e "$ROOT/server/.[dev]" -q
if [[ ! -f "$ROOT/server/.env" ]]; then
  cp "$ROOT/server/.env.example" "$ROOT/server/.env"
  echo "    created server/.env from .env.example"
fi

echo ""
echo "Phase 0 setup complete. Verify with:"
echo "  ./desktop/scripts/verify-phase0.sh"
echo ""
echo "Optional next steps:"
echo "  source $ROOT/.venv/bin/activate && pytest tests/ -q"
echo "  ./matemium.sh demo -q preview"
if [[ "$WITH_RUST" == false ]]; then
  echo "  Re-run with --with-rust (and --with-node) before Phase 3 Tauri work"
fi