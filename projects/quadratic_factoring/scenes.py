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

        # ---- Problem ----
        builder.add_heading("Factor a quadratic", style={"align": "center", "margin-bottom": 0.5})
        builder.add_body(
            "We solve by factoring: rewrite the trinomial as a product of two binomials, "
            "then use the zero-product rule.",
            style={"margin-bottom": 0.7},
        )
        builder.add_math(
            r"x^2 - 5x + 6 = 0",
            style={"margin-bottom": 1.0, "align": "center"},
        )

        # ---- Strategy ----
        builder.add_heading("Find two numbers", style={"margin-top": 0.4, "margin-bottom": 0.35})
        builder.add_flex_row(
            [
                builder.text_spec("multiply to", style={"width": 2.0, "align": "right"}),
                builder.math_spec(r"+6", style={"width": 1.2}),
                builder.text_spec("and add to", style={"width": 2.0, "align": "center"}),
                builder.math_spec(r"-5", style={"width": 1.2}),
            ],
            gap=0.35,
            justify_content="center",
            style={"margin-bottom": 0.5},
        )
        builder.add_body(
            "List factor pairs of 6: (1, 6), (2, 3). "
            "Only 2 and 3 add to 5 — with the middle term negative, both signs are minus.",
            style={"margin-bottom": 0.6},
        )

        # ---- Factor ----
        builder.add_heading("Write the factors", style={"margin-top": 0.35, "margin-bottom": 0.35})
        builder.add_math(
            r"x^2 - 5x + 6 = (x - 2)(x - 3)",
            run_time=2.0,
            style={"margin-bottom": 0.8, "align": "center"},
        )
        builder.add_observation(
            "Check by FOIL: (x − 2)(x − 3) = x² − 3x − 2x + 6 = x² − 5x + 6 ✓",
            style={"margin-bottom": 0.6},
        )

        # ---- Zero product ----
        builder.add_heading("Zero-product rule", style={"margin-top": 0.35, "margin-bottom": 0.35})
        builder.add_math(
            r"(x - 2)(x - 3) = 0",
            style={"margin-bottom": 0.5, "align": "center"},
        )
        builder.add_body(
            "If a product is zero, at least one factor is zero.",
            style={"margin-bottom": 0.45},
        )
        builder.add_flex_column(
            [
                builder.math_spec(r"x - 2 = 0 \quad \Rightarrow \quad x = 2", style={"width": 5.0}),
                builder.math_spec(r"x - 3 = 0 \quad \Rightarrow \quad x = 3", style={"width": 5.0}),
            ],
            gap=0.4,
            align_items="center",
            style={"margin-bottom": 0.7},
        )

        # ---- Visual break (parabola cross-section) ----
        builder.add_3d(
            r"z = x^2 - 5x + 6",
            pitch=48,
            style={"margin-bottom": 0.5, "width": 5.0, "align": "center"},
        )
        builder.add_body(
            "The parabola crosses the x-axis at x = 2 and x = 3 — exactly our factored roots.",
            after_3d=True,
            style={"margin-bottom": 0.6},
        )

        # ---- Verify ----
        builder.add_heading("Verify", style={"margin-top": 0.35, "margin-bottom": 0.35})
        builder.add_flex_row(
            [
                builder.math_spec(r"x=2:\; 4-10+6=0", style={"width": 2.8}),
                builder.math_spec(r"x=3:\; 9-15+6=0", style={"width": 2.8}),
            ],
            gap=0.6,
            justify_content="center",
            style={"margin-bottom": 0.5},
        )

        # ---- Summary ----
        builder.add_heading("Summary", style={"align": "center", "margin-top": 0.4, "margin-bottom": 0.4})
        builder.add_flex_column(
            [
                builder.text_spec("① Find two numbers: product = c, sum = b", style={"width": 5.8}),
                builder.text_spec("② Write (x − m)(x − n)", style={"width": 5.8}),
                builder.text_spec("③ Set each factor to zero", style={"width": 5.8}),
            ],
            gap=0.3,
            align_items="center",
            style={"margin-bottom": 0.5},
        )
        builder.add_math(
            r"x^2 - 5x + 6 = 0 \;\Rightarrow\; x = 2 \text{ or } x = 3",
            style={"align": "center", "margin-bottom": 0.8},
        )

        # --- 3D world enhancements (newest authoring) ---
        # Test meaningful 3D world features:
        # - Main tape default (flat)
        # - Second tape perpendicular (90 deg rotation)
        # - Bigger sphere, placed further away
        # - Camera tour ends with orbiting the sphere
        root_marker = builder.add_object(
            "Solid3D",
            position=(7, 1, 6),
            content={"shape": "sphere", "size": 1.8},
        )

        # Secondary tape perpendicular to main tape
        summary_tape = builder.add_tape(
            "summary_panel",
            position=(0, 1, -5),
            rotation=(90, 0, 0),
        )

        with builder.in_object_space(summary_tape):
            builder.add_heading("Roots", style={"align": "center"})
            builder.add_math(r"x=2 \quad x=3", style={"align": "center"})

        # Camera tour using the new high-level observation modes
        # 1. Normal 3D cinematic look at the 3D marker (tape treated as 3D object)
        builder.observe_object(root_marker, run_time=2.5)

        # 2. Switch to tape-scroll-mode for classic reveal on the main tape
        builder.scroll_tape(local_y=6.0, run_time=3.5)

        # 3. Look at the secondary (perpendicular) tape in pure 3D
        builder.observe_object(summary_tape, run_time=2.0)

        # 4. Lift and orbit the sphere as the finale
        builder.add_solid_lift(root_marker, lift=2.5, run_time=1.0)
        builder.add_camera_inspect(
            root_marker,
            orbit=True,
            orbit_degrees=360.0,
            orbit_run_time=6.0,
            return_to_sheet=True,
            return_run_time=1.5,
        )

        super().__init__(dsl=builder.build(), **kwargs)