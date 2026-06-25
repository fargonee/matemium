#!/usr/bin/env bash
# Phase 5 gate — Vite React frontend builds and wires to Tauri commands.
# See: COMPLETE_LINUX_UBUNTU_APP_TODO.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP_DIR="$ROOT/desktop/app"
TAURI_DIR="$ROOT/desktop/src-tauri"
FAIL=0

ok() { echo "  OK  $1"; }
fail() { echo "  FAIL $1"; FAIL=1; }

echo "==> Phase 5 verification (TypeScript frontend)"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi

echo "--- 5.1 Scaffold ---"
for f in package.json vite.config.ts src/App.tsx src/api/tauri.ts src/components/Editor.tsx; do
  if [[ -f "$APP_DIR/$f" ]]; then ok "$f"; else fail "missing $f"; fi
done

if [[ -f "$APP_DIR/node_modules/@tauri-apps/api/package.json" ]]; then
  ok "@tauri-apps/api installed"
else
  fail "@tauri-apps/api missing — run npm install in desktop/app"
fi

if [[ -f "$APP_DIR/node_modules/@monaco-editor/react/package.json" ]]; then
  ok "@monaco-editor/react installed"
else
  fail "@monaco-editor/react missing"
fi

echo "--- 5.2 npm run build ---"
cd "$APP_DIR"
if npm run build 2>&1; then
  ok "npm run build"
else
  fail "npm run build"
fi

if [[ -f "$APP_DIR/dist/index.html" ]]; then ok "dist/index.html"; else fail "missing dist"; fi

echo "--- 5.3 Tauri config uses Vite ---"
python3 - <<'PY' "$TAURI_DIR/tauri.conf.json" || fail "tauri.conf.json build section"
import json, sys
cfg = json.load(open(sys.argv[1]))
build = cfg.get("build", {})
assert "npm run dev" in build.get("beforeDevCommand", ""), build
assert "npm run build" in build.get("beforeBuildCommand", ""), build
assert "prefix app" in build.get("beforeDevCommand", ""), build
assert build.get("frontendDist") == "../app/dist", build.get("frontendDist")
asset = cfg.get("app", {}).get("security", {}).get("assetProtocol", {})
assert asset.get("enable") is True, asset
print("  OK  Vite dev/build commands + assetProtocol")
PY

echo "--- 5.4 cargo tauri build ---"
cd "$TAURI_DIR"
if cargo tauri build 2>&1; then
  ok "cargo tauri build (with frontend)"
else
  fail "cargo tauri build"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "Phase 5 verification passed."
  echo "Dev loop: cd desktop/src-tauri && cargo tauri dev"
  exit 0
fi
echo "Phase 5 verification failed."
exit 1