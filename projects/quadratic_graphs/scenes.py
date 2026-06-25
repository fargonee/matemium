"""Quadratic graphs — compare shapes, trace dots, zoom & highlight.

Project slug: quadratic_graphs
Render:       matemium render quadratic_graphs
Output:       outputs/quadratic_graphs/media/
"""

from __future__ import annotations

from canvas import CanvasScene
from canvas.builder import CanvasBuilder

from .helpers import add_compare_row, add_plot_trace


class QuadraticGraphs(CanvasScene):
    """How a, b, and c change the graph of ax² + bx + c."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Quadratic Graphs")

        builder.add_heading("Graphs of quadratics", style={"align": "center", "margin-bottom": 0.45})
        builder.add_math(
            r"ax^2 + bx + c = 0",
            style={"align": "center", "margin-bottom": 0.55},
        )
        builder.add_body(
            "The same formula can look very different on a graph. "
            "Each coefficient moves the parabola in a predictable way — "
            "compare pairs side by side and watch y change as x moves.",
            style={"margin-bottom": 0.65},
        )

        builder.add_heading("Effect of a", style={"margin-top": 0.35, "margin-bottom": 0.3})
        plot_a_pos, plot_a_neg = add_compare_row(
            builder,
            (1, -2, 1),
            (-1, 2, 1),
            left_id="plot_a_pos",
            right_id="plot_a_neg",
            style={"align": "center", "margin-bottom": 0.35},
            left_kwargs={"x_range": (-1, 3), "x_start": 0, "color": "#5eb3ff"},
            right_kwargs={"x_range": (-1, 3), "x_start": 0, "color": "#ff8a65"},
        )

        builder.add_body(
            "a > 0: opens upward (blue).  a < 0: opens downward (orange). "
            "The sign of a is the single biggest shape difference.",
            style={"margin-bottom": 0.45},
        )
        add_plot_trace(builder, plot_a_pos, x_from=-0.5, x_to=2.5, run_time=3.2)
        builder.add_camera_focus(plot_a_pos, zoom=2.1, hold_time=1.2)

        super().__init__(dsl=builder.build(), **kwargs)