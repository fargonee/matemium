"""Quadratic graph lesson helpers — not core engine API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from canvas.builder import CanvasBuilder
from canvas.dsl import CanvasElement, EntryAnimation, PlotTrace
from canvas.plots import format_quadratic_tex


def quad_plot_content(
    a: float,
    b: float,
    c: float,
    *,
    formula: Optional[str] = None,
    x_range: tuple[float, float] = (-2.5, 3.5),
    x_start: float = 0.0,
    color: str = "#5eb3ff",
    **kwargs: Any,
) -> Dict[str, Any]:
    return {
        "a": a,
        "b": b,
        "c": c,
        "formula": formula or format_quadratic_tex(a, b, c),
        "x_range": x_range,
        "x_start": x_start,
        "color": color,
        **kwargs,
    }


def quadratic_plot_element(
    a: float,
    b: float,
    c: float,
    *,
    id: str,
    **kwargs: Any,
) -> CanvasElement:
    return CanvasElement(
        id=id,
        type="QuadraticPlot",
        content=quad_plot_content(a, b, c, **kwargs),
        entry_animation=EntryAnimation(type="Create", run_time=1.2),
    )


def quadratic_plot_flex_spec(
    builder: CanvasBuilder,
    a: float,
    b: float,
    c: float,
    *,
    id: str,
    style: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """One addressable plot for ``add_flex_row`` via generic ``element_spec``."""
    return builder.element_spec(
        quadratic_plot_element(a, b, c, id=id, **kwargs),
        style=style,
    )


def add_compare_row(
    builder: CanvasBuilder,
    left: tuple[float, float, float],
    right: tuple[float, float, float],
    *,
    left_id: str,
    right_id: str,
    gap: float = 0.55,
    style: Optional[Dict[str, Any]] = None,
    plot_style: Optional[Dict[str, Any]] = None,
    left_kwargs: Optional[Dict[str, Any]] = None,
    right_kwargs: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Side-by-side quadratic plots — separate elements, shared flex reveal."""
    ps = plot_style or {"width": 3.2}
    builder.add_flex_row(
        [
            quadratic_plot_flex_spec(
                builder, *left, id=left_id, style=ps, **(left_kwargs or {})
            ),
            quadratic_plot_flex_spec(
                builder, *right, id=right_id, style=ps, **(right_kwargs or {})
            ),
        ],
        gap=gap,
        style=style,
    )
    return builder.last_flex_ids


def add_plot_trace(
    builder: CanvasBuilder,
    element_id: str,
    *,
    plot_index: int = 0,
    x_from: float = -2.0,
    x_to: float = 2.0,
    run_time: float = 3.0,
    show_readout: bool = True,
) -> CanvasBuilder:
    counter = getattr(builder, "_counter", 0) + 1
    builder._counter = counter
    builder.dsl.add_plot_trace(
        PlotTrace(
            id=f"trace_{counter}",
            element_id=element_id,
            plot_index=plot_index,
            x_from=x_from,
            x_to=x_to,
            run_time=run_time,
            show_readout=show_readout,
        )
    )
    return builder