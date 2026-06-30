"""Default measurement backend backed by Manim (used for final renders)."""

from __future__ import annotations

from typing import Any, Optional

from ..measure import measure_element as _measure_element
from . import MeasuredSize, MeasurementBackend, BoundingBox3D


class ManimMeasurementBackend:
    """Uses the existing manim-based measurement (Text/MathTex etc.)."""

    def measure_text(
        self,
        text: str,
        *,
        font_size: float = 36,
        wrap: bool = False,
        target_width: Optional[float] = None,
        **kwargs: Any,
    ) -> MeasuredSize:
        # The existing measure_element understands CanvasElement-like dicts or objects.
        # We synthesize a minimal one.
        fake = type("E", (), {
            "type": "Text",
            "content": text,
            "layout": None,
        })()
        # We call the low-level path via the public measure_element
        try:
            w, h = _measure_element(fake, style={"wrap": wrap, "width": target_width})
            return MeasuredSize(width=w, height=h)
        except Exception:
            # Safe fallback
            approx_w = len(text) * (font_size * 0.018) + 0.2
            return MeasuredSize(width=approx_w, height=font_size * 0.032)

    def measure_math(
        self,
        latex: str,
        *,
        scale: float = 0.9,
        target_width: Optional[float] = None,
        **kwargs: Any,
    ) -> MeasuredSize:
        fake = type("E", (), {
            "type": "MathTex",
            "content": latex,
            "layout": None,
        })()
        try:
            w, h = _measure_element(fake, style={"width": target_width})
            return MeasuredSize(width=w * scale, height=h * scale)
        except Exception:
            approx = max(1.2, len(latex) * 0.035)
            return MeasuredSize(width=approx, height=0.6)

    def measure_element(self, elem: Any, **kwargs: Any) -> MeasuredSize:
        try:
            w, h = _measure_element(elem, **kwargs)
            return MeasuredSize(width=w, height=h)
        except Exception:
            return MeasuredSize(width=2.0, height=0.6)

    def measure_bounding_box(self, obj: Any, **kwargs: Any) -> BoundingBox3D:
        # For Manim, delegate to building a temp mob and get bounds.
        # For Phase 6, simplistic: use 2D for tapes, full 3D for solids.
        from ..measure import build_mobject
        try:
            surf = obj.get_surface_info() if hasattr(obj, 'get_surface_info') else None
            if surf and surf.get('is_planar'):
                w = surf.get('width', 9.0)
                h = surf.get('height', 16.0)
                return BoundingBox3D(min=(-w/2, -h/2, 0), max=(w/2, h/2, 0.01))
            mob = build_mobject(obj) if hasattr(obj, 'type') else None
            if mob:
                # approximate 3D from manim get_center, get_width etc, assume z=0 for 2D
                cx, cy, cz = mob.get_center()
                w = mob.get_width() or 1.0
                h = mob.get_height() or 1.0
                d = getattr(mob, 'get_depth', lambda: 0)() or 0.1
                return BoundingBox3D(
                    min=(cx - w/2, cy - h/2, cz - d/2),
                    max=(cx + w/2, cy + h/2, cz + d/2)
                )
        except Exception:
            pass
        return BoundingBox3D(min=(0,0,0), max=(1,1,1))

    def get_surface_info(self, obj: Any, **kwargs: Any) -> dict:
        # For TapeObject, report local 2D size.
        if hasattr(obj, 'local_canvas_settings') and obj.local_canvas_settings:
            s = obj.local_canvas_settings
            return {"width": s.frame_width, "height": s.frame_height, "is_planar": True}
        if hasattr(obj, 'type') and obj.type in ("TapeObject", "sheet"):
            return {"width": 9.0, "height": 16.0, "is_planar": True}
        return {"is_planar": False}
