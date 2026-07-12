"""Quadratic factoring lesson — step-by-step math video test scene.

Project slug: quadratic_factoring
Render:       matemium render quadratic_factoring
Output:       outputs/quadratic_factoring/media/
"""

from __future__ import annotations

from canvas import CanvasScene
from canvas.builder import CanvasBuilder


class QuadraticFactoring(CanvasScene):
    """Factor x² − 5x + 6 = 0 and find the roots."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Quadratic Factoring")
        tape = builder.add_tape("main")

        # ---- Problem ----
        tape.add_heading("Factor a quadratic", style={"align": "center", "margin-bottom": 0.5})
        tape.add_body(
            "We solve by factoring: rewrite the trinomial as a product of two binomials, "
            "then use the zero-product rule.",
            style={"margin-bottom": 0.7},
        )
        tape.add_math(
            r"x^2 - 5x + 6 = 0",
            style={"margin-bottom": 1.0, "align": "center"},
        )

        # ---- Strategy ----
        tape.add_heading("Find two numbers", style={"margin-top": 0.4, "margin-bottom": 0.35})
        tape.add_flex_row(
            [
                tape.text_spec("multiply to", style={"width": 2.0, "align": "right"}),
                tape.math_spec(r"+6", style={"width": 1.2}),
                tape.text_spec("and add to", style={"width": 2.0, "align": "center"}),
                tape.math_spec(r"-5", style={"width": 1.2}),
            ],
            gap=0.35,
            justify_content="center",
            style={"margin-bottom": 0.5},
        )
        tape.add_body(
            "List factor pairs of 6: (1, 6), (2, 3). "
            "Only 2 and 3 add to 5 — with the middle term negative, both signs are minus.",
            style={"margin-bottom": 0.6},
        )

        # ---- Factor ----
        tape.add_heading("Write the factors", style={"margin-top": 0.35, "margin-bottom": 0.35})
        tape.add_math(
            r"x^2 - 5x + 6 = (x - 2)(x - 3)",
            run_time=2.0,
            style={"margin-bottom": 0.8, "align": "center"},
        )
        tape.add_body(
            "Check by FOIL: (x − 2)(x − 3) = x² − 3x − 2x + 6 = x² − 5x + 6 ✓",
            style={"margin-bottom": 0.6},
        )

        # ---- Zero product ----
        tape.add_heading("Zero-product rule", style={"margin-top": 0.35, "margin-bottom": 0.35})
        tape.add_math(
            r"(x - 2)(x - 3) = 0",
            style={"margin-bottom": 0.5, "align": "center"},
        )
        tape.add_body(
            "If a product is zero, at least one factor is zero.",
            style={"margin-bottom": 0.45},
        )
        tape.add_flex_column(
            [
                tape.math_spec(r"x - 2 = 0 \quad \Rightarrow \quad x = 2", style={"width": 5.0}),
                tape.math_spec(r"x - 3 = 0 \quad \Rightarrow \quad x = 3", style={"width": 5.0}),
            ],
            gap=0.4,
            align_items="center",
            style={"margin-bottom": 0.7},
        )

        # ---- Visual break (parabola cross-section) ----
        tape.add_body(
            "The parabola crosses the x-axis at x = 2 and x = 3 — exactly our factored roots.",
            style={"margin-bottom": 0.6},
        )

        # ---- Verify ----
        tape.add_heading("Verify", style={"margin-top": 0.35, "margin-bottom": 0.35})
        tape.add_flex_row(
            [
                tape.math_spec(r"x=2:\; 4-10+6=0", style={"width": 2.8}),
                tape.math_spec(r"x=3:\; 9-15+6=0", style={"width": 2.8}),
            ],
            gap=0.6,
            justify_content="center",
            style={"margin-bottom": 0.5},
        )

        # ---- Summary ----
        tape.add_heading("Summary", style={"align": "center", "margin-top": 0.4, "margin-bottom": 0.4})
        tape.add_flex_column(
            [
                tape.text_spec("① Find two numbers: product = c, sum = b", style={"width": 5.8}),
                tape.text_spec("② Write (x − m)(x − n)", style={"width": 5.8}),
                tape.text_spec("③ Set each factor to zero", style={"width": 5.8}),
            ],
            gap=0.3,
            align_items="center",
            style={"margin-bottom": 0.5},
        )
        tape.add_math(
            r"x^2 - 5x + 6 = 0 \;\Rightarrow\; x = 2 \text{ or } x = 3",
            style={"align": "center", "margin-bottom": 0.8},
        )

        # --- Context switch demo ---
        root_marker = builder.add_object(
            "Solid3D",
            position=(7, 1, 6),
            content={"shape": "sphere", "size": 1.8},
        )
        builder.observe_object(root_marker, run_time=2.5)

        # Clean context switch to new tape
        summary_tape = builder.add_tape("summary_panel")

        summary_tape.add_heading("Roots", style={"align": "center"})
        summary_tape.add_math(r"x=2 \quad x=3", style={"align": "center"})

        super().__init__(dsl=builder.build(), **kwargs)