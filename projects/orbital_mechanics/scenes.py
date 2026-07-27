"""Flagship physics showcase: orbit as continuous free fall."""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings, LayoutBox
from canvas.builder import CanvasBuilder

from .helpers import (
    ACCELERATION_CORAL,
    ALTITUDE_KM,
    EARTH_BLUE,
    ESCAPE_GOLD,
    MUTED,
    ORBIT_CYAN,
    REENTRY_CORAL,
    VELOCITY_GOLD,
    circular_speed,
    gravity_at_altitude,
    gravity_fraction,
    launch_markers,
    launch_trials,
    local_vector_diagram,
    one_trial_plot_series,
    orbit_plot_series,
)

BG = "#07111f"
WHITE = "#f4f8ff"
SOFT = "#b9c7da"
PLOT_STYLE = {"width": 9.2, "height": 4.65, "margin-bottom": 0.55}
PLOT_OPTIONS = {
    "markers": launch_markers(),
    "x_range": [-3.2, 3.2, 1],
    "y_range": [-3.2, 3.2, 1],
    "width": 6.8,
    "height": 4.25,
    "tips": False,
}


def trial_plot_target(trial_id: str) -> CanvasElement:
    """Morph target with the same resolved footprint as the source plot."""

    return CanvasElement(
        id=f"launch_experiment_{trial_id}",
        type="DataPlot",
        content={
            "series": one_trial_plot_series(trial_id),
            **PLOT_OPTIONS,
        },
        layout=LayoutBox(
            width=9.2,
            height=4.65,
            margin_bottom=0.55,
        ),
    )


def card(
    b: CanvasBuilder,
    title: str,
    value: str,
    color: str,
    *,
    width: float = 3.6,
) -> dict:
    return b.text_spec(
        [
            b.run(f"{title}\n{value}", color=color, font_size=24),
        ],
        style={"width": width, "height": 1.35, "wrap": True},
    )


# ---DIV: Opening question---
def part_opening(b: CanvasBuilder) -> None:
    b.add_heading(
        [
            b.run("ORBIT", color=ORBIT_CYAN, bold=True, font_size=52),
            b.run(" IS A CONTINUOUS FALL", color=WHITE, bold=True, font_size=52),
        ],
        style={"width": 13.0, "margin-bottom": 0.45},
    )
    b.add_body(
        "A satellite is always falling toward Earth. The puzzle is why it never arrives.",
        style={"width": 10.8, "align": "center", "margin-bottom": 1.0},
    )
    b.add_flex_row(
        [
            card(b, "GRAVITY", "still pulls inward", ACCELERATION_CORAL),
            card(b, "VELOCITY", "carries it sideways", VELOCITY_GOLD),
            card(b, "CURVATURE", "Earth falls away below", EARTH_BLUE),
        ],
        gap=0.55,
        justify_content="center",
        style={"margin-bottom": 1.5},
    )


# ---DIV: Gravity is still present---
def part_gravity(b: CanvasBuilder) -> None:
    fraction = gravity_fraction()
    gravity = gravity_at_altitude()
    b.add_heading(
        "Weightless does not mean gravity-free",
        style={"width": 11.0, "margin-bottom": 0.45},
    )
    b.add_flex_row(
        [
            card(
                b,
                f"AT {ALTITUDE_KM:.0f} km",
                f"g ≈ {gravity:.2f} m/s²",
                EARTH_BLUE,
                width=4.1,
            ),
            card(
                b,
                "THAT IS",
                f"{100.0 * fraction:.0f}% of surface gravity",
                ACCELERATION_CORAL,
                width=4.5,
            ),
        ],
        gap=0.7,
        justify_content="center",
        style={"margin-bottom": 0.65},
    )
    b.add_body(
        "Astronauts float because spacecraft and occupants accelerate together in free fall.",
        style={"width": 10.7, "align": "center", "margin-bottom": 1.35},
    )


