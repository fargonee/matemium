"""PyInstaller sidecar binary smoke tests (skip if not built)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BINARY = REPO / "dist" / "matemium-sidecar"
DEMO_SCENES = REPO / "projects" / "demo" / "scenes.py"

pytestmark = pytest.mark.skipif(
    not BINARY.is_file(),
    reason="dist/matemium-sidecar not built — run ./desktop/scripts/build-sidecar.sh",
)


def _ipc(command: str, params: dict) -> dict:
    req = json.dumps({"type": "request", "id": "t", "command": command, "params": params})
    proc = subprocess.run(
        [str(BINARY)],
        input=req + "\n",
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln]
    assert lines, f"no stdout from sidecar: stderr={proc.stderr!r}"
    return json.loads(lines[-1])


def test_binary_version():
    proc = subprocess.run(
        [str(BINARY), "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "matemium-sidecar" in proc.stdout
    assert "protocol" in proc.stdout


def test_binary_ping():
    resp = _ipc("ping", {})
    assert resp["ok"] is True
    assert resp["result"]["engine"] == "matemium"


def test_binary_list_and_check_project(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    shutil.copy(DEMO_SCENES, ws / "scenes.py")
    listed = _ipc("list_scenes", {"workspace": str(ws)})
    assert resp_ok(listed)
    assert "PortraitDemo" in listed["result"]["scenes"]
    checked = _ipc("check_project", {"workspace": str(ws), "scene": "PortraitDemo"})
    assert resp_ok(checked)
    assert checked["result"]["ok"] is True


def resp_ok(payload: dict) -> bool:
    return payload.get("ok") is True


@pytest.mark.slow
def test_binary_render_project(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    ws = tmp_path / "ws"
    ws.mkdir()
    shutil.copy(DEMO_SCENES, ws / "scenes.py")
    out = tmp_path / "renders"
    resp = _ipc(
        "render_project",
        {
            "workspace": str(ws),
            "scene": "PortraitDemo",
            "quality": "preview",
            "output_dir": str(out),
        },
    )
    assert resp_ok(resp)
    video = Path(resp["result"]["video"])
    assert video.is_file()
    assert video.suffix == ".mp4"