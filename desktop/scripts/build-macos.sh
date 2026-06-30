#!/usr/bin/env bash
# Full macOS production build for Matemium desktop.
# Supports Apple Silicon (aarch64) and Intel (x86_64).
# Run on the matching macOS host / runner.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="${VENV:-$ROOT/.venv}"

# Default to Apple Silicon (modern default). Override via env for Intel builds.
TRIPLE="${MATEMIUM_TARGET_TRIPLE:-aarch64-apple-darwin}"

# Portable pip
if [[ -x "$VENV/bin/pip" ]]; then
  PIP="$VENV/bin/pip"
elif [[ -x "$VENV/Scripts/pip.exe" ]]; then
  PIP="$VENV/Scripts/pip.exe"
else
  PIP="pip"
fi

if [[ ! -x "$VENV/bin/python" && ! -x "$VENV/Scripts/python.exe" ]]; then
  echo "Missing venv at $VENV — run appropriate setup for macOS"
  exit 1
fi

echo "==> Building matemium-sidecar for $TRIPLE"
export MATEMIUM_TARGET_TRIPLE="$TRIPLE"
"$PIP" install pyinstaller -q
"$ROOT/desktop/scripts/build-sidecar.sh"

# build-sidecar.sh already installs to binaries/ with correct name.
# We still ensure the expected name exists for the rest of the flow.

if [[ ! -f "$ROOT/desktop/app/package.json" ]]; then
  echo "Frontend not scaffolded yet — skip npm build"
  exit 0
fi

echo "==> Building frontend"
cd "$ROOT/desktop/app"
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install --ignore-scripts
fi
npm run build

if [[ ! -f "$ROOT/desktop/src-tauri/Cargo.toml" ]]; then
  echo "Tauri not initialized yet — skip cargo tauri build"
  exit 0
fi

echo "==> Building Tauri bundle (macOS)"
cd "$ROOT/desktop/src-tauri"

# Build for the specific target. Tauri will produce the right bundle for the triple.
cargo tauri build --target "$TRIPLE"

echo "Done. Artifacts under desktop/src-tauri/target/${TRIPLE}/release/bundle/ (or default target/release/bundle/)"
