#!/usr/bin/env bash
# Phase 3 gate — Tauri v2 scaffold compiles and bundles sidecar externalBin.
# See: COMPLETE_LINUX_UBUNTU_APP_TODO.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TAURI_DIR="$ROOT/desktop/src-tauri"
TRIPLE="x86_64-unknown-linux-gnu"
FAIL=0

ok() { echo "  OK  $1"; }
fail() { echo "  FAIL $1"; FAIL=1; }

echo "==> Phase 3 verification (Tauri v2 scaffold)"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi

echo "--- 3.1 Tauri project files ---"
for f in Cargo.toml tauri.conf.json src/main.rs src/lib.rs; do
  if [[ -f "$TAURI_DIR/$f" ]]; then ok "$f"; else fail "missing $f"; fi
done

if command -v cargo >/dev/null 2>&1; then ok "cargo"; else fail "cargo not in PATH"; fi
if cargo tauri --version >/dev/null 2>&1; then ok "cargo tauri $(cargo tauri --version 2>&1)"; else fail "cargo tauri CLI"; fi

echo "--- 3.2 tauri.conf.json (Linux + sidecar) ---"
python3 - <<'PY' "$TAURI_DIR/tauri.conf.json" || fail "tauri.conf.json parse"
import json, sys
cfg = json.load(open(sys.argv[1]))
assert cfg.get("identifier") == "app.matemium.canvas", cfg.get("identifier")
assert cfg.get("productName") == "Matemium", cfg.get("productName")
bundle = cfg.get("bundle", {})
assert "binaries/matemium-sidecar" in bundle.get("externalBin", []), bundle.get("externalBin")
targets = bundle.get("targets", [])
assert "deb" in targets and "appimage" in targets, targets
deps = bundle.get("linux", {}).get("deb", {}).get("depends", [])
for pkg in ("ffmpeg", "texlive-latex-extra", "dvipng", "dvisvgm"):
    assert pkg in deps, deps
print("  OK  identifier, bundle.externalBin, deb depends")
PY

SIDECAR="$TAURI_DIR/binaries/matemium-sidecar-${TRIPLE}"
if [[ -x "$SIDECAR" ]]; then ok "sidecar binary ($TRIPLE)"; else fail "missing $SIDECAR"; fi

echo "--- 3.3 cargo tauri build ---"
if [[ ! -f "$ROOT/desktop/app/dist/index.html" ]]; then
  fail "missing desktop/app/dist/index.html (placeholder frontend)"
fi

cd "$TAURI_DIR"
if cargo tauri build 2>&1; then
  ok "cargo tauri build"
  for pattern in "target/release/bundle/deb/"*.deb "target/release/bundle/appimage/"*.AppImage; do
    if compgen -G "$pattern" >/dev/null; then ok "artifact: $(basename "$pattern")"; fi
  done
else
  fail "cargo tauri build"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "Phase 3 verification passed."
  exit 0
fi
echo "Phase 3 verification failed."
exit 1