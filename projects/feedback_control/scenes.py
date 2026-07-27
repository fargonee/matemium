"""Landscape engineering flagship: feedback as measured correction."""

from __future__ import annotations

from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

from .helpers import (
    BG,
    COMMAND,
    DISTURBANCE,
    ERROR,
    MEASURED,
    TARGET,
    TUNINGS,
    WHITE,
    control_loop_diagram,
    correction_cards,
    one_response_series,
    physical_hill_diagram,
    response_series,
    sample_near,
    simulate,
)

PLOT_OPTIONS = {
    "x_range": [0.0, 20.0, 5.0],
    "y_range": [17.0, 27.0, 1.0],
    "width": 10.8,
    "height": 3.7,
    "tips": False,
}


def part_opening(b: CanvasBuilder) -> None:
    b.add_heading(
        [
            b.run("FEEDBACK", color=COMMAND, bold=True),
            b.run("  /  MEASURE, COMPARE, CORRECT", color=WHITE, bold=True),
        ],
        style={"width": 13.2, "margin-bottom": 0.4},
    )
    b.add_body(
        "The target stays at 25 m/s. The road changes underneath the car.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.4},
    )
    nodes, edges = physical_hill_diagram()
    b.add_diagram(
        nodes,
        edges,
        id="physical_hill",
        style={"width": 11.8, "height": 4.1, "margin-bottom": 0.45},
        run_time=1.5,
    )
    b.add_body(
        "Open loop: the same command cannot respond to an unmeasured disturbance.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.8},
    )


def part_loop(b: CanvasBuilder) -> None:
    b.add_heading(
        "01  CLOSE THE LOOP",
        style={"margin-top": 2.6, "margin-bottom": 0.35},
    )
    nodes, edges = control_loop_diagram()
    loop_id = b.add_diagram(
        nodes,
        edges,
        id="control_loop",
        style={"width": 12.8, "height": 5.2, "margin-bottom": 0.4},
        run_time=1.6,
    )
    for edge_id, color in (
        ("output", MEASURED),
        ("feedback", MEASURED),
        ("error", ERROR),
        ("command", COMMAND),
        ("drive", COMMAND),
    ):
        b.add_state_transition(
            [
                {
                    "target_id": f"{loop_id}::edge:{edge_id}",
                    "changes": {"stroke_color": color, "stroke_width": 10},
                }
            ],
            run_time=0.45,
        )
    b.add_math(
        r"e(t)=r(t)-y(t)",
        style={"width": 6.5, "margin-bottom": 0.25},
        run_time=1.1,
    )
    b.add_body(
        "Measure speed → compute error → change throttle → measure again.",
        style={"width": 11.6, "align": "center", "margin-bottom": 0.7},
    )


def part_one_correction(b: CanvasBuilder) -> None:
    tuning = TUNINGS["balanced"]
    sample = sample_near(
        simulate(float(tuning["kp"]), float(tuning["ki"])),
        4.5,
    )
    b.add_heading(
        "02  FOLLOW ONE CORRECTION",
        style={"margin-top": 2.6, "margin-bottom": 0.35},
    )
    nodes, edges = correction_cards(sample)
    b.add_diagram(
        nodes,
        edges,
        id="one_correction",
        style={"width": 11.5, "height": 2.2, "margin-bottom": 0.65},
        run_time=1.3,
    )
    b.add_body(
        "The disturbance is not removed. The controller changes the input until measured output returns to target.",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.65},
    )


def part_recovery(b: CanvasBuilder) -> None:
    b.add_heading(
        "03  RECOVERY IS A TIME HISTORY",
        style={"margin-top": 2.6, "margin-bottom": 0.8},
    )
    balanced_id = b.add_data_plot(
        one_response_series("balanced"),
        markers=[],
        id="balanced_response",
        style={"width": 11.0, "height": 4.0, "margin-bottom": 0.9},
        run_time=1.6,
        **PLOT_OPTIONS,
    )
    b.add_state_transition(
        [
            {
                "target_id": f"{balanced_id}::series:balanced",
                "changes": {"stroke_color": COMMAND, "stroke_width": 9},
            },
            {
                "target_id": f"{balanced_id}::series:hill",
                "changes": {"stroke_color": DISTURBANCE, "stroke_width": 7},
            },
        ],
        run_time=0.9,
    )
    b.add_body(
        "Orange: hill begins at 3 s. Gold: target. Mint: balanced closed-loop response.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_tuning(b: CanvasBuilder) -> None:
    b.add_heading(
        "04  TUNING CHANGES THE SHAPE",
        style={"margin-top": 2.6, "margin-bottom": 0.8},
    )
    tuning_id = b.add_data_plot(
        response_series(),
        markers=[],
        id="tuning_plot",
        style={"width": 11.0, "height": 4.0, "margin-bottom": 0.9},
        run_time=1.6,
        **PLOT_OPTIONS,
    )
    for name in ("slow", "balanced", "aggressive", "open"):
        b.add_state_transition(
            [
                {
                    "target_id": f"{tuning_id}::series:{name}",
                    "changes": {"stroke_width": 9},
                }
            ],
            run_time=0.55,
        )
    b.add_body(
        "gray slow  ·  mint balanced  ·  red aggressive  ·  violet open loop",
        style={"width": 12.6, "align": "center", "margin-bottom": 0.55},
    )
    b.add_math(
        r"u(t)=K_p e(t)+K_i\int e(t)\,dt",
        style={"width": 8.0, "margin-bottom": 0.65},
        run_time=1.3,
    )


def part_finale(b: CanvasBuilder) -> None:
    b.add_heading(
        "STABILITY IS NOT A ONE-TIME COMMAND",
        style={"margin-top": 2.6, "margin-bottom": 0.35},
    )
    b.add_body(
        [
            b.run("MEASURE", color=MEASURED, bold=True, font_size=38),
            b.run("  →  "),
            b.run("COMPARE", color=ERROR, bold=True, font_size=38),
            b.run("  →  "),
            b.run("CORRECT", color=COMMAND, bold=True, font_size=38),
            b.run("  →  REPEAT", color=TARGET, bold=True, font_size=38),
        ],
        id="feedback_cycle",
        style={"width": 13.0, "align": "center", "margin-bottom": 0.55},
    )
    b.add_body(
        "Cruise control is one example. The same loop language describes temperature, motion, voltage, and process control.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )
    b.add_camera_focus(
        "feedback_cycle",
        mode="isolate",
        zoom=1.18,
        hold_time=0.9,
        run_time=0.65,
        reset_run_time=0.55,
    )


class FeedbackControl(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(
            title="How Feedback Stabilizes a System",
            background_color=BG,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        part_opening(builder)
        part_loop(builder)
        part_one_correction(builder)
        part_recovery(builder)
        part_tuning(builder)
        part_finale(builder)
        super().__init__(dsl=builder.build(), **kwargs)
