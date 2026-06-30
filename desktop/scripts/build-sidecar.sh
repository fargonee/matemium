#!/usr/bin/env bash
# Build matemium-sidecar PyInstaller binary and install into Tauri binaries/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SPEC="$ROOT/desktop/packaging/matemium-sidecar.spec"
VENV="${VENV:-$ROOT/.venv}"
TRIPLE="${MATEMIUM_TARGET_TRIPLE:-x86_64-unknown-linux-gnu}"

# Portable Python / pip detection (Linux/macOS .venv/bin vs Windows .venv/Scripts)
if [[ -x "$VENV/bin/python" ]]; then
  PYTHON="$VENV/bin/python"
  PIP="$VENV/bin/pip"
elif [[ -x "$VENV/Scripts/python.exe" ]]; then
  PYTHON="$VENV/Scripts/python.exe"
  PIP="$VENV/Scripts/pip.exe"
else
  echo "Missing engine venv at $VENV (looked for bin/python and Scripts/python.exe)"
  echo "Create with: python -m venv .venv && .venv/bin/pip install -e '.[dev]' pyinstaller"
  exit 1
fi

if ! "$PIP" show pyinstaller >/dev/null 2>&1; then
  echo "Installing PyInstaller into $VENV ..."
  "$PIP" install pyinstaller
fi

echo "==> Building sidecar from $SPEC"
cd "$ROOT"

# Use python -m PyInstaller (most reliable across platforms)
"$PYTHON" -m PyInstaller "$SPEC" --noconfirm --clean

OUT="$ROOT/dist/matemium-sidecar"
if [[ -f "${OUT}.exe" ]]; then
  OUT="${OUT}.exe"
  TAURI_NAME="matemium-sidecar-${TRIPLE}.exe"
else
  TAURI_NAME="matemium-sidecar-${TRIPLE}"
fi

if [[ ! -f "$OUT" ]]; then
  echo "FAIL: expected output not found at dist/matemium-sidecar"
  exit 1
fi

chmod +x "$OUT" 2>/dev/null || true
echo "==> Built: $OUT ($(du -h "$OUT" | cut -f1))"

BIN_DIR="$ROOT/desktop/src-tauri/binaries"
mkdir -p "$BIN_DIR"
cp "$OUT" "$BIN_DIR/$TAURI_NAME"
chmod +x "$BIN_DIR/$TAURI_NAME" 2>/dev/null || true
echo "==> Installed Tauri externalBin: $BIN_DIR/$TAURI_NAME"

echo "==> Smoke test"
BIN="$BIN_DIR/$TAURI_NAME" "$ROOT/desktop/scripts/verify-sidecar-binary.sh" || true

echo ""
echo "Phase 2 complete. Binary ready for Tauri externalBin."