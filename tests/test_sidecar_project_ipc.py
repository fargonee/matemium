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


def test_upload_reference_text(demo_workspace: Path):
    stdout = StringIO()
    events = EventEmitter(stream=stdout)
    
    result = dispatch(
        "upload_reference",
        {
            "workspace": str(demo_workspace),
            "file_name": "syllabus.txt",
            "file_content_text": "Trigonometric identities: sin^2 + cos^2 = 1."
        },
        events
    )
    assert result["status"] == "success"
    assert result["file_name"] == "syllabus.txt"
    assert (demo_workspace / "references" / "syllabus.txt").is_file()
    assert (demo_workspace / "references" / "syllabus.txt").read_text(encoding="utf-8") == "Trigonometric identities: sin^2 + cos^2 = 1."


def test_upload_reference_base64(demo_workspace: Path):
    import base64
    stdout = StringIO()
    events = EventEmitter(stream=stdout)
    
    encoded = base64.b64encode(b"Euler formula: e^(ix) = cos(x) + i*sin(x)").decode("utf-8")
    result = dispatch(
        "upload_reference",
        {
            "workspace": str(demo_workspace),
            "file_name": "euler.txt",
            "file_content_base64": encoded
        },
        events
    )
    assert result["status"] == "success"
    assert (demo_workspace / "references" / "euler.txt").is_file()
    assert (demo_workspace / "references" / "euler.txt").read_text(encoding="utf-8") == "Euler formula: e^(ix) = cos(x) + i*sin(x)"


def test_retrieve_autoscans_references(demo_workspace: Path):
    # Upload first
    dispatch(
        "upload_reference",
        {
            "workspace": str(demo_workspace),
            "file_name": "notes.md",
            "file_content_text": "# Trigonometry\nLet us prove the sine rule of triangles."
        },
        EventEmitter(stream=StringIO())
    )
    
    # Query RAG retrieve
    resp = dispatch(
        "retrieve",
        {
            "workspace": str(demo_workspace),
            "query": "sine rule",
            "top_k": 3
        },
        EventEmitter(stream=StringIO())
    )
    
    # Verify we successfully auto-scanned references/ folder and found matches!
    assert "results" in resp
    results = resp["results"]
    assert len(results) > 0
    assert any("sine rule" in r["chunk"].lower() for r in results)


def test_list_and_delete_references(demo_workspace: Path):
    # Upload some references first
    dispatch(
        "upload_reference",
        {
            "workspace": str(demo_workspace),
            "file_name": "ref1.txt",
            "file_content_text": "First reference content."
        },
        EventEmitter(stream=StringIO())
    )
    dispatch(
        "upload_reference",
        {
            "workspace": str(demo_workspace),
            "file_name": "ref2.txt",
            "file_content_text": "Second reference content."
        },
        EventEmitter(stream=StringIO())
    )
    
    # List references
    list_res = dispatch(
        "list_references",
        {"workspace": str(demo_workspace)},
        EventEmitter(stream=StringIO())
    )
    assert list_res["status"] == "success"
    assert "ref1.txt" in list_res["references"]
    assert "ref2.txt" in list_res["references"]
    
    # Delete one
    delete_res = dispatch(
        "delete_reference",
        {"workspace": str(demo_workspace), "file_name": "ref1.txt"},
        EventEmitter(stream=StringIO())
    )
    assert delete_res["status"] == "success"
    assert delete_res["deleted"] is True
    
    # List again and verify it is gone
    list_res2 = dispatch(
        "list_references",
        {"workspace": str(demo_workspace)},
        EventEmitter(stream=StringIO())
    )
    assert "ref1.txt" not in list_res2["references"]
    assert "ref2.txt" in list_res2["references"]
    
    # Get content of the remaining reference
    content_res = dispatch(
        "get_reference_content",
        {"workspace": str(demo_workspace), "file_name": "ref2.txt"},
        EventEmitter(stream=StringIO())
    )
    assert content_res["status"] == "success"
    assert content_res["content"] == "Second reference content."