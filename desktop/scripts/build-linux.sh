#!/usr/bin/env bash
# Full Linux production build — see COMPLETE_LINUX_UBUNTU_APP_TODO.md Phase 7
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="${VENV:-$ROOT/.venv}"
TRIPLE="x86_64-unknown-linux-gnu"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Missing venv at $VENV — run: python3 -m venv .venv && pip install -e '.[dev]' pyinstaller"
  exit 1
fi

echo "==> Building matemium-sidecar"
"$VENV/bin/pip" install pyinstaller -q
"$ROOT/desktop/scripts/build-sidecar.sh"

mkdir -p "$ROOT/desktop/src-tauri/binaries"
cp "$ROOT/dist/matemium-sidecar" \
  "$ROOT/desktop/src-tauri/binaries/matemium-sidecar-${TRIPLE}"
chmod +x "$ROOT/desktop/src-tauri/binaries/matemium-sidecar-${TRIPLE}"

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