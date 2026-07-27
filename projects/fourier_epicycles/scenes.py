"""Fourier flagship: a mute, data-driven journey from rotation to reconstruction."""

from __future__ import annotations

from math import pi

from canvas import CanvasElement, CanvasScene, CanvasSettings, EntryAnimation
from canvas.builder import CanvasBuilder

from .helpers import (
    ACCENT,
    BACKGROUND,
    HARMONIC_COLORS,
    INK,
    epicycle_diagram_content,
    one_rotation_plot_content,
    reconstruction_plot_content,
    spectrum_plot_content,
    square_wave_terms,
)


def diagram_element(element_id: str, content: dict) -> CanvasElement:
    return CanvasElement(
        id=element_id,
        type="Diagram",
        content=content,
        entry_animation=EntryAnimation(type="Create", run_time=1.6),
    )


def plot_element(element_id: str, content: dict) -> CanvasElement:
    return CanvasElement(
        id=element_id,
        type="DataPlot",
        content=content,
        entry_animation=EntryAnimation(type="Create", run_time=1.6),
    )


def morph_diagram(
    builder: CanvasBuilder,
    element_id: str,
    content: dict,
    *,
    run_time: float = 0.75,
) -> None:
    builder.add_element_morph(
        element_id,
        CanvasElement(id=f"{element_id}_target", type="Diagram", content=content),
        run_time=run_time,
    )


def morph_plot(
    builder: CanvasBuilder,
    element_id: str,
    content: dict,
    *,
    run_time: float = 0.9,
) -> None:
    builder.add_element_morph(
        element_id,
        CanvasElement(id=f"{element_id}_target", type="DataPlot", content=content),
        run_time=run_time,
    )


# ---DIV: Opening challenge---
def part_opening(tape, builder: CanvasBuilder) -> None:
    tape.add_heading(
        [
            builder.run("FOURIER SERIES", color=HARMONIC_COLORS[0], bold=True),
            builder.run("  /  DRAWING WITH ROTATION", color=INK, bold=True),
        ],
        id="hero_title",
        style={"align": "center", "margin-bottom": 0.5},
    )
    tape.add_body(
        "How can perfectly smooth circles rebuild a signal with an abrupt edge?",
        id="hero_question",
        style={"width": 12.2, "align": "center", "margin-bottom": 0.7},
    )
    tape.add_data_plot(
        reconstruction_plot_content(9)["series"],
        markers=[],
        id="hero_wave",
        x_range=[-pi, pi, pi / 2],
        y_range=[-1.55, 1.55, 0.5],
        width=11.4,
        height=4.1,
        tips=False,
        style={"width": 11.4, "height": 4.1, "margin-bottom": 0.5},
        run_time=2.0,
    )
    tape.add_body(
        [
            builder.run("target", color="#52657A", bold=True),
            builder.run("  +  "),
            builder.run("9 rotating harmonics", color=ACCENT, bold=True),
        ],
        style={"width": 10.0, "align": "center"},
    )


# ---DIV: One rotation becomes one wave---
def part_one_rotation(tape, builder: CanvasBuilder) -> None:
    tape.add_heading(
        "01  ONE ROTATION BECOMES ONE WAVE",
        style={"margin-top": 3.0, "margin-bottom": 0.5},
    )
    tape.add_body(
        "Watch the vertical coordinate. The point turns at constant speed; its height rises and falls smoothly.",
        style={"width": 12.6, "margin-bottom": 0.55},
    )
    tape.add_flex_row(
        [
            builder.element_spec(
                diagram_element("one_circle", epicycle_diagram_content(0.0, term_count=1, scale=1.9)),
                style={"width": 4.5, "height": 4.1},
            ),
            builder.element_spec(
                plot_element("one_wave", one_rotation_plot_content(0.0)),
                style={"width": 8.4, "height": 4.1},
            ),
        ],
        gap=0.8,
        justify_content="center",
        style={"margin-bottom": 0.45},
    )
    for phase in (pi / 4, pi / 2, 3 * pi / 4, pi, 3 * pi / 2, 2 * pi):
        morph_diagram(
            builder,
            "one_circle",
            epicycle_diagram_content(phase, term_count=1, scale=1.9),
            run_time=0.55,
        )
        morph_plot(builder, "one_wave", one_rotation_plot_content(phase), run_time=0.55)
    builder.add_state_transition(
        [
            {
                "target_id": "one_circle::edge:vector_1",
                "changes": {"stroke_color": ACCENT, "stroke_width": 7.0},
            },
            {
                "target_id": "one_wave::series:sine",
                "changes": {"stroke_color": ACCENT, "stroke_width": 7.0},
            },
            {
                "target_id": "one_wave::marker:projection",
                "changes": {"scale": 1.45},
            },
        ],
        run_time=0.9,
        lag_ratio=0.08,
    )
    tape.add_flex_row(
        [
            builder.math_spec(
                r"y(t)=A\sin(\omega t+\phi)",
                style={"width": 6.2},
                run_time=1.2,
            ),
            builder.text_spec(
                [
                    builder.run("A", color=HARMONIC_COLORS[0], bold=True),
                    builder.run(" height   "),
                    builder.run("ω", color=HARMONIC_COLORS[1], bold=True),
                    builder.run(" speed   "),
                    builder.run("φ", color=HARMONIC_COLORS[2], bold=True),
                    builder.run(" starting angle"),
                ],
                style={"width": 6.4},
            ),
        ],
        gap=0.8,
        justify_content="center",
    )