# ---DIV: Three controlled launches---
def part_launch_experiment(b: CanvasBuilder) -> None:
    trials = launch_trials()
    b.add_heading(
        "One launch point. Only the sideways speed changes.",
        style={"width": 12.4, "margin-bottom": 0.35},
    )
    b.add_body(
        "Normalized teaching view • altitude is exaggerated • drag is ignored",
        style={"width": 10.5, "align": "center", "margin-bottom": 0.55},
    )
    plot_id = b.add_data_plot(
        one_trial_plot_series("reentry"),
        id="launch_experiment",
        style=PLOT_STYLE,
        run_time=1.5,
        **PLOT_OPTIONS,
    )
    b.add_flex_row(
        [
            card(
                b,
                "TRIAL 1 · TOO SLOW",
                f"{trials[0]['speed_km_s']:.2f} km/s → intersects Earth",
                REENTRY_CORAL,
                width=5.0,
            ),
            card(
                b,
                "WHAT CHANGED?",
                "sideways distance before falling inward",
                SOFT,
                width=5.0,
            ),
        ],
        gap=0.65,
        justify_content="center",
        style={"margin-bottom": 0.8},
    )
    b.add_element_morph(
        plot_id,
        trial_plot_target("circular"),
        run_time=1.35,
    )
    b.add_flex_row(
        [
            card(
                b,
                "TRIAL 2 · CIRCULAR",
                f"{trials[1]['speed_km_s']:.2f} km/s → keeps missing",
                ORBIT_CYAN,
                width=5.0,
            ),
            card(
                b,
                "THE BALANCE",
                "the path bends as fast as Earth curves away",
                ORBIT_CYAN,
                width=5.0,
            ),
        ],
        gap=0.65,
        justify_content="center",
        style={"margin-bottom": 0.8},
    )
    b.add_element_morph(
        plot_id,
        trial_plot_target("escape"),
        run_time=1.35,
    )
    b.add_flex_row(
        [
            card(
                b,
                "TRIAL 3 · ESCAPE",
                f"{trials[2]['speed_km_s']:.2f} km/s → positive energy",
                ESCAPE_GOLD,
                width=5.0,
            ),
            card(
                b,
                "NOT JUST “HIGH”",
                "speed exceeds the local escape threshold",
                ESCAPE_GOLD,
                width=5.0,
            ),
        ],
        gap=0.65,
        justify_content="center",
        style={"margin-bottom": 1.5},
    )


# ---DIV: Compare the regimes---
def part_comparison(b: CanvasBuilder) -> None:
    b.add_heading(
        "The same gravity produces three different paths",
        style={"width": 11.8, "margin-bottom": 0.45},
    )
    comparison_id = b.add_data_plot(
        orbit_plot_series(),
        id="regime_comparison",
        style=PLOT_STYLE,
        run_time=1.5,
        **PLOT_OPTIONS,
    )
    b.add_flex_row(
        [
            card(b, "TOO SLOW", "re-entry", REENTRY_CORAL, width=3.35),
            card(b, "JUST RIGHT", "circular orbit", ORBIT_CYAN, width=3.35),
            card(b, "ESCAPE", "positive energy", ESCAPE_GOLD, width=3.35),
        ],
        gap=0.55,
        justify_content="center",
        style={"margin-bottom": 0.65},
    )
    b.add_state_transition(
        [
            {
                "target_id": f"{comparison_id}::series:reentry",
                "changes": {"stroke_width": 8},
            },
            {
                "target_id": f"{comparison_id}::series:circular",
                "changes": {"stroke_opacity": 0.22},
            },
            {
                "target_id": f"{comparison_id}::series:escape",
                "changes": {"stroke_opacity": 0.22},
            },
        ],
        run_time=0.8,
    )
    b.add_state_transition(
        [
            {
                "target_id": f"{comparison_id}::series:reentry",
                "changes": {"stroke_opacity": 0.22, "stroke_width": 4},
            },
            {
                "target_id": f"{comparison_id}::series:circular",
                "changes": {"stroke_opacity": 1.0, "stroke_width": 8},
            },
        ],
        run_time=0.8,
    )
    b.add_state_transition(
        [
            {
                "target_id": f"{comparison_id}::series:circular",
                "changes": {"stroke_opacity": 0.22, "stroke_width": 4},
            },
            {
                "target_id": f"{comparison_id}::series:escape",
                "changes": {"stroke_opacity": 1.0, "stroke_width": 8},
            },
        ],
        run_time=0.8,
    )
    b.add_state_transition(
        [
            {
                "target_id": f"{comparison_id}::series:reentry",
                "changes": {"stroke_opacity": 1.0},
            },
            {
                "target_id": f"{comparison_id}::series:circular",
                "changes": {"stroke_opacity": 1.0},
            },
        ],
        run_time=0.65,
    )


