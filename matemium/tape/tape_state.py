from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TapeState:
    name: str
    visible_rows: list[str]
    hidden_rows: list[str]
    highlighted_targets: list[str]
    scroll_offset: float
    active_row_index: int
    scale: float
    viewport_center_y: float
    row_opacities: dict[str, float] = field(default_factory=dict)
    highlight_specs: list[dict[str, Any]] = field(default_factory=list)
    event_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