# ---DIV: A spectrum is a recipe---
def part_spectrum(tape, builder: CanvasBuilder) -> None:
    terms = square_wave_terms(7)
    tape.add_heading(
        "02  THE SPECTRUM IS THE RECIPE",
        style={"margin-top": 3.0, "margin-bottom": 0.5},
    )
    tape.add_body(
        "A square wave uses odd frequencies. Faster circles are smaller, but each keeps a stable identity.",
        style={"width": 12.4, "margin-bottom": 0.4},
    )
    spectrum_id = tape.add_data_plot(
        spectrum_plot_content(7)["series"],
        id="spectrum",
        x_range=[0, 14, 2],
        y_range=[0, 1.45, 0.25],
        width=11.2,
        height=3.8,
        tips=False,
        smooth=False,
        style={"width": 11.2, "height": 3.8, "margin-bottom": 0.35},
        run_time=1.7,
    )
    builder.add_state_transition(
        [
            {
                "target_id": f"{spectrum_id}::series:h{int(term['harmonic'])}",
                "changes": {"stroke_width": 12.0, "scale": 1.04},
            }
            for term in terms[:5]
        ],
        run_time=1.1,
        lag_ratio=0.12,
    )
    tape.add_math(
        r"s_N(t)=\frac{4}{\pi}\sum_{k=0}^{N-1}\frac{\sin((2k+1)t)}{2k+1}",
        id="series_formula",
        style={"width": 10.8, "margin-bottom": 0.35},
        run_time=1.8,
    )
    tape.add_body(
        "Frequency says how fast. Amplitude says how much. Addition does the reconstruction.",
        style={"width": 11.6, "align": "center"},
    )


# ---DIV: Add the harmonics---
def part_reconstruction(tape, builder: CanvasBuilder) -> None:
    tape.add_heading(
        "03  ADD THE HARMONICS",
        style={"margin-top": 3.0, "margin-bottom": 0.5},
    )
    tape.add_body(
        "The quiet line is the target. The bright line is the current partial sum.",
        style={"width": 11.6, "margin-bottom": 0.4},
    )
    reconstruction_id = tape.add_data_plot(
        reconstruction_plot_content(1)["series"],
        id="reconstruction",
        x_range=[-pi, pi, pi / 2],
        y_range=[-1.55, 1.55, 0.5],
        width=11.5,
        height=4.5,
        tips=False,
        style={"width": 11.5, "height": 4.5, "margin-bottom": 0.25},
        run_time=1.8,
    )
    tape.add_math(
        r"N=1\quad\text{harmonic}",
        id="partial_formula",
        style={"width": 5.0},
        run_time=1.1,
    )
    for count in (2, 3, 5, 9):
        morph_plot(
            builder,
            reconstruction_id,
            reconstruction_plot_content(count),
            run_time=1.15,
        )
        builder.add_element_morph(
            "partial_formula",
            CanvasElement(
                id=f"formula_{count}",
                type="MathTex",
                content=rf"N={count}\quad\text{{harmonics}}",
            ),
            run_time=0.9,
            match_shapes=True,
        )
    builder.add_state_transition(
        [
            {
                "target_id": f"{reconstruction_id}::series:target",
                "changes": {"stroke_opacity": 0.35},
            },
            {
                "target_id": f"{reconstruction_id}::series:sum",
                "changes": {"stroke_width": 7.5},
            },
        ],
        run_time=0.9,
    )
    tape.add_body(
        "More high frequencies sharpen the transition while the broad smooth regions settle quickly.",
        style={"width": 12.0, "align": "center"},
    )


