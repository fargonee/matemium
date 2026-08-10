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
WS_IPC="$WS"
if command -v cygpath >/dev/null 2>&1; then
  # Git Bash paths such as /tmp/... are not always visible to native Windows
  # binaries. Use a Windows-native path with forward slashes so it is also
  # safe to embed in JSON without escaping backslashes.
  WS_IPC="$(cygpath -m "$WS")"
fi
resp="$(echo "{\"type\":\"request\",\"id\":\"2\",\"command\":\"list_scenes\",\"params\":{\"workspace\":\"$WS_IPC\"}}" | "$BIN" 2>/dev/null | tail -1)"
echo "$resp"
echo "$resp" | grep -q 'PortraitDemo' || { echo "FAIL: list_scenes"; exit 1; }

echo "==> IPC check_project"
resp="$(echo "{\"type\":\"request\",\"id\":\"3\",\"command\":\"check_project\",\"params\":{\"workspace\":\"$WS_IPC\",\"scene\":\"PortraitDemo\"}}" | "$BIN" 2>/dev/null | tail -1)"
echo "$resp"
echo "$resp" | grep -q '"ok": true' || { echo "FAIL: check_project"; exit 1; }

if command -v ffmpeg >/dev/null 2>&1; then
  echo "==> IPC render_project (preview — requires ffmpeg + LaTeX)"
  out="$WS/renders"
  mkdir -p "$out"
  out_ipc="$out"
  if command -v cygpath >/dev/null 2>&1; then
    out_ipc="$(cygpath -m "$out")"
  fi
  resp="$(echo "{\"type\":\"request\",\"id\":\"4\",\"command\":\"render_project\",\"params\":{\"workspace\":\"$WS_IPC\",\"scene\":\"PortraitDemo\",\"quality\":\"preview\",\"output_dir\":\"$out_ipc\"}}" | "$BIN" 2>/dev/null | tail -1 || true)"
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
