"""Structured progress events emitted on the sidecar stdout stream."""

from __future__ import annotations

import sys
from typing import Any, TextIO

from .protocol import encode_event


class EventEmitter:
    """Writes NDJSON event lines alongside JSON response lines."""

    def __init__(self, stream: TextIO | None = None):
        self._stream = stream or sys.stdout

    def emit(self, event: str, **data: Any) -> None:
        line = encode_event(event, data)
        self._stream.write(line + "\n")
        self._stream.flush()

    def compile_started(self, *, element_count: int) -> None:
        self.emit("compile_started", element_count=element_count)

    def layout_done(
        self,
        *,
        duration_estimate: float,
        animation_count: int | None = None,
    ) -> None:
        data: dict[str, Any] = {"duration_estimate": duration_estimate}
        if animation_count is not None:
            data["animation_count"] = animation_count
        self.emit("layout_done", **data)

    def render_started(
        self,
        *,
        quality: str,
        animation_count: int | None = None,
    ) -> None:
        data: dict[str, Any] = {"quality": quality}
        if animation_count is not None:
            data["animation_count"] = animation_count
        self.emit("render_started", **data)

    def render_progress(
        self,
        *,
        pct: float,
        message: str = "",
        section: str | None = None,
        frame: int | None = None,
        total_frames: int | None = None,
        partial_index: int | None = None,
        partial_total: int | None = None,
        partial_cached: bool | None = None,
    ) -> None:
        data: dict[str, Any] = {"pct": pct, "message": message}
        if section is not None:
            data["section"] = section
        if frame is not None:
            data["frame"] = frame
        if total_frames is not None:
            data["total_frames"] = total_frames
        if partial_index is not None:
            data["partial_index"] = partial_index
        if partial_total is not None:
            data["partial_total"] = partial_total
        if partial_cached is not None:
            data["partial_cached"] = partial_cached
        self.emit("render_progress", **data)

    def render_complete(self, *, video: str) -> None:
        self.emit("render_complete", video=video)

    def lint_started(self, *, workspace: str) -> None:
        self.emit("lint_started", workspace=workspace)

    def lint_complete(self, *, count: int) -> None:
        self.emit("lint_complete", count=count)

    def check_complete(self, *, ok: bool, scene: str) -> None:
        self.emit("check_complete", ok=ok, scene=scene)

    def error(self, *, code: str, message: str) -> None:
        self.emit("error", code=code, message=message)