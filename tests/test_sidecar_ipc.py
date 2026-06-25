"""Sidecar IPC protocol and DSL validation tests (no Manim renders)."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from matemium.ipc.duration import estimate_timeline_duration
from matemium.ipc.events import EventEmitter
from matemium.ipc.handlers import dispatch
from matemium.ipc.protocol import (
    IPC_PROTOCOL_VERSION,
    encode_response,
    parse_line,
)
from matemium.ipc.server import handle_request, run_server
from matemium.ipc.validate import validate_dsl_payload

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
MINIMAL_DSL = json.loads((FIXTURES / "minimal_sheet.dsl.json").read_text(encoding="utf-8"))


def test_parse_and_encode_roundtrip():
    line = '{"type":"request","id":"abc","command":"ping","params":{}}'
    req = parse_line(line)
    assert req.id == "abc"
    assert req.command == "ping"

    from matemium.ipc.protocol import Response

    encoded = encode_response(Response(id="abc", ok=True, result={"ok": True}))
    payload = json.loads(encoded)
    assert payload["type"] == "response"
    assert payload["ok"] is True


def test_ping_handler():
    result = dispatch("ping", {}, EventEmitter(stream=StringIO()))
    assert result["version"]
    assert result["protocol"] == IPC_PROTOCOL_VERSION


def test_validate_minimal_fixture():
    result = validate_dsl_payload(MINIMAL_DSL)
    assert result.valid
    assert result.dsl is not None
    assert len(result.errors) == 0


def test_validate_rejects_unknown_type():
    bad = {
        "canvas_settings": {"orientation": "portrait"},
        "timeline": [{"id": "x", "type": "NotARealType"}],
    }
    result = validate_dsl_payload(bad)
    assert not result.valid
    assert any(e.code == "UNKNOWN_TYPE" for e in result.errors)


def test_validate_dsl_command():
    from matemium.ipc.protocol import Request

    resp = handle_request(
        Request(id="v1", command="validate_dsl", params={"dsl": MINIMAL_DSL})
    )
    assert resp.ok
    assert resp.result is not None
    assert resp.result["valid"] is True
    assert resp.result["timeline_length"] == 4


def test_estimate_duration():
    result = validate_dsl_payload(MINIMAL_DSL)
    assert result.dsl is not None
    duration = estimate_timeline_duration(result.dsl)
    assert duration > 0


def test_server_ping_over_stdio():
    stdin = StringIO(
        '{"type":"request","id":"1","command":"ping","params":{}}\n'
    )
    stdout = StringIO()
    code = run_server(stdin=stdin, stdout=stdout)
    assert code == 0
    lines = [json.loads(line) for line in stdout.getvalue().strip().splitlines()]
    assert lines[0]["ok"] is True
    assert lines[0]["result"]["protocol"] == IPC_PROTOCOL_VERSION


def test_unknown_command_returns_error():
    from matemium.ipc.protocol import Request

    resp = handle_request(Request(id="9", command="not_real", params={}))
    assert not resp.ok
    assert resp.error is not None
    assert resp.error["code"] == "UNKNOWN_COMMAND"


def test_workspace_resolution(tmp_path):
    from matemium.workspace import exports_dir_for_workspace, resolve_job_workspace

    ws = resolve_job_workspace({"output_dir": str(tmp_path / "job-1")})
    assert ws.is_dir()
    exports = exports_dir_for_workspace(ws)
    assert exports.is_dir()