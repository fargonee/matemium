"""Quadratic graphs — compare shapes, trace dots, zoom & highlight.

Project slug: quadratic_graphs
Render:       matemium render quadratic_graphs
Output:       outputs/quadratic_graphs/media/
"""

from __future__ import annotations

from canvas import CanvasScene, WorldPoint
from canvas.builder import CanvasBuilder

from .helpers import add_compare_row, add_plot_trace


class QuadraticGraphs(CanvasScene):
    """How a, b, and c change the graph of ax² + bx + c."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Quadratic Graphs")
        tape = builder.add_tape("main")

        # Pose the main tape in 3D space (tilts the plane itself). Camera in tape-scroll
        # mode will automatically look straight down the local normal (from above).)

        tape.add_heading("Graphs of quadratics", style={"align": "center", "margin-bottom": 0.45})
        tape.add_math(
            r"ax^2 + bx + c = 0",
            style={"align": "center", "margin-bottom": 0.55},
        )
        tape.add_body(
            "The same formula can look very different on a graph. "
            "Each coefficient moves the parabola in a predictable way — "
            "compare pairs side by side and watch y change as x moves.",
            style={"margin-bottom": 0.65},
        )

        tape.add_heading("Effect of a", style={"margin-top": 0.35, "margin-bottom": 0.3})
        plot_a_pos, plot_a_neg = add_compare_row(tape, 
            builder,
            (1, -2, 1),
            (-1, 2, 1),
            left_id="plot_a_pos",
            right_id="plot_a_neg",
            style={"align": "center", "margin-bottom": 0.35},
            left_kwargs={"x_range": (-1, 3), "x_start": 0, "color": "#5eb3ff"},
            right_kwargs={"x_range": (-1, 3), "x_start": 0, "color": "#ff8a65"},
        )

        tape.add_body(
            "a > 0: opens upward (blue).  a < 0: opens downward (orange). "
            "The sign of a is the single biggest shape difference.",
            style={"margin-bottom": 0.45},
        )
        add_plot_trace(builder, plot_a_pos, x_from=-0.5, x_to=2.5, run_time=3.2)
        # Focus on element (still supported; alternatively use observe_object with params) 
        builder.add_camera_focus(plot_a_pos, zoom=2.1, hold_time=1.2)

        # Add a 3D axes to give spatial context to the graphs (pose already set early)
        builder.add_object("Axes", position=(-2, 0, 3), scale=0.6)

        # Create a floating "notes" tape using the new first-class add_tape API
        notes = builder.add_tape("graph_notes")
        notes.add_body("a controls width", style={"align": "center"})

        # Use new modes to animate the presentation
        builder.observe_object("Axes", run_time=2.0)  # normal 3D  # enter tape scroll on main rotated tape
        builder.observe_object(notes, run_time=2.0)   # look at secondary tape in 3D
        builder.add_camera_keyframe(target=WorldPoint(position=(1, 4, 6)), duration=2.0)

        super().__init__(dsl=builder.build(), **kwargs)