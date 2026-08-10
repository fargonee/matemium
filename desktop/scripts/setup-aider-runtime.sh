#!/usr/bin/env bash
# Create a dedicated uv-managed Aider runtime without changing Matemium's main Python.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
AIDER_VERSION="${MATEMIUM_AIDER_VERSION:-0.86.2}"
AIDER_PYTHON="${MATEMIUM_AIDER_PYTHON:-3.12}"
RUNTIME_DIR="${MATEMIUM_AIDER_RUNTIME_DIR:-$ROOT/.aider-runtime}"

if command -v uv >/dev/null 2>&1; then
  UV_BIN="$(command -v uv)"
elif [[ -x "$HOME/.local/bin/uv" ]]; then
  UV_BIN="$HOME/.local/bin/uv"
else
  echo "uv is required to provision the Aider runtime. Install uv first: https://docs.astral.sh/uv/"
  exit 1
fi

mkdir -p "$(dirname "$RUNTIME_DIR")"

echo "==> Creating Aider runtime at $RUNTIME_DIR with Python $AIDER_PYTHON"
"$UV_BIN" venv --python "$AIDER_PYTHON" "$RUNTIME_DIR"

if [[ -x "$RUNTIME_DIR/bin/python" ]]; then
  RUNTIME_PYTHON="$RUNTIME_DIR/bin/python"
  AIDER_BIN="$RUNTIME_DIR/bin/aider"
elif [[ -x "$RUNTIME_DIR/Scripts/python.exe" ]]; then
  RUNTIME_PYTHON="$RUNTIME_DIR/Scripts/python.exe"
  AIDER_BIN="$RUNTIME_DIR/Scripts/aider.exe"
else
  echo "FAIL: Python executable not found in Aider runtime: $RUNTIME_DIR"
  exit 1
fi

echo "==> Installing aider-chat==$AIDER_VERSION"
"$UV_BIN" pip install --python "$RUNTIME_PYTHON" "aider-chat==$AIDER_VERSION"

if [[ ! -x "$AIDER_BIN" ]]; then
  echo "FAIL: expected Aider executable not found at $AIDER_BIN"
  exit 1
fi

echo "==> Verifying Aider"
"$AIDER_BIN" --version

echo ""
echo "Aider runtime ready."
echo "Set MATEMIUM_AIDER_RUNTIME_DIR=$RUNTIME_DIR if launching the sidecar outside the desktop app."
