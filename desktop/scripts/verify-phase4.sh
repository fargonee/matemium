#!/usr/bin/env bash
# Phase 4 gate — Rust shell modules, sidecar IPC bridge, project CRUD.
# See: COMPLETE_LINUX_UBUNTU_APP_TODO.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TAURI_DIR="$ROOT/desktop/src-tauri"
TRIPLE="x86_64-unknown-linux-gnu"
SIDECAR="$TAURI_DIR/binaries/matemium-sidecar-${TRIPLE}"
FAIL=0

ok() { echo "  OK  $1"; }
fail() { echo "  FAIL $1"; FAIL=1; }

echo "==> Phase 4 verification (Rust shell)"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi

echo "--- 4.1 Module layout ---"
for f in protocol.rs workspace.rs projects.rs sidecar.rs cloud.rs commands.rs state.rs; do
  if [[ -f "$TAURI_DIR/src/$f" ]]; then ok "src/$f"; else fail "missing src/$f"; fi
done

python3 - <<'PY' "$TAURI_DIR/src/lib.rs" || fail "invoke handler registration"
import pathlib, sys
text = pathlib.Path(sys.argv[1]).read_text()
for cmd in (
    "project_list", "project_create", "project_open", "project_save", "project_delete",
    "sidecar_ping", "sidecar_lint", "sidecar_check", "sidecar_list_scenes", "sidecar_render",
    "cloud_chat",
):
    assert f"commands::{cmd}" in text, cmd
print("  OK  Tauri commands registered")
PY

echo "--- 4.2 cargo test (unit) ---"
cd "$TAURI_DIR"
if cargo test --lib 2>&1; then
  ok "cargo test --lib"
else
  fail "cargo test --lib"
fi

echo "--- 4.3 sidecar ping integration ---"
if [[ -x "$SIDECAR" ]]; then
  export MATEMIUM_SIDECAR_BIN="$SIDECAR"
  if cargo test --test sidecar_integration ping_real_sidecar_binary 2>&1; then
    ok "sidecar ping via binary"
  else
    fail "sidecar ping integration"
  fi
else
  fail "missing sidecar binary at $SIDECAR"
fi

echo "--- 4.4 cargo build ---"
if cargo build 2>&1; then
  ok "cargo build"
else
  fail "cargo build"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "Phase 4 verification passed."
  echo "Manual dev check: cd desktop/src-tauri && cargo tauri dev"
  echo "  invoke('sidecar_ping') from the WebView console once Phase 5 UI exists."
  exit 0
fi
echo "Phase 4 verification failed."
exit 1