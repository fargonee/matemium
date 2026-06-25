"""Guardrail 4 — .matemium_debug.json emission on terminal critic failure."""

from __future__ import annotations

import json
import traceback
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Phase, ProjectSession

DEBUG_FILENAME = ".matemium_debug.json"


def _serialize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _serialize(v) for k, v in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    if isinstance(value, Phase):
        return value.value
    return value


def build_debug_payload(
    session: ProjectSession,
    *,
    error: str,
    error_trace: str,
    retry_count: int,
    script_excerpt: str,
) -> dict[str, Any]:
    blueprint_snapshot = _serialize(session.blueprint) if session.blueprint else None
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": session.current_phase.value,
        "halted": True,
        "retry_count": retry_count,
        "max_retries": 3,
        "error": error,
        "error_trace": error_trace,
        "script_excerpt": script_excerpt,
        "blueprint_snapshot": blueprint_snapshot,
        "project_dir": str(session.project_dir),
        "model_tier": session.model_tier.value,
        "token_ledger": _serialize(session.token_ledger),
        "transitions": _serialize(session.transitions),
    }


def write_debug_log(session: ProjectSession, payload: dict[str, Any]) -> Path:
    """Write .matemium_debug.json into the project workspace directory."""
    session.project_dir.mkdir(parents=True, exist_ok=True)
    path = session.project_dir / DEBUG_FILENAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def format_exception_trace(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))