"""Electromagnetic waves — multi-section physics lesson test scene.

Project slug: em_waves
Render:       matemium render em_waves
Output:       outputs/em_waves/media/
"""

from __future__ import annotations

from canvas import CanvasScene
from canvas.builder import CanvasBuilder
from canvas.dsl import WorldPoint


class EmWaves(CanvasScene):
    """How Maxwell's equations lead to propagating EM waves."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Electromagnetic Waves")
        tape = builder.add_tape("main")

        # Pose the main tape in 3D space (tilts the plane itself). Camera in tape-scroll
        # mode will automatically look straight down the local normal (from above).)

        # ---- Intro ----
        tape.add_heading("Electromagnetic waves", style={"align": "center", "margin-bottom": 0.5})
        tape.add_body(
            "Light, radio, and X-rays are the same phenomenon: oscillating electric and magnetic "
            "fields that travel through space — coupled, in phase, and perpendicular to each other.",
            style={"margin-bottom": 0.7},
        )
        tape.add_flex_row(
            [
                tape.text_spec("Electric field E", style={"width": 2.6, "align": "center"}),
                tape.text_spec("⟷ coupled", style={"width": 1.6, "align": "center"}),
                tape.text_spec("Magnetic field B", style={"width": 2.6, "align": "center"}),
            ],
            gap=0.3,
            justify_content="center",
            style={"margin-bottom": 0.6},
        )

        # ---- Maxwell (vacuum) ----
        tape.add_heading("Maxwell's equations (vacuum)", style={"margin-top": 0.4, "margin-bottom": 0.35})
        tape.add_body(
            "In empty space, with no charges or currents, four laws tie E and B together.",
            style={"margin-bottom": 0.5},
        )
        tape.add_flex_column(
            [
                tape.math_spec(r"\nabla \cdot \vec{E} = 0", style={"width": 4.5}),
                tape.math_spec(r"\nabla \cdot \vec{B} = 0", style={"width": 4.5}),
                tape.math_spec(r"\nabla \times \vec{E} = -\frac{\partial \vec{B}}{\partial t}", style={"width": 5.5}),
                tape.math_spec(
                    r"\nabla \times \vec{B} = \mu_0 \varepsilon_0 \frac{\partial \vec{E}}{\partial t}",
                    style={"width": 5.8},
                ),
            ],
            gap=0.35,
            align_items="center",
            style={"margin-bottom": 0.6},
        )
        tape.add_body(
            "Faraday (3rd) says a changing B creates curl in E. "
            "Ampère–Maxwell (4th) says a changing E creates curl in B.",
            style={"margin-bottom": 0.6},
        )

        # ---- Wave equation ----
        tape.add_heading("The wave equation", style={"margin-top": 0.35, "margin-bottom": 0.35})
        tape.add_body(
            "Take the curl of Faraday's law, substitute Ampère–Maxwell, and assume no charges. "
            "The electric field obeys a wave equation:",
            style={"margin-bottom": 0.5},
        )
        tape.add_math(
            r"\nabla^2 \vec{E} = \mu_0 \varepsilon_0 \frac{\partial^2 \vec{E}}{\partial t^2}",
            run_time=2.0,
            style={"margin-bottom": 0.5, "align": "center"},
        )
        tape.add_body(
            "The same equation holds for B. Solutions are waves that propagate at speed "
            r"c = 1/\sqrt{\mu_0 \varepsilon_0}.",
            style={"margin-bottom": 0.55},
        )
        tape.add_math(
            r"c = \frac{1}{\sqrt{\mu_0 \varepsilon_0}} \approx 3 \times 10^8\ \mathrm{m/s}",
            style={"margin-bottom": 0.7, "align": "center"},
        )

        # ---- Plane wave ----
        tape.add_heading("A plane wave", style={"margin-top": 0.35, "margin-bottom": 0.35})
        tape.add_body(
            "Traveling in the +x direction, E and B oscillate in phase, perpendicular to each other "
            "and to the direction of travel.",
            style={"margin-bottom": 0.5},
        )
        tape.add_flex_row(
            [
                tape.math_spec(
                    r"\vec{E} = E_0 \cos(kx - \omega t)\,\hat{\jmath}",
                    style={"width": 3.4},
                ),
                tape.math_spec(
                    r"\vec{B} = B_0 \cos(kx - \omega t)\,\hat{k}",
                    style={"width": 3.4},
                ),
            ],
            gap=0.5,
            justify_content="center",
            align_items="center",
            style={"margin-bottom": 0.45},
        )
        tape.add_flex_column(
            [
                tape.text_spec("E ⟂ B", style={"width": 3.0, "align": "center"}),
                tape.text_spec("both ⟂ direction of travel", style={"width": 4.5, "align": "center"}),
                tape.math_spec(r"\frac{E_0}{B_0} = c", style={"width": 3.2}),
            ],
            gap=0.3,
            align_items="center",
            style={"margin-bottom": 0.6},
        )

        # ---- Visual break ----
        builder.add_3d(
            r"z = \sin(x)\cos(y)",
            pitch=50,
            style={"margin-bottom": 0.5, "width": 5.2, "align": "center"},
        )
        tape.add_body(
            "A snapshot of a wave-like surface — the full 3D field animation is coming; "
            "for now the equation labels the visual break between theory and summary.",
            after_3d=True,
            style={"margin-bottom": 0.6},
        )

        # ---- Spectrum ----
        tape.add_heading("One phenomenon, many frequencies", style={"margin-top": 0.35, "margin-bottom": 0.35})
        tape.add_flex_row(
            [
                tape.text_spec("Radio", style={"width": 1.3, "align": "center"}),
                tape.text_spec("Microwave", style={"width": 1.5, "align": "center"}),
                tape.text_spec("Visible", style={"width": 1.3, "align": "center"}),
                tape.text_spec("X-ray", style={"width": 1.2, "align": "center"}),
            ],
            gap=0.25,
            justify_content="space-between",
            style={"margin-bottom": 0.45},
        )
        tape.add_body(
            "Same physics — different wavelength λ and frequency f, related by c = λf.",
            style={"margin-bottom": 0.5},
        )
        tape.add_math(
            r"c = \lambda f",
            style={"align": "center", "margin-bottom": 0.7},
        )

        # ---- Summary ----
        tape.add_heading("Summary", style={"align": "center", "margin-top": 0.4, "margin-bottom": 0.4})
        tape.add_flex_column(
            [
                tape.text_spec("① Maxwell links changing E and B", style={"width": 5.8}),
                tape.text_spec("② Both fields satisfy wave equations", style={"width": 5.8}),
                tape.text_spec("③ Waves travel at c, E ⟂ B ⟂ propagation", style={"width": 5.8}),
                tape.text_spec("④ Light is an electromagnetic wave", style={"width": 5.8}),
            ],
            gap=0.28,
            align_items="center",
            style={"margin-bottom": 0.5},
        )
        tape.add_math(
            r"\nabla \times \vec{E} = -\frac{\partial \vec{B}}{\partial t}"
            r"\quad\Rightarrow\quad"
            r"\text{light}",
            style={"align": "center", "margin-bottom": 0.8},
        )

        # Add a 3D representation (axes + a simple solid for the wave concept)
        # (main tape pose already set early at top of __init__)
        builder.add_object("Axes", id="em_axes", position=(0, -1, 4), scale=0.7)
        builder.add_object(
            "Solid3D",
            id="em_wave_3d",
            position=(1.5, 0.5, 5),
            content={"shape": "cylinder", "size": 0.8},
        )

        # Create a secondary camera-facing "key formulas" tape.
        key_tape = builder.add_tape(
            "key_formulas",
        )
        key_tape.add_math(r"\nabla \times \vec{E} = -\frac{\partial \vec{B}}{\partial t}")
        key_tape.add_math(r"c = \frac{1}{\sqrt{\mu_0 \varepsilon_0}}")

        # Camera sequence using new observation modes to "animate" the content
        # Normal 3D view of the wave concept object
        builder.observe_object("em_wave_3d", run_time=3.0)

        # Enter tape-scroll mode on the main tilted tape

        # Explicitly close the formulas tape over the world.
        builder.scroll_tape(tape_id="key_formulas", local_y=0.0, run_time=2.5)

        # Pure 3D fly-around
        builder.add_camera_keyframe(target=WorldPoint(position=(2, 3, 10)), duration=2.5)

        super().__init__(dsl=builder.build(), **kwargs)
