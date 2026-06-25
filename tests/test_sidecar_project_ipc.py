"""Sidecar project IPC commands (no full renders by default)."""

from __future__ import annotations

import json
import shutil
from io import StringIO
from pathlib import Path

import pytest

from matemium.ipc.events import EventEmitter
from matemium.ipc.handlers import dispatch
from matemium.ipc.protocol import Request
from matemium.ipc.server import handle_request

REPO = Path(__file__).resolve().parent.parent
DEMO_SCENES = REPO / "projects" / "demo" / "scenes.py"


@pytest.fixture
def demo_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    shutil.copy(DEMO_SCENES, ws / "scenes.py")
    return ws


def test_dispatch_list_scenes(demo_workspace: Path):
    result = dispatch(
        "list_scenes",
        {"workspace": str(demo_workspace)},
        EventEmitter(stream=StringIO()),
    )
    assert "PortraitDemo" in result["scenes"]


def test_dispatch_lint_project(demo_workspace: Path):
    stdout = StringIO()
    events = EventEmitter(stream=stdout)
    result = dispatch(
        "lint_project",
        {"workspace": str(demo_workspace)},
        events,
    )
    assert result["ok"] is True
    assert result["diagnostics"] == []
    lines = [json.loads(ln) for ln in stdout.getvalue().strip().splitlines() if ln]
    assert any(e["event"] == "lint_complete" for e in lines)


def test_dispatch_check_project(demo_workspace: Path):
    resp = handle_request(
        Request(
            id="c1",
            command="check_project",
            params={"workspace": str(demo_workspace), "scene": "PortraitDemo"},
        )
    )
    assert resp.ok
    assert resp.result is not None
    assert resp.result["ok"] is True
    assert resp.result["scene"] == "PortraitDemo"


def test_check_project_via_stdio(demo_workspace: Path):
    stdin = StringIO(
        json.dumps(
            {
                "type": "request",
                "id": "1",
                "command": "check_project",
                "params": {
                    "workspace": str(demo_workspace),
                    "scene": "PortraitDemo",
                },
            }
        )
        + "\n"
    )
    stdout = StringIO()
    from matemium.ipc.server import run_server

    run_server(stdin=stdin, stdout=stdout)
    response = json.loads(stdout.getvalue().strip().splitlines()[-1])
    assert response["ok"] is True
    assert response["result"]["ok"] is True


def test_render_project_missing_workspace():
    resp = handle_request(
        Request(id="r0", command="render_project", params={})
    )
    assert not resp.ok
    assert resp.error["code"] == "MISSING_WORKSPACE"


@pytest.mark.slow
def test_render_project_produces_video(demo_workspace: Path, tmp_path: Path):
    out = tmp_path / "renders"
    result = dispatch(
        "render_project",
        {
            "workspace": str(demo_workspace),
            "scene": "PortraitDemo",
            "quality": "preview",
            "output_dir": str(out),
        },
        EventEmitter(stream=StringIO()),
    )
    preview = Path(result["video"])
    export = Path(result["export_video"])
    assert preview.is_file()
    assert preview.suffix == ".mp4"
    assert preview.parent == demo_workspace / "renders"
    assert export.is_file()
    assert export.parent == out