"""NDJSON request loop for the PyInstaller sidecar process."""

from __future__ import annotations

import sys
import traceback
from typing import TextIO, Any, Callable

from .events import EventEmitter
from .protocol import ProtocolError, Request, Response, encode_response, parse_line

# Lazy import of dispatch so that even importing the server module does not
# execute handlers.py top level (though we made it light).
_dispatch: Callable[[str, dict[str, Any], EventEmitter], dict[str, Any]] | None = None


def _get_dispatch():
    global _dispatch
    if _dispatch is None:
        from .handlers import dispatch as _d
        _dispatch = _d
    return _dispatch


def run_server(
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Read newline-delimited JSON requests until EOF or shutdown command."""
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout
    events = EventEmitter(stream=output_stream)

    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue

        response = _handle_line(line, events)
        output_stream.write(encode_response(response) + "\n")
        output_stream.flush()

        if response.ok and response.result and response.result.get("shutdown"):
            return 0

    return 0


def _handle_line(line: str, events: EventEmitter) -> Response:
    req_id = "unknown"
    try:
        request = parse_line(line)
        req_id = request.id

        if request.command == "shutdown":
            return Response(id=req_id, ok=True, result={"shutdown": True})

        result = _get_dispatch()(request.command, request.params, events)
        return Response(id=req_id, ok=True, result=result)

    except ProtocolError as exc:
        events.error(code=exc.code, message=exc.message)
        return Response(
            id=req_id,
            ok=False,
            error={"code": exc.code, "message": exc.message},
        )
    except Exception as exc:
        tb = traceback.format_exc()
        events.error(code="INTERNAL_ERROR", message=str(exc))
        return Response(
            id=req_id,
            ok=False,
            error={"code": "INTERNAL_ERROR", "message": str(exc), "traceback": tb},
        )


def handle_request(request: Request, events: EventEmitter | None = None) -> Response:
    """Programmatic single-request handler (used in tests)."""
    import io

    emitter = events or EventEmitter(stream=io.StringIO())
    try:
        if request.command == "shutdown":
            return Response(id=request.id, ok=True, result={"shutdown": True})
        result = _get_dispatch()(request.command, request.params, emitter)
        return Response(id=request.id, ok=True, result=result)
    except ProtocolError as exc:
        return Response(
            id=request.id,
            ok=False,
            error={"code": exc.code, "message": exc.message},
        )