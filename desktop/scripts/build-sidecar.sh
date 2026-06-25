#!/usr/bin/env bash
# Build matemium-sidecar PyInstaller binary and install into Tauri binaries/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SPEC="$ROOT/desktop/packaging/matemium-sidecar.spec"
VENV="${VENV:-$ROOT/.venv}"
TRIPLE="${MATEMIUM_TARGET_TRIPLE:-x86_64-unknown-linux-gnu}"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Missing engine venv at $VENV"
  echo "Run: ./desktop/scripts/setup-ubuntu-dev.sh"
  exit 1
fi

if [[ ! -x "$VENV/bin/pyinstaller" ]]; then
  echo "Installing PyInstaller into $VENV ..."
  "$VENV/bin/pip" install pyinstaller
fi

echo "==> Building sidecar from $SPEC"
cd "$ROOT"
"$VENV/bin/pyinstaller" "$SPEC" --noconfirm --clean

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

chmod +x "$OUT"
echo "==> Built: $OUT ($(du -h "$OUT" | cut -f1))"

BIN_DIR="$ROOT/desktop/src-tauri/binaries"
mkdir -p "$BIN_DIR"
cp "$OUT" "$BIN_DIR/$TAURI_NAME"
chmod +x "$BIN_DIR/$TAURI_NAME"
echo "==> Installed Tauri externalBin: $BIN_DIR/$TAURI_NAME"

echo "==> Smoke test"
"$ROOT/desktop/scripts/verify-sidecar-binary.sh"

echo ""
echo "Phase 2 complete. Binary ready for Tauri externalBin."