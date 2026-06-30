"""Renderer-agnostic measurement protocol.

The layout engine and builder use this to obtain sizes for Text/MathTex/etc.
Different backends can be plugged in:

- ManimMeasurementBackend (default, used for final video)
- KaTeXMeasurementBackend (used by desktop manim-web preview for pixel-perfect WYSIWYG)

This enables the "layout in Python, render faithfully in manim-web" model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..coords import Vector3


@dataclass
class MeasuredSize:
    width: float
    height: float
    # Optional baseline / ascender info for better vertical alignment
    baseline: float = 0.0
    ascent: float = 0.0
    descent: float = 0.0


class MeasurementBackend(Protocol):
    """Pluggable measurement strategy."""

    def measure_text(
        self,
        text: str,
        *,
        font_size: float = 36,
        wrap: bool = False,
        target_width: Optional[float] = None,
        **kwargs: Any,
    ) -> MeasuredSize: ...

    def measure_math(
        self,
        latex: str,
        *,
        scale: float = 0.9,
        target_width: Optional[float] = None,
        **kwargs: Any,
    ) -> MeasuredSize: ...

    def measure_element(self, elem: Any, **kwargs: Any) -> MeasuredSize:
        """Convenience for CanvasElement-like objects."""
        ...

    def measure_bounding_box(self, obj: Any, **kwargs: Any) -> BoundingBox3D:
        """For 3D objects, return local bounds (min, max). Default may delegate to 2D."""
        ...

    def get_surface_info(self, obj: Any, **kwargs: Any) -> dict:
        """For planar objects like tapes, report local surface for 3D placement."""
        ...


@dataclass
class BoundingBox3D:
    min: tuple[float, float, float]
    max: tuple[float, float, float]

    @property
    def size(self) -> tuple[float, float, float]:
        return (
            self.max[0] - self.min[0],
            self.max[1] - self.min[1],
            self.max[2] - self.min[2],
        )


# Re-exports for convenience
__all__ = ["MeasuredSize", "MeasurementBackend", "BoundingBox3D"]
