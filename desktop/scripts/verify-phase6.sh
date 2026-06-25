#!/usr/bin/env bash
# Phase 6 gate — server auth + chat integration.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TAURI_DIR="$ROOT/desktop/src-tauri"
SERVER_VENV="$ROOT/server/.venv"
FAIL=0
SERVER_PID=""

ok() { echo "  OK  $1"; }
fail() { echo "  FAIL $1"; FAIL=1; }

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "==> Phase 6 verification (server integration)"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi

echo "--- 6.1 auth_login registered ---"
python3 - <<'PY' "$TAURI_DIR/src/lib.rs" || fail "auth_login handler"
import pathlib, sys
text = pathlib.Path(sys.argv[1]).read_text()
assert "commands::auth_login" in text
print("  OK  auth_login in lib.rs")
PY

echo "--- 6.2 Start server stub ---"
if ! curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
  "$SERVER_VENV/bin/python" -m matemium_server &
  SERVER_PID=$!
  for _ in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi

if curl -sf http://127.0.0.1:8080/health | grep -q '"status":"ok"'; then
  ok "server health"
else
  fail "server health"
fi

echo "--- 6.3 curl auth + chat ---"
TOKEN=$(curl -sf -X POST http://127.0.0.1:8080/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@matemium.app","password":"test"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
if [[ "$TOKEN" == dev.* ]]; then ok "auth token ($TOKEN)"; else fail "auth token"; fi

CHAT=$(curl -sf -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"add heading"}]}')
if echo "$CHAT" | grep -q '"code_edit"'; then ok "chat code_edit"; else fail "chat code_edit"; fi

echo "--- 6.4 Rust auth integration test ---"
cd "$TAURI_DIR"
export MATEMIUM_SERVER_URL="http://127.0.0.1:8080"
if cargo test --test auth_integration auth_and_chat_against_stub_server 2>&1; then
  ok "cargo test auth_integration"
else
  fail "cargo test auth_integration"
fi

echo "--- 6.5 auth_login command path + Bearer evidence ---"
SCRATCH="${SCRATCH:-/tmp/grok-goal-b1e6f39e5e19/implementer}"
if "$ROOT/desktop/scripts/exercise-auth-chat.sh" "$SCRATCH/auth-chat.log"; then
  ok "auth_login command path + Bearer header"
else
  fail "auth_login command path"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "Phase 6 verification passed."
  exit 0
fi
echo "Phase 6 verification failed."
exit 1