"""Layout engine for Matemium.

Parses author-facing style dicts, measures elements, and resolves absolute
canvas positions using a vertical flow model (border-box) plus flex containers.

Phase 1 (this module): flat timeline with resolved coordinates on each leaf.
Future: optional layout tree before coordinate resolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    pass

from .coords import z_for_element
from .dsl import CanvasElement, LayoutBox
from .measure import measure_element, strip_layout_from_content, get_measurement_backend, _OBJECT_KINDS
# The measurement backend (see canvas/measurement/) allows swapping the sizing
# implementation. For manim-web preview we can eventually supply a KaTeX one
# so that layout decisions made here match exactly what the browser will render.

EXTRA_MARGIN_AFTER_3D = 1.6
# Default vertical gap between stacked block elements (Manim units).
DEFAULT_ROW_MARGIN_BOTTOM = 1.0


@dataclass
class Style:
    """Author-facing style parsed from a CSS-like dict."""

    margin_top: float = 0.0
    margin_bottom: float = 0.0
    margin_left: float = 0.0
    margin_right: float = 0.0
    width: Optional[float] = None
    height: Optional[float] = None
    align: str = "center"
    wrap: Optional[bool] = None

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "Style":
        if not d:
            return cls()
        m = d.get("margin", 0)
        if isinstance(m, (int, float)):
            mt = mb = ml = mr = float(m)
        else:
            parts = str(m).split()
            if len(parts) == 1:
                mt = mb = ml = mr = float(parts[0])
            elif len(parts) == 2:
                mt = mb = float(parts[0])
                ml = mr = float(parts[1])
            elif len(parts) == 4:
                mt, mr, mb, ml = (float(parts[i]) for i in range(4))
            else:
                mt = mb = ml = mr = 0.0
        mt = float(d.get("margin-top", mt))
        mb = float(d.get("margin-bottom", mb))
        ml = float(d.get("margin-left", ml))
        mr = float(d.get("margin-right", mr))
        wrap = d.get("wrap")
        if wrap is not None:
            wrap = bool(wrap)
        return cls(
            margin_top=mt,
            margin_bottom=mb,
            margin_left=ml,
            margin_right=mr,
            width=d.get("width"),
            height=d.get("height"),
            align=d.get("align", d.get("text-align", "center")),
            wrap=wrap,
        )


@dataclass
class FlowState:
    """Vertical flow cursor for the infinite tape."""

    last_bottom: float = 0.0
    y: float = 0.0
    last_was_3d: bool = False


@dataclass
class MeasuredItem:
    element: CanvasElement
    style: Style
    width: float
    height: float
    wrap: bool


class LayoutEngine:
    """Resolves element sizes and positions within a specific object's local space.

    Phase 6: Always scoped to an object's local space.
    - For TapeObject: full CSS-like flex, vertical flow, styling.
    - For other 3D objects: may use identity layout or simple rules (explicit positions).
    The engine is instantiated per-object during build.
    """

    def __init__(self, frame_width: float, frame_height: float = 16.0, scope: Optional[Any] = None):
        self.scope = scope  # Phase 6: the owning object (TapeObject, etc.)
        if scope and hasattr(scope, 'local_canvas_settings') and scope.local_canvas_settings:
            frame_width = scope.local_canvas_settings.frame_width
            frame_height = scope.local_canvas_settings.frame_height
        elif scope and hasattr(scope, 'get_local_frame'):
            fw, fh = scope.get_local_frame()
            frame_width, frame_height = fw, fh
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.flow = FlowState()
        self.scope = scope
        self.is_tape_like = bool(scope and hasattr(scope, 'local_elements'))  # Phase 6
        self.tape = scope if self.is_tape_like else None  # compat

    def usable_width(self, style: Style) -> float:
        return max(0.5, self.frame_width - style.margin_left - style.margin_right)

    def measure(self, elem: CanvasElement, style: Style) -> MeasuredItem:
        # Phase 9: check registered kind measure first
        if elem.type in _OBJECT_KINDS and _OBJECT_KINDS[elem.type].get("measure"):
            try:
                ms = _OBJECT_KINDS[elem.type]["measure"](elem, style=style, usable_width=self.usable_width(style))
                if isinstance(ms, MeasuredSize):
                    return MeasuredItem(elem, style, ms.width, ms.height, False)
            except Exception:
                pass

        backend = get_measurement_backend()
        if backend is not None:
            # Renderer-agnostic path: delegate sizing to the injected backend.
            # When the desktop preview provides a KaTeXMeasurementBackend, layout
            # sizes will match what manim-web will display → true WYSIWYG.
            try:
                ms = backend.measure_element(elem, usable_width=self.usable_width(style))
                return MeasuredItem(elem, style, ms.width, ms.height, False)
            except Exception:
                pass  # fall through to default

        tw, th, wrap = measure_element(
            elem,
            usable_width=self.usable_width(style),
            style_width=style.width,
            style_height=style.height,
            wrap=style.wrap,
        )
        return MeasuredItem(elem, style, tw, th, wrap)

    def _horizontal_center(
        self,
        style: Style,
        box_width: float,
    ) -> float:
        if style.align == "left":
            return -(self.frame_width / 2) + style.margin_left + (box_width / 2)
        if style.align == "right":
            return (self.frame_width / 2) - style.margin_right - (box_width / 2)
        return (style.margin_left - style.margin_right) / 2.0

    def _finalize_element(
        self,
        elem: CanvasElement,
        style: Style,
        width: float,
        height: float,
        wrap: bool,
        x: float,
        center_y: float,
    ) -> CanvasElement:
        elem.canvas_position = (x, center_y, z_for_element(elem))
        elem.layout = LayoutBox(
            width=width,
            height=height,
            wrap=wrap,
            align=style.align,
            margin_top=style.margin_top,
            margin_bottom=style.margin_bottom,
            margin_left=style.margin_left,
            margin_right=style.margin_right,
        )
        elem.content = strip_layout_from_content(elem.content)
        return elem

    def place_overlay(
        self,
        elem: CanvasElement,
        center_x: float,
        center_y: float,
        width: float,
        height: float,
    ) -> CanvasElement:
        """Place at absolute canvas coords without advancing vertical flow."""
        return self._finalize_element(
            elem, Style(), width, height, False, center_x, center_y
        )

    def place_block(
        self,
        elem: CanvasElement,
        style_dict: Optional[Dict[str, Any]] = None,
    ) -> CanvasElement:
        """Place a single element in the vertical flow.
        Phase 6: for non-tape scopes, skip auto-flow and use explicit pos.
        """
        if not getattr(self, 'is_tape_like', True):
            style = Style.from_dict(style_dict)
            measured = self.measure(elem, style)
            x = getattr(elem, 'canvas_position', (0,0,0))[0] or 0
            y = getattr(elem, 'canvas_position', (0,0,0))[1] or 0
            return self._finalize_element(
                elem, style, measured.width, measured.height, measured.wrap, x, y
            )
        style = Style.from_dict(style_dict)
        if style.margin_bottom == 0.0:
            style.margin_bottom = DEFAULT_ROW_MARGIN_BOTTOM
        measured = self.measure(elem, style)

        extra_mt = (
            EXTRA_MARGIN_AFTER_3D
            if self.flow.last_was_3d and elem.type not in ("ThreeDGraph", "Surface", "Solid3D")
            else 0.0
        )

        top_y = self.flow.last_bottom - style.margin_top - extra_mt
        center_y = top_y - (measured.height / 2.0)
        x = self._horizontal_center(style, measured.width)

        self._finalize_element(
            elem, style, measured.width, measured.height, measured.wrap, x, center_y
        )

        bottom_y = top_y - measured.height
        self.flow.last_bottom = bottom_y - style.margin_bottom
        self.flow.last_was_3d = elem.type in ("ThreeDGraph", "Surface", "Solid3D")
        return elem

    def layout_flex_row(
        self,
        items: List[MeasuredItem],
        *,
        gap: float,
        justify_content: str,
        align_items: str,
        container_style: Style,
    ) -> List[CanvasElement]:
        if not getattr(self, 'is_tape_like', True):
            # non-tape: return as-is with positions
            return [m.element for m in items]
        n = len(items)
        if n == 0:
            return []

        total_content_w = sum(m.width for m in items)
        max_h = max(m.height for m in items)

        j = (justify_content or "start").lower()
        if container_style.width is not None:
            row_box_w = float(container_style.width)
        elif j in (
            "space-between", "space_between",
            "space-around", "space_around",
            "space-evenly", "space_evenly",
        ):
            usable = self.usable_width(container_style)
            inner_w = total_content_w + (n - 1) * gap if n > 1 else total_content_w
            row_box_w = max(inner_w, usable * 0.92)
        else:
            row_box_w = total_content_w + (n - 1) * gap if n > 1 else total_content_w

        row_box_h = max_h
        inner_w = total_content_w + (n - 1) * gap if n > 1 else total_content_w

        if inner_w > row_box_w and row_box_w > 0.1:
            row_scale = row_box_w / inner_w
            scaled: List[MeasuredItem] = []
            for m in items:
                new_w = m.width * row_scale
                new_h = m.height * row_scale
                if m.element.type == "Text" and m.wrap:
                    remeasured = self.measure(
                        m.element,
                        Style(
                            margin_top=m.style.margin_top,
                            margin_bottom=m.style.margin_bottom,
                            margin_left=m.style.margin_left,
                            margin_right=m.style.margin_right,
                            width=new_w,
                            height=m.style.height,
                            align=m.style.align,
                            wrap=True,
                        ),
                    )
                    new_w, new_h = remeasured.width, remeasured.height
                scaled.append(
                    MeasuredItem(m.element, m.style, new_w, new_h, m.wrap)
                )
            items = scaled
            max_h = max(m.height for m in items)
            row_box_h = max_h
            total_content_w = sum(m.width for m in items)
            inner_w = total_content_w + (n - 1) * gap if n > 1 else total_content_w

        extra_mt = EXTRA_MARGIN_AFTER_3D if self.flow.last_was_3d else 0.0
        row_top = self.flow.last_bottom - container_style.margin_top - extra_mt
        row_cy = row_top - (row_box_h / 2.0)
        row_cx = self._horizontal_center(container_style, row_box_w)
        row_left = row_cx - (row_box_w / 2.0)

        child_xs = self._distribute_x(
            items, gap, j, row_left, row_box_w, total_content_w, n
        )
        child_ys = self._cross_align_y(items, align_items, row_top, row_cy, row_box_h)

        placed: List[CanvasElement] = []
        for idx, m in enumerate(items):
            placed.append(
                self._finalize_element(
                    m.element,
                    m.style,
                    m.width,
                    m.height,
                    m.wrap,
                    child_xs[idx],
                    child_ys[idx],
                )
            )

        row_bot = row_top - row_box_h
        self.flow.last_bottom = row_bot - container_style.margin_bottom
        self.flow.last_was_3d = any(
            m.element.type in ("ThreeDGraph", "Surface", "Solid3D") for m in items
        )
        return placed

    def layout_flex_column(
        self,
        items: List[MeasuredItem],
        *,
        gap: float,
        justify_content: str,
        align_items: str,
        container_style: Style,
    ) -> List[CanvasElement]:
        if not getattr(self, 'is_tape_like', True):
            return [m.element for m in items]
        n = len(items)
        if n == 0:
            return []

        total_h = sum(m.height for m in items)
        max_w = max(m.width for m in items)
        inner_h = total_h + (n - 1) * gap if n > 1 else total_h
        col_box_h = float(container_style.height) if container_style.height else inner_h
        col_box_w = float(container_style.width) if container_style.width else max_w

        extra_mt = EXTRA_MARGIN_AFTER_3D if self.flow.last_was_3d else 0.0
        col_top = self.flow.last_bottom - container_style.margin_top - extra_mt
        col_cy = col_top - (col_box_h / 2.0)

        calign = (align_items or "center").lower()
        if calign == "left":
            col_cx = -(self.frame_width / 2) + container_style.margin_left + (col_box_w / 2)
        elif calign == "right":
            col_cx = (self.frame_width / 2) - container_style.margin_right - (col_box_w / 2)
        else:
            col_cx = (container_style.margin_left - container_style.margin_right) / 2.0

        child_ys = self._distribute_y(
            items, gap, justify_content, col_top, col_box_h, total_h, n
        )

        placed: List[CanvasElement] = []
        for idx, m in enumerate(items):
            if calign == "left":
                ix = col_cx - (col_box_w / 2) + (m.width / 2)
            elif calign == "right":
                ix = col_cx + (col_box_w / 2) - (m.width / 2)
            else:
                ix = col_cx
            placed.append(
                self._finalize_element(
                    m.element,
                    m.style,
                    m.width,
                    m.height,
                    m.wrap,
                    ix,
                    child_ys[idx],
                )
            )

        col_bot = col_top - col_box_h
        self.flow.last_bottom = col_bot - container_style.margin_bottom
        self.flow.last_was_3d = any(
            m.element.type in ("ThreeDGraph", "Surface", "Solid3D") for m in items
        )
        return placed

    def suggest_camera_dy(
        self,
        *,
        viewport_fraction: float = 0.85,
        min_dy: float = 2.0,
    ) -> Optional[float]:
        """Suggest scroll when content extends beyond the current camera anchor."""
        extent = abs(self.flow.last_bottom - self.flow.y)
        threshold = self.frame_height * viewport_fraction
        if extent <= threshold:
            return None
        return max(min_dy, extent - threshold)

    def _distribute_x(
        self,
        items: List[MeasuredItem],
        gap: float,
        justify: str,
        row_left: float,
        row_box_w: float,
        total_content_w: float,
        n: int,
    ) -> List[float]:
        if n == 1:
            return [row_left + row_box_w / 2.0]

        centers: List[float] = []
        if justify in ("space-between", "space_between"):
            space = (row_box_w - total_content_w) / (n - 1)
            cx = row_left
            for m in items:
                centers.append(cx + m.width / 2.0)
                cx += m.width + space
        elif justify in ("space-around", "space_around"):
            space = (row_box_w - total_content_w) / n
            cx = row_left + space / 2.0
            for m in items:
                centers.append(cx + m.width / 2.0)
                cx += m.width + space
        elif justify in ("space-evenly", "space_evenly"):
            space = (row_box_w - total_content_w) / (n + 1)
            cx = row_left + space
            for m in items:
                centers.append(cx + m.width / 2.0)
                cx += m.width + space
        elif justify in ("end", "flex-end", "right"):
            used = total_content_w + (n - 1) * gap
            cx = row_left + (row_box_w - used)
            for m in items:
                centers.append(cx + m.width / 2.0)
                cx += m.width + gap
        elif justify in ("center", "centre"):
            used = total_content_w + (n - 1) * gap
            cx = row_left + (row_box_w - used) / 2.0
            for m in items:
                centers.append(cx + m.width / 2.0)
                cx += m.width + gap
        else:
            cx = row_left
            for m in items:
                centers.append(cx + m.width / 2.0)
                cx += m.width + gap
        return centers

    def _cross_align_y(
        self,
        items: List[MeasuredItem],
        align_items: str,
        row_top: float,
        row_cy: float,
        row_box_h: float,
    ) -> List[float]:
        a = (align_items or "center").lower()
        ys: List[float] = []
        for m in items:
            if a in ("start", "flex-start", "top"):
                ys.append(row_top - m.height / 2.0)
            elif a in ("end", "flex-end", "bottom"):
                row_bot = row_top - row_box_h
                ys.append(row_bot + m.height / 2.0)
            else:
                ys.append(row_cy)
        return ys

    def _distribute_y(
        self,
        items: List[MeasuredItem],
        gap: float,
        justify: str,
        col_top: float,
        col_box_h: float,
        total_h: float,
        n: int,
    ) -> List[float]:
        if n == 1:
            return [col_top - col_box_h / 2.0]

        j = (justify or "start").lower()
        centers: List[float] = []
        if j in ("space-between", "space_between"):
            space = (col_box_h - total_h) / (n - 1)
            cy = col_top
            for m in items:
                centers.append(cy - m.height / 2.0)
                cy -= m.height + space
        elif j in ("space-around", "space_around"):
            space = (col_box_h - total_h) / n
            cy = col_top - space / 2
            for m in items:
                centers.append(cy - m.height / 2.0)
                cy -= m.height + space
        elif j in ("space-evenly", "space_evenly"):
            space = (col_box_h - total_h) / (n + 1)
            cy = col_top - space
            for m in items:
                centers.append(cy - m.height / 2.0)
                cy -= m.height + space
        elif j in ("end", "flex-end"):
            used = total_h + (n - 1) * gap
            cy = col_top - (col_box_h - used)
            for m in items:
                centers.append(cy - m.height / 2.0)
                cy -= m.height + gap
        elif j in ("center",):
            used = total_h + (n - 1) * gap
            cy = col_top - (col_box_h - used) / 2
            for m in items:
                centers.append(cy - m.height / 2.0)
                cy -= m.height + gap
        else:
            cy = col_top
            for m in items:
                centers.append(cy - m.height / 2.0)
                cy -= m.height + gap
        return centers