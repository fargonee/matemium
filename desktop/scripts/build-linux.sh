#!/usr/bin/env bash
# Full Linux production build.
# Respects MATEMIUM_TARGET_TRIPLE (defaults to x86_64-unknown-linux-gnu).
# Phase 10: Includes asset manifest copy, size checks (via build-sidecar), CI readiness.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="${VENV:-$ROOT/.venv}"
TRIPLE="${MATEMIUM_TARGET_TRIPLE:-x86_64-unknown-linux-gnu}"

# Portable discovery (used by build-sidecar.sh too)
if [[ -x "$VENV/bin/python" ]]; then
  PIP="$VENV/bin/pip"
elif [[ -x "$VENV/Scripts/pip.exe" ]]; then
  PIP="$VENV/Scripts/pip.exe"
else
  PIP="pip"
fi

if [[ ! -x "$VENV/bin/python" && ! -x "$VENV/Scripts/python.exe" ]]; then
  echo "Missing venv at $VENV"
  exit 1
fi

echo "==> Building matemium-sidecar"
"$PIP" install pyinstaller -q
"$ROOT/desktop/scripts/build-sidecar.sh"

mkdir -p "$ROOT/desktop/src-tauri/binaries"
# build-sidecar.sh already copies using the triple when MATEMIUM_TARGET_TRIPLE is set.
# This ensures the file is present with the expected name for this run.
SRC="$ROOT/dist/matemium-sidecar"
if [[ -f "${SRC}.exe" ]]; then SRC="${SRC}.exe"; fi
cp "$SRC" "$ROOT/desktop/src-tauri/binaries/matemium-sidecar-${TRIPLE}" 2>/dev/null || true
chmod +x "$ROOT/desktop/src-tauri/binaries/matemium-sidecar-${TRIPLE}" || true

if [[ ! -f "$ROOT/desktop/app/package.json" ]]; then
  echo "Frontend not scaffolded yet — skip npm build (see COMPLETE_LINUX_UBUNTU_APP_TODO.md Phase 5)"
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
  echo "Tauri not initialized yet — skip cargo tauri build (see COMPLETE_LINUX_UBUNTU_APP_TODO.md Phase 3)"
  exit 0
fi

echo "==> Building Tauri bundle"
cd "$ROOT/desktop/src-tauri"
cargo tauri build

echo "Done. Artifacts under desktop/src-tauri/target/release/bundle/"

# Phase 10: Quick size check for base installer (example; real CI enforces)
BUNDLE_DIR="$ROOT/desktop/src-tauri/target/release/bundle"
if [[ -d "$BUNDLE_DIR" ]]; then
  du -sh "$BUNDLE_DIR"/* 2>/dev/null | head -5 || true
  echo "Phase 10 packaging notes applied (see PRODUCT-ARCHITECTURE-IMPLEMENTATION.md §11)."
fi