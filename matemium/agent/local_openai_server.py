"""OpenAI-compatible local model server for Aider.

The desktop app owns local GGUF model assets. Aider expects an HTTP provider,
so this module exposes the selected GGUF through a small OpenAI-compatible
chat-completions endpoint and delegates native inference to the existing
crash-isolated llama.cpp worker.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import time
from typing import Any

from .local_runner import LocalInferenceRunner


SERVER_MODEL = "matemium-local"


class LocalOpenAIHandler(BaseHTTPRequestHandler):
    server_version = "MatemiumLocalOpenAI/1.0"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler naming
        if self.path.rstrip("/") == "/v1/models":
            self._write_json({
                "object": "list",
                "data": [{"id": SERVER_MODEL, "object": "model", "owned_by": "matemium"}],
            })
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler naming
        if self.path.rstrip("/") != "/v1/chat/completions":
            self.send_error(404, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length") or "0")
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            messages = payload.get("messages") or []
            if not isinstance(messages, list):
                raise ValueError("messages must be a list")

            runner = LocalInferenceRunner()
            if not runner.model_path or not runner.model_path.is_file():
                raise FileNotFoundError(
                    "No verified local GGUF model is configured for the Matemium provider."
                )

            from .llm_worker import generate_in_worker

            content = generate_in_worker(
                model_path=runner.model_path,
                context_window=runner.context_window,
                messages=[
                    {"role": str(message.get("role", "user")), "content": str(message.get("content", ""))}
                    for message in messages
                    if isinstance(message, dict)
                ],
            )

            if payload.get("stream"):
                self._write_stream(content)
            else:
                self._write_json(self._completion_response(content))
        except Exception as exc:
            self._write_json(
                {
                    "error": {
                        "message": f"{type(exc).__name__}: {exc}",
                        "type": "matemium_local_provider_error",
                    }
                },
                status=500,
            )

    def _completion_response(self, content: str) -> dict[str, Any]:
        now = int(time.time())
        return {
            "id": f"chatcmpl-matemium-{now}",
            "object": "chat.completion",
            "created": now,
            "model": SERVER_MODEL,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    def _write_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_stream(self, content: str) -> None:
        now = int(time.time())
        chunks = [
            {
                "id": f"chatcmpl-matemium-{now}",
                "object": "chat.completion.chunk",
                "created": now,
                "model": SERVER_MODEL,
                "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
            },
            {
                "id": f"chatcmpl-matemium-{now}",
                "object": "chat.completion.chunk",
                "created": now,
                "model": SERVER_MODEL,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            },
        ]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for chunk in chunks:
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), LocalOpenAIHandler)
    server.serve_forever()
    return 0
