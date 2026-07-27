"""Wire format for desktop ↔ sidecar communication (newline-delimited JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

IPC_PROTOCOL_VERSION = "1.0"

# Timeline types accepted from cloud / desktop clients (core product surface).
ELEMENT_TYPES = frozenset({
    "MathTex", "Text", "ThreeDGraph", "Surface", "Solid3D", "Axes",
    "NumberPlane", "ParametricFunction", "VGroup", "Dot", "Arrow",
    "Image", "SVG", "DataPath", "DataPlot", "Diagram",
})

ACTION_TYPES = frozenset({
    "CameraMove", "TransformElement", "SolidLift", "SolidRotate",
    "CameraInspect", "CameraFocus", "StateTransition", "ElementMorph",
})

# Dev / legacy types still parseable but flagged in strict validation.
LEGACY_TYPES = frozenset({
    "GridBoard", "GridMark", "QuadraticPlot", "QuadraticPlotPair", "PlotTrace",
})

KNOWN_TIMELINE_TYPES = ELEMENT_TYPES | ACTION_TYPES | LEGACY_TYPES


@dataclass(frozen=True)
class Request:
    id: str
    command: str
    params: dict[str, Any]


@dataclass(frozen=True)
class Response:
    id: str
    ok: bool
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


def parse_line(line: str) -> Request:
    """Parse one NDJSON request line."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ProtocolError("INVALID_JSON", str(exc)) from exc

    if data.get("type") != "request":
        raise ProtocolError("INVALID_ENVELOPE", "Expected type=request")

    req_id = data.get("id")
    command = data.get("command")
    if not req_id or not isinstance(req_id, str):
        raise ProtocolError("INVALID_REQUEST", "Missing or invalid id")
    if not command or not isinstance(command, str):
        raise ProtocolError("INVALID_REQUEST", "Missing or invalid command")

    params = data.get("params") or {}
    if not isinstance(params, dict):
        raise ProtocolError("INVALID_REQUEST", "params must be an object")

    return Request(id=req_id, command=command, params=params)


def encode_response(response: Response) -> str:
    payload: dict[str, Any] = {
        "type": "response",
        "id": response.id,
        "ok": response.ok,
    }
    if response.ok:
        payload["result"] = response.result or {}
    else:
        payload["error"] = response.error or {"code": "UNKNOWN", "message": "Unknown error"}
    return json.dumps(payload, ensure_ascii=False)


def encode_event(event: str, data: dict[str, Any] | None = None) -> str:
    return json.dumps(
        {"type": "event", "event": event, "data": data or {}},
        ensure_ascii=False,
    )


class ProtocolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
