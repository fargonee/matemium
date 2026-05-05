from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from manim import Mobject


@dataclass(slots=True)
class TapeRow:
    id: str
    mobject: Mobject
    row_type: str
    y_position: float
    height: float
    top_y: float
    center_y: float
    bottom_y: float
    anchor_name: str | None = None
    visible: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

