#!/usr/bin/env bash
# Exercise auth_login command path + capture Authorization: Bearer evidence.
# Usage: ./desktop/scripts/exercise-auth-chat.sh [output.log]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TAURI_DIR="$ROOT/desktop/src-tauri"
SERVER_VENV="$ROOT/server/.venv"
OUT="${1:-/tmp/grok-goal-b1e6f39e5e19/implementer/auth-chat.log}"
ECHO_PORT=18081
SERVER_PID=""
ECHO_PID=""

mkdir -p "$(dirname "$OUT")"
exec > >(tee "$OUT") 2>&1

cleanup() {
  [[ -n "$ECHO_PID" ]] && kill "$ECHO_PID" 2>/dev/null || true
  [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true
  wait "$ECHO_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi

echo "==> auth-chat exercise ($(date -Iseconds))"

echo "--- 1. Header echo stub on :$ECHO_PORT ---"
python3 -u - <<'PY' &
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        auth = self.headers.get("Authorization", "MISSING")
        print(f"RECEIVED_AUTH={auth}", flush=True)
        if self.path == "/v1/auth/token":
            body = json.dumps(
                {
                    "access_token": "dev.echo.token",
                    "token_type": "bearer",
                    "expires_in": 3600,
                }
            )
        elif self.path == "/v1/chat/completions":
            body = json.dumps(
                {
                    "id": "echo-1",
                    "message": {"role": "assistant", "content": "ok"},
                    "code_edit": {"description": "x", "full_file": "pass"},
                    "model": "stub",
                    "stub": True,
                }
            )
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

HTTPServer(("127.0.0.1", 18081), Handler).serve_forever()
PY
ECHO_PID=$!
for _ in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:$ECHO_PORT/health" >/dev/null 2>&1; then
    echo "  OK  echo stub healthy"
    break
  fi
  sleep 0.2
done

echo "--- 2. auth_login_inner against echo stub (command path) ---"
cd "$TAURI_DIR"
export MATEMIUM_SERVER_URL="http://127.0.0.1:$ECHO_PORT"
cargo test --test auth_login_command auth_login_command_path_returns_access_token -- --nocapture

echo "--- 3. cloud::chat sends Authorization: Bearer (echo stub logs RECEIVED_AUTH) ---"
cargo test --test auth_login_command auth_login_then_chat_sends_bearer_header -- --nocapture
grep -q "RECEIVED_AUTH=Bearer dev.echo.token" "$OUT"
echo "  OK  RECEIVED_AUTH=Bearer dev.echo.token captured from desktop Rust chat path"

echo "--- 4. Real matemium_server stub ---"
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
curl -sf http://127.0.0.1:8080/health
echo "  OK  matemium_server health"

echo "--- 5. curl -v auth + chat with Bearer (outgoing header in transcript) ---"
TOKEN=$(curl -sf -X POST http://127.0.0.1:8080/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@matemium.app","password":"test"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
echo "TOKEN=$TOKEN"

curl -sv -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"add heading"}]}' \
  -o /dev/null 2>&1 | grep -E '> Authorization: Bearer|HTTP/'

echo "--- 6. auth_login_inner on real server (invoke-equivalent path) ---"
export MATEMIUM_SERVER_URL="http://127.0.0.1:8080"
cargo test --test auth_login_command -- --nocapture

echo ""
echo "auth-chat exercise complete → $OUT"