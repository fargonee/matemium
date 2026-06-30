#!/usr/bin/env bash
# Smoke-test the PyInstaller matemium-sidecar binary (Phase 2 acceptance).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BIN="${BIN:-$ROOT/dist/matemium-sidecar}"
DEMO="$ROOT/projects/demo/scenes.py"

if [[ ! -x "$BIN" ]]; then
  echo "FAIL: sidecar binary not found or not executable: $BIN"
  echo "Run: ./desktop/scripts/build-sidecar.sh"
  exit 1
fi

echo "==> Binary: $BIN"
echo "==> Version"
"$BIN" --version

echo "==> IPC ping"
resp="$(echo '{"type":"request","id":"1","command":"ping","params":{}}' | "$BIN" 2>/dev/null | tail -1)"
echo "$resp"
echo "$resp" | grep -q '"ok": true' || { echo "FAIL: ping"; exit 1; }

echo "==> IPC list_scenes (demo workspace)"
WS="$(mktemp -d)"
trap 'rm -rf "$WS"' EXIT
cp "$DEMO" "$WS/scenes.py"
resp="$(echo "{\"type\":\"request\",\"id\":\"2\",\"command\":\"list_scenes\",\"params\":{\"workspace\":\"$WS\"}}" | "$BIN" 2>/dev/null | tail -1)"
echo "$resp"
echo "$resp" | grep -q 'PortraitDemo' || { echo "FAIL: list_scenes"; exit 1; }

echo "==> IPC check_project"
resp="$(echo "{\"type\":\"request\",\"id\":\"3\",\"command\":\"check_project\",\"params\":{\"workspace\":\"$WS\",\"scene\":\"PortraitDemo\"}}" | "$BIN" 2>/dev/null | tail -1)"
echo "$resp"
echo "$resp" | grep -q '"ok": true' || { echo "FAIL: check_project"; exit 1; }

if command -v ffmpeg >/dev/null 2>&1; then
  echo "==> IPC render_project (preview — requires ffmpeg + LaTeX)"
  out="$WS/renders"
  mkdir -p "$out"
  resp="$(echo "{\"type\":\"request\",\"id\":\"4\",\"command\":\"render_project\",\"params\":{\"workspace\":\"$WS\",\"scene\":\"PortraitDemo\",\"quality\":\"preview\",\"output_dir\":\"$out\"}}" | "$BIN" 2>/dev/null | tail -1 || true)"
  echo "$resp"
  if echo "$resp" | grep -q '"video"'; then
    echo "Render smoke passed"
  else
    echo "WARN: render_project did not return video (common on CI if LaTeX not fully available). This is non-fatal for the binary build."
  fi
else
  echo "SKIP: render_project (ffmpeg not on PATH)"
fi

echo ""
echo "Phase 2 sidecar binary: OK"