from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TapeEvent:
    id: str
    type: str
    target: str | int | None
    animation: str
    start_state: str | None = None
    end_state: str | None = None
    run_time: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