# ---DIV: Local vector geometry---
def part_vectors(b: CanvasBuilder) -> None:
    nodes, edges = local_vector_diagram()
    b.add_heading(
        "Freeze one instant on the circular path",
        style={"width": 11.0, "margin-bottom": 0.45},
    )
    vector_id = b.add_diagram(
        nodes,
        edges,
        id="orbital_vectors",
        style={"width": 8.4, "height": 4.35, "margin-bottom": 0.45},
        run_time=1.35,
    )
    b.add_state_transition(
        [
            {
                "target_id": f"{vector_id}::edge:velocity",
                "changes": {"stroke_width": 9, "stroke_color": VELOCITY_GOLD},
            },
            {
                "target_id": f"{vector_id}::edge:acceleration",
                "changes": {"stroke_opacity": 0.22},
            },
        ],
        run_time=0.75,
    )
    b.add_body(
        [
            b.run(
                "Velocity points tangent to the path.",
                color=VELOCITY_GOLD,
                bold=True,
            ),
        ],
        style={"width": 8.8, "align": "center", "margin-bottom": 0.35},
    )
    b.add_state_transition(
        [
            {
                "target_id": f"{vector_id}::edge:velocity",
                "changes": {"stroke_opacity": 0.22, "stroke_width": 6},
            },
            {
                "target_id": f"{vector_id}::edge:acceleration",
                "changes": {"stroke_opacity": 1.0, "stroke_width": 9},
            },
            {
                "target_id": f"{vector_id}::edge-label:acceleration",
                "changes": {"color": ACCELERATION_CORAL},
            },
        ],
        run_time=0.75,
    )
    b.add_body(
        [
            b.run(
                "Acceleration points inward. Here, gravity is the centripetal force.",
                color=ACCELERATION_CORAL,
                bold=True,
            ),
        ],
        style={"width": 10.1, "align": "center", "margin-bottom": 1.2},
    )


# ---DIV: Governing relationship---
def part_equation(b: CanvasBuilder) -> None:
    speed = circular_speed()
    b.add_heading(
        "Now the geometry becomes an equation",
        style={"width": 10.8, "margin-bottom": 0.75},
    )
    b.add_flex_row(
        [
            b.math_spec(
                r"\underbrace{\frac{GMm}{r^2}}_{\text{gravity inward}}",
                style={"width": 3.65, "height": 2.1},
            ),
            b.math_spec(
                r"=\underbrace{\frac{mv^2}{r}}_{\text{curved motion}}",
                style={"width": 3.65, "height": 2.1},
            ),
        ],
        gap=0.5,
        justify_content="center",
        style={"margin-bottom": 0.55},
    )
    b.add_math(
        r"v_{\mathrm{circular}}=\sqrt{\frac{GM}{r}}",
        id="circular_speed_law",
        style={"width": 7.2, "margin-bottom": 0.55},
        run_time=1.4,
    )
    b.add_camera_focus(
        "circular_speed_law",
        mode="isolate",
        zoom=1.55,
        hold_time=1.0,
        run_time=0.8,
        reset_run_time=0.65,
    )
    b.add_body(
        f"At {ALTITUDE_KM:.0f} km:  v ≈ {speed:.2f} km/s",
        style={"width": 8.0, "align": "center", "margin-bottom": 1.3},
    )


# ---DIV: Final synthesis---
def part_finale(b: CanvasBuilder) -> None:
    b.add_heading(
        [
            b.run("FALLING", color=ACCELERATION_CORAL, bold=True, font_size=48),
            b.run(" + ", color=MUTED, bold=True, font_size=48),
            b.run("MISSING", color=ORBIT_CYAN, bold=True, font_size=48),
        ],
        style={"width": 10.6, "margin-bottom": 0.5},
    )
    b.add_body(
        "Orbit is not a place where gravity stops.",
        style={"width": 9.4, "align": "center", "margin-bottom": 0.4},
    )
    b.add_body(
        "It is the motion of falling around Earth—again and again—without reaching the ground.",
        style={"width": 11.0, "align": "center", "margin-bottom": 1.2},
    )
    b.add_body(
        "INWARD GRAVITY  +  TANGENT VELOCITY\n=  CONTINUOUS FREE FALL",
        style={
            "width": 10.8,
            "align": "center",
            "margin-bottom": 0.4,
        },
    )


# ---DIV: Main scene---
class OrbitalMechanics(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(
            title="Why an Orbit Is a Continuous Fall",
            background_color=BG,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        part_opening(builder)
        part_gravity(builder)
        part_launch_experiment(builder)
        part_comparison(builder)
        part_vectors(builder)
        part_equation(builder)
        part_finale(builder)
        super().__init__(dsl=builder.build(), **kwargs)
