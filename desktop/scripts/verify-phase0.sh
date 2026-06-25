#!/usr/bin/env bash
# Phase 0 verification — checks Ubuntu dev prerequisites for Matemium desktop.
# Exit 0 if all required checks pass; non-zero otherwise.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FAIL=0
WARN=0

ok()   { echo "  OK   $*"; }
fail() { echo "  FAIL $*"; FAIL=1; }
warn() { echo "  WARN $*"; WARN=1; }

check_cmd() {
  local label="$1"
  shift
  if command -v "$1" >/dev/null 2>&1; then
    ok "$label ($("$1" "${@:2}" 2>/dev/null | head -1 || true))"
  else
    fail "$label — command not found: $1"
  fi
}

echo "==> Phase 0 verification (repo: $ROOT)"
echo ""

echo "--- 0.1 System packages (build + Manim + Tauri GTK) ---"
for pkg in ffmpeg pdflatex pkg-config; do
  check_cmd "$pkg" "$pkg" -version 2>/dev/null || check_cmd "$pkg" "$pkg" --version
done

gtk_runtime_ok=false
for lib in libwebkit2gtk-4.1-0 libgtk-3-0 libgtk-3-0t64; do
  if dpkg -s "$lib" >/dev/null 2>&1; then
    ok "$lib installed"
    [[ "$lib" == libgtk-3-* ]] && gtk_runtime_ok=true
  fi
done
if [[ "$gtk_runtime_ok" == false ]]; then
  warn "libgtk-3 runtime not found (needed for Tauri — run setup-ubuntu-dev.sh)"
fi

for devpkg in libwebkit2gtk-4.1-dev libgtk-3-dev build-essential; do
  if dpkg -s "$devpkg" >/dev/null 2>&1; then
    ok "$devpkg installed"
  else
    warn "$devpkg not installed (needed for Tauri build)"
  fi
done

echo ""
echo "--- 0.2 Rust (required before Phase 3) ---"
if command -v rustc >/dev/null 2>&1; then
  ok "rustc $(rustc --version)"
else
  warn "rustc not installed — run setup-ubuntu-dev.sh --with-rust"
fi

if command -v cargo >/dev/null 2>&1; then
  if cargo tauri --version >/dev/null 2>&1; then
    ok "tauri $(cargo tauri --version 2>&1 | head -1)"
  else
    warn "cargo tauri not installed — cargo install tauri-cli --version '^2.0.0' --locked"
  fi
else
  warn "cargo not installed"
fi

echo ""
echo "--- 0.3 Node.js 20+ (required before Phase 5 UI) ---"
if command -v node >/dev/null 2>&1; then
  major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
  if [[ "$major" -ge 20 ]]; then
    ok "node $(node --version)"
  else
    warn "node $(node --version) — need v20+ (setup-ubuntu-dev.sh --with-node)"
  fi
else
  warn "node not installed — run setup-ubuntu-dev.sh --with-node"
fi

echo ""
echo "--- 0.5 Engine venv ---"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  ok "engine venv $("$ROOT/.venv/bin/python" --version 2>&1)"
  if "$ROOT/.venv/bin/pip" show matemium >/dev/null 2>&1; then
    ok "matemium $($ROOT/.venv/bin/matemium --version 2>/dev/null)"
  else
    fail "matemium not installed in .venv — pip install -e '.[dev]'"
  fi
  if "$ROOT/.venv/bin/python" -c "import manim" 2>/dev/null; then
    ok "manim importable"
  else
    fail "manim not importable in engine venv"
  fi
else
  fail "missing $ROOT/.venv — run setup-ubuntu-dev.sh"
fi

echo ""
echo "--- 0.5 Engine tests ---"
if [[ -x "$ROOT/.venv/bin/pytest" ]]; then
  if "$ROOT/.venv/bin/python" -m pytest "$ROOT/tests/" -q --tb=no 2>/dev/null; then
    ok "pytest tests/ passed"
  else
    fail "pytest tests/ failed"
  fi
else
  fail "pytest not in engine venv"
fi

echo ""
echo "--- 0.5 Sidecar IPC smoke ---"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  resp="$(
    echo '{"type":"request","id":"1","command":"ping","params":{}}' \
      | "$ROOT/.venv/bin/python" -m matemium.sidecar 2>/dev/null \
      | tail -1
  )"
  if echo "$resp" | grep -q '"ok": true'; then
    ok "sidecar ping"
  else
    fail "sidecar ping failed: $resp"
  fi
fi

echo ""
echo "--- 0.6 Server venv ---"
if [[ -x "$ROOT/server/.venv/bin/python" ]]; then
  ok "server venv"
  if "$ROOT/server/.venv/bin/pip" show matemium-server >/dev/null 2>&1; then
    ok "matemium-server installed"
  else
    fail "matemium-server not installed — cd server && pip install -e '.[dev]'"
  fi
  if "$ROOT/server/.venv/bin/python" -m pytest "$ROOT/server/tests/" -q --tb=no 2>/dev/null; then
    ok "server tests passed"
  else
    fail "server tests failed"
  fi
else
  warn "missing server/.venv — run setup-ubuntu-dev.sh"
fi

echo ""
echo "--- Phase 2 sidecar binary (optional until built) ---"
if [[ -x "$ROOT/dist/matemium-sidecar" ]]; then
  if "$ROOT/desktop/scripts/verify-sidecar-binary.sh" >/dev/null 2>&1; then
    ok "frozen sidecar binary (dist/matemium-sidecar)"
  else
    warn "sidecar binary present but verify-sidecar-binary.sh failed — rebuild"
  fi
else
  warn "dist/matemium-sidecar not built — run ./desktop/scripts/build-sidecar.sh (Phase 2)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  if [[ "$WARN" -eq 0 ]]; then
    echo "Phase 0: ALL CHECKS PASSED (including optional Tauri/Node if installed)."
  else
    echo "Phase 0: REQUIRED CHECKS PASSED (warnings above — install before Phases 3–5)."
  fi
  exit 0
else
  echo "Phase 0: FAILED — fix FAIL items above, then re-run."
  exit 1
fi