# ---DIV: Geometry and signal share one state---
def part_synchronized_views(tape, builder: CanvasBuilder) -> None:
    tape.add_heading(
        "04  ONE STATE, TWO VIEWS",
        style={"margin-top": 3.0, "margin-bottom": 0.5},
    )
    tape.add_body(
        "The chain endpoint and the bright plot marker are the same partial sum, seen geometrically and graphically.",
        style={"width": 12.6, "margin-bottom": 0.45},
    )
    start_phase = 0.12
    tape.add_flex_row(
        [
            builder.element_spec(
                diagram_element(
                    "epicycle_chain",
                    epicycle_diagram_content(start_phase, term_count=5, scale=1.55),
                ),
                style={"width": 5.2, "height": 4.6},
            ),
            builder.element_spec(
                plot_element(
                    "phase_plot",
                    reconstruction_plot_content(5, phase=start_phase),
                ),
                style={"width": 8.0, "height": 4.6},
            ),
        ],
        gap=0.65,
        justify_content="center",
        style={"margin-bottom": 0.45},
    )
    for phase in (0.42, 0.78, 1.15, 1.55, 2.05, 2.65):
        morph_diagram(
            builder,
            "epicycle_chain",
            epicycle_diagram_content(phase, term_count=5, scale=1.55),
            run_time=0.68,
        )
        morph_plot(
            builder,
            "phase_plot",
            reconstruction_plot_content(5, phase=phase),
            run_time=0.68,
        )
    builder.add_state_transition(
        [
            {
                "target_id": "epicycle_chain::node:tip_9",
                "changes": {"fill_color": ACCENT, "scale": 1.7},
            },
            {
                "target_id": "phase_plot::marker:phase",
                "changes": {"scale": 1.7},
            },
        ],
        run_time=0.85,
    )
    tape.add_body(
        "No representation is decorative: color and state bind circle, coefficient, and curve.",
        style={"width": 11.9, "align": "center"},
    )


# ---DIV: Gibbs phenomenon---
def part_gibbs(tape, builder: CanvasBuilder) -> None:
    tape.add_heading(
        "05  THE EDGE FIGHTS BACK",
        style={"margin-top": 3.0, "margin-bottom": 0.5},
    )
    tape.add_body(
        "Near a jump, extra terms squeeze the ringing into a narrower region—but the peak does not simply disappear.",
        style={"width": 12.4, "margin-bottom": 0.45},
    )
    detail_id = tape.add_data_plot(
        reconstruction_plot_content(3, detailed=True)["series"],
        id="gibbs_detail",
        x_range=[-0.8, 0.8, 0.4],
        y_range=[-1.55, 1.55, 0.5],
        width=11.3,
        height=4.4,
        tips=False,
        style={"width": 11.3, "height": 4.4, "margin-bottom": 0.35},
        run_time=1.7,
    )
    for count in (7, 15, 25):
        morph_plot(
            builder,
            detail_id,
            reconstruction_plot_content(count, detailed=True),
            run_time=1.05,
        )
    builder.add_camera_focus(
        detail_id,
        mode="overlay",
        zoom=1.85,
        hold_time=1.5,
        run_time=0.8,
        reset_run_time=0.7,
    )
    tape.add_flex_row(
        [
            builder.text_spec(
                "✓ transition narrows",
                style={"width": 5.5},
            ),
            builder.text_spec(
                "≠ uniform convergence at the jump",
                style={"width": 6.8},
            ),
        ],
        gap=0.7,
        justify_content="center",
    )


# ---DIV: Final synthesis---
def part_finale(tape, builder: CanvasBuilder) -> None:
    tape.add_heading(
        "COMPLEX BEHAVIOR. SIMPLE ROTATIONS.",
        id="final_title",
        style={"margin-top": 3.2, "align": "center", "margin-bottom": 0.55},
    )
    tape.add_flex_row(
        [
            builder.text_spec(
                "FREQUENCY\nchooses the speed",
                style={"width": 3.8},
            ),
            builder.text_spec(
                "AMPLITUDE\nchooses the size",
                style={"width": 3.8},
            ),
            builder.text_spec(
                "PHASE\nchooses the start",
                style={"width": 3.8},
            ),
        ],
        gap=0.65,
        justify_content="center",
        style={"margin-bottom": 0.7},
    )
    tape.add_math(
        r"\text{periodic signal}=\sum \text{simple rotating components}",
        style={"width": 11.5, "margin-bottom": 0.7},
        run_time=1.8,
    )
    tape.add_body(
        "Matemium  •  structured ideas in motion",
        style={"width": 10.0, "align": "center"},
    )
    builder.add_camera_focus(
        "final_title",
        mode="isolate",
        zoom=1.18,
        dim_opacity=0.05,
        hold_time=1.8,
        reset_zoom=False,
    )


# ---DIV: Main scene---
class FourierEpicycles(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(
            title="Fourier Series: Drawing With Rotating Circles",
            background_color=BACKGROUND,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        tape = builder.add_tape("main")
        part_opening(tape, builder)
        part_one_rotation(tape, builder)
        part_spectrum(tape, builder)
        part_reconstruction(tape, builder)
        part_synchronized_views(tape, builder)
        part_gibbs(tape, builder)
        part_finale(tape, builder)
        super().__init__(dsl=builder.build(), **kwargs)
