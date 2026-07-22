"""Versioned, redacted SSE event contract shared by legacy migration routes."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = 1
MAX_STRING = 2048
MAX_EVENT_BYTES = 16 * 1024
SENSITIVE = ("api_key", "apikey", "authorization", "password", "secret", "access_token", "refresh_token")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if any(token in str(key).lower() for token in SENSITIVE) else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value[:50]]
    if isinstance(value, str) and len(value.encode("utf-8")) > MAX_STRING:
        encoded = value.encode("utf-8")[:MAX_STRING]
        return encoded.decode("utf-8", errors="ignore") + "…[truncated]"
    return value


class AgentEventEmitter:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or str(uuid.uuid4())
        self.sequence = 0

    def event(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.sequence += 1
        sanitized = _sanitize(payload or {})
        if len(json.dumps(sanitized, ensure_ascii=False).encode("utf-8")) > MAX_EVENT_BYTES:
            sanitized = {
                "truncated": True,
                "summary": "Event exceeded the 16 KiB streaming limit; reload bounded evidence by ID.",
            }
        return {
            "event_id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "sequence": self.sequence,
            "schema_version": SCHEMA_VERSION,
            "event_type": event_type,
            "payload": sanitized,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def legacy_callback_event(self, legacy: dict[str, Any]) -> dict[str, Any]:
        kind = legacy.get("type")
        if kind == "thought":
            return self.event(
                "progress_updated",
                {"summary": "The agent evaluated the latest observation and selected its next action."},
            )
        mapping = {
            "tool_call": "action_started",
            "tool_output": "action_completed",
            "status": "progress_updated",
            "error": "run_failed",
        }
        payload = {key: value for key, value in legacy.items() if key != "type"}
        return self.event(mapping.get(str(kind), "progress_updated"), payload)
