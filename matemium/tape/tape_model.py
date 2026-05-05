from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from manim import Mobject

from .tape_event import TapeEvent
from .tape_row import TapeRow
from .tape_state import TapeState


class TapeModel:
    def __init__(self) -> None:
        self.rows: list[TapeRow] = []
        self.anchors: dict[str, str] = {}
        self.states: dict[str, TapeState] = {}
        self.events: list[TapeEvent] = []
        self.metadata: dict[str, object] = {}

    def register_row(self, row: TapeRow) -> None:
        self.rows.append(row)

    def add_anchor(self, name: str, row_id: str) -> None:
        self.anchors[name] = row_id

    def get_row(self, row_id: str) -> TapeRow:
        for row in self.rows:
            if row.id == row_id:
                return row
        raise KeyError(f"Unknown row id: {row_id}")

    def latest_row(self) -> TapeRow:
        if not self.rows:
            raise ValueError("No rows have been registered yet.")
        return self.rows[-1]

    def resolve_row(self, target: str | TapeRow | Mobject | None) -> TapeRow:
        if target is None or target == "latest":
            return self.latest_row()
        if isinstance(target, TapeRow):
            return target
        if isinstance(target, str):
            if target in self.anchors:
                return self.get_row(self.anchors[target])
            return self.get_row(target)
        if isinstance(target, Mobject):
            for row in self.rows:
                if row.mobject is target:
                    return row
        raise KeyError(f"Unable to resolve target: {target!r}")

    def add_event(self, event: TapeEvent) -> None:
        self.events.append(event)

    def capture_state(
        self,
        name: str,
        *,
        visible_rows: Iterable[str],
        hidden_rows: Iterable[str],
        highlighted_targets: Iterable[str],
        scroll_offset: float,
        active_row_index: int,
        scale: float,
        viewport_center_y: float,
        row_opacities: dict[str, float] | None = None,
        highlight_specs: Iterable[dict[str, object]] | None = None,
        event_index: int = 0,
        metadata: dict[str, object] | None = None,
    ) -> TapeState:
        state = TapeState(
            name=name,
            visible_rows=list(visible_rows),
            hidden_rows=list(hidden_rows),
            highlighted_targets=list(highlighted_targets),
            scroll_offset=scroll_offset,
            active_row_index=active_row_index,
            scale=scale,
            viewport_center_y=viewport_center_y,
            row_opacities=dict(row_opacities or {}),
            highlight_specs=[dict(spec) for spec in (highlight_specs or [])],
            event_index=event_index,
            metadata=dict(metadata or {}),
        )
        self.states[name] = state
        return state

    def copy_state(self, name: str) -> TapeState:
        state = self.states[name]
        return TapeState(**asdict(state))
