"""Cinematic engineering flagship: feedback as measured correction in motion.

One deterministic vehicle world persists while isolated tapes inspect its
signals, loop structure, and response history.  World and tapes share authored
simulation snapshots; the project does not claim an engine-level reactive clock.
"""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings, LayoutBox
from canvas.builder import CanvasBuilder

from .helpers import (
    BG,
    COMMAND,
    DISTURBANCE,
    ERROR,
    MEASURED,
    MUTED,
    TARGET,
    TARGET_SPEED,
    TUNINGS,
    WHITE,
    control_loop_diagram,
    response_series,
    sample_near,
    simulate,
    vehicle_world_state,
)

WORLD_ID = "feedback_vehicle_world"
PLOT_OPTIONS = {
    "x_range": [0.0, 20.0, 5.0],
    "y_range": [17.0, 27.0, 2.0],
    "width": 9.4,
    "height": 3.25,
    "tips": False,
}


def state_sample(time: float, *, feedback: bool = True, tuning: str = "balanced"):
    gains = TUNINGS[tuning]
    return sample_near(
        simulate(float(gains["kp"]), float(gains["ki"]), feedback=feedback),
        time,
    )


def car_position(time: float) -> tuple[float, float, float]:
    # Camera target offsets match the deterministic world path in helpers.py.
    x = -4.0 + 0.4 * time
    start, end = -2.8, 1.25
    if x <= start:
        y = -0.8
    elif x >= end:
        y = 0.75
    else:
        u = (x - start) / (end - start)
        y = -0.8 + 1.55 * u * u * (3.0 - 2.0 * u)
    return (x, 0.0, y + 0.94)


def world_target(
    time: float,
    *,
    feedback: bool = True,
    tuning: str = "balanced",
    stage: str = "overview",
):
    return CanvasElement(
        id=WORLD_ID,
        type="FeedbackVehicleWorld",
        content=vehicle_world_state(time, feedback=feedback, tuning=tuning, stage=stage),
        auto_focus=False,
    )


def response_markers(time: float, *, feedback: bool = True, tuning: str = "balanced"):
    sample = state_sample(time, feedback=feedback, tuning=tuning)
    return [
        {
            "id": "now",
            "point": [sample["time"], sample["speed"]],
            "color": WHITE,
            "radius": 0.11,
        }
    ]


def response_target(time: float) -> CanvasElement:
    return CanvasElement(
        id="live_response",
        type="DataPlot",
        content={
            "series": [
                item
                for item in response_series(active="balanced")
                if item["id"] in {"target", "hill", "balanced"}
            ],
            "markers": response_markers(time),
            **PLOT_OPTIONS,
        },
        layout=LayoutBox(width=9.8, height=3.65, margin_bottom=0.2),
    )


def metric(b: CanvasBuilder, label: str, value: str, color: str) -> dict:
    return b.text_spec(
        [
            b.run(f"{label}\n", color=color, bold=True, font_size=23),
            b.run(value, color=WHITE, font_size=25),
        ],
        style={"width": 2.25, "height": 1.0, "align": "center"},
    )


def author_principle(b: CanvasBuilder, tape) -> None:
    tape.add_heading(
        [b.run("A HILL CHANGES THE CAR", color=DISTURBANCE, bold=True, font_size=34)],
        style={"width": 10.4, "margin-bottom": 0.18},
    )
    tape.add_heading(
        [b.run("FEEDBACK CHANGES THE RESPONSE", color=COMMAND, bold=True, font_size=34)],
        style={"width": 10.4, "margin-bottom": 0.42},
    )
    tape.add_body(
        "Target speed stays fixed. Measurement decides whether the command must change.",
        style={"width": 9.6, "align": "center", "margin-bottom": 0.2},
    )


def author_dashboard(b: CanvasBuilder, tape, *, time: float, feedback: bool) -> None:
    sample = state_sample(time, feedback=feedback)
    title = "OPEN LOOP · NOTHING MEASURES THE LOSS" if not feedback else "CLOSED LOOP · ONE CORRECTION"
    tape.add_heading(title, style={"width": 10.2, "margin-bottom": 0.32})
    tape.add_flex_row(
        [
            metric(b, "TARGET", f"{TARGET_SPEED:.2f} m/s", TARGET),
            metric(b, "MEASURED", f"{sample['speed']:.2f} m/s", MEASURED),
            metric(b, "ERROR", f"{sample['error']:.2f} m/s", ERROR),
            metric(b, "COMMAND", f"{sample['command']:.2f}", COMMAND if feedback else MUTED),
        ],
        gap=0.24,
        justify_content="center",
        style={"margin-bottom": 0.28},
    )
    tape.add_body(
        (
            "The fixed command cannot react to an unmeasured hill load."
            if not feedback
            else "Measurement creates error; PI action raises the actuator command."
        ),
        style={"width": 9.4, "align": "center", "margin-bottom": 0.18},
    )


def author_loop(b: CanvasBuilder, tape) -> None:
    tape.add_heading("THE LOOP KEEPS ASKING AGAIN", style={"width": 10.8, "margin-bottom": 0.48})
    nodes, edges = control_loop_diagram()
    loop_id = tape.add_diagram(
        nodes,
        edges,
        id="control_loop",
        style={"width": 10.7, "height": 3.45, "margin-bottom": 0.18},
        run_time=1.25,
    )
    for edge_id, color in (
        ("output", MEASURED),
        ("feedback", MEASURED),
        ("error", ERROR),
        ("command", COMMAND),
        ("drive", COMMAND),
    ):
        tape.add_state_transition(
            [{"target_id": f"{loop_id}::edge:{edge_id}", "changes": {"stroke_color": color, "stroke_width": 5}}],
            run_time=0.32,
        )


def author_response(b: CanvasBuilder, tape) -> str:
    tape.add_heading("THE PHYSICAL RECOVERY HAS A TIME HISTORY", style={"width": 10.8, "margin-bottom": 0.25})
    plot_id = tape.add_data_plot(
        [
            item
            for item in response_series(active="balanced")
            if item["id"] in {"target", "hill", "balanced"}
        ],
        markers=response_markers(6.0),
        id="live_response",
        style={"width": 9.8, "height": 3.65, "margin-bottom": 0.2},
        run_time=1.2,
        **PLOT_OPTIONS,
    )
    tape.add_body(
        [
            b.run("gold target", color=TARGET, bold=True, font_size=20),
            b.run("  ·  "),
            b.run("orange disturbance", color=DISTURBANCE, bold=True, font_size=20),
            b.run("  ·  "),
            b.run("mint response", color=COMMAND, bold=True, font_size=20),
        ],
        style={"width": 9.4, "align": "center", "margin-bottom": 0.12},
    )
    return plot_id


def author_comparison(b: CanvasBuilder, tape) -> None:
    tape.add_heading("SAME HILL · FOUR CONTROL CHOICES", style={"width": 10.6, "margin-bottom": 0.25})
    tape.add_data_plot(
        response_series(),
        markers=[],
        id="tuning_comparison",
        style={"width": 9.8, "height": 3.65, "margin-bottom": 0.18},
        run_time=1.2,
        **PLOT_OPTIONS,
    )
    tape.add_body(
        [
            b.run("slow", color=str(TUNINGS["slow"]["color"]), bold=True),
            b.run("  ·  "),
            b.run("balanced", color=COMMAND, bold=True),
            b.run("  ·  "),
            b.run("aggressive", color=ERROR, bold=True),
            b.run("  ·  "),
            b.run("open loop", color="#9a6cff", bold=True),
        ],
        style={"width": 9.5, "align": "center", "margin-bottom": 0.12},
    )


def author_finale(b: CanvasBuilder, tape) -> None:
    tape.add_heading(
        [b.run("STABILITY IS A LOOP", color=WHITE, bold=True, font_size=37)],
        style={"width": 10.2, "margin-bottom": 0.18},
    )
    tape.add_heading(
        [b.run("NOT A ONE-TIME COMMAND", color=COMMAND, bold=True, font_size=37)],
        style={"width": 10.2, "margin-bottom": 0.42},
    )
    tape.add_body(
        [
            b.run("MEASURE", color=MEASURED, bold=True, font_size=30),
            b.run("  →  "),
            b.run("COMPARE", color=ERROR, bold=True, font_size=30),
            b.run("  →  "),
            b.run("CORRECT", color=COMMAND, bold=True, font_size=30),
            b.run("  →  REPEAT", color=TARGET, bold=True, font_size=30),
        ],
        style={"width": 10.8, "align": "center", "margin-bottom": 0.15},
    )


def build_production() -> CanvasBuilder:
    b = CanvasBuilder(
        canvas_settings=CanvasSettings.for_youtube(
            title="How Feedback Stabilizes a System",
            background_color=BG,
        )
    )
    principle = b.add_tape("principle", frame_width=11.6, frame_height=5.4)
    open_dashboard = b.add_tape("open_dashboard", frame_width=11.6, frame_height=5.2)
    loop = b.add_tape("control_loop", frame_width=11.8, frame_height=5.6)
    closed_dashboard = b.add_tape("closed_dashboard", frame_width=11.6, frame_height=5.2)
    response = b.add_tape("response", frame_width=11.8, frame_height=5.7)
    comparison = b.add_tape("comparison", frame_width=11.8, frame_height=5.7)
    finale = b.add_tape("finale", frame_width=11.6, frame_height=5.2)

    b.add_object(
        "FeedbackVehicleWorld",
        id=WORLD_ID,
        content=vehicle_world_state(0.0, feedback=True, stage="overview"),
    )
    start = car_position(0.0)
    b.add_camera_inspect(
        WORLD_ID,
        path=[
            b.inspect_shot(phi=67, theta=-72, zoom=0.72, target_offset=(0.0, 0.0, 0.0), run_time=1.5, hold=0.5),
            b.inspect_shot(phi=76, theta=-90, zoom=1.55, target_offset=start, run_time=2.0, hold=0.8),
        ],
        return_to_sheet=False,
    )
    author_principle(b, principle)

    # The same road disturbance is first observed with no feedback.
    open_time = 6.0
    b.add_element_morph(
        WORLD_ID,
        world_target(open_time, feedback=False, stage="disturbance"),
        run_time=1.7,
    )
    open_pos = car_position(open_time)
    b.add_camera_inspect(
        WORLD_ID,
        path=[
            b.inspect_shot(phi=74, theta=-92, zoom=1.48, target_offset=open_pos, run_time=1.6, hold=0.7),
            b.inspect_shot(phi=66, theta=-68, zoom=1.38, target_offset=open_pos, run_time=2.0, hold=0.9),
        ],
        return_to_sheet=False,
    )
    author_dashboard(b, open_dashboard, time=open_time, feedback=False)
    author_loop(b, loop)

    # Close the loop at the identical physical time and road position. Only the
    # controller state, speed, error, and command differ.
    b.add_element_morph(
        WORLD_ID,
        world_target(open_time, feedback=True, stage="measurement"),
        run_time=1.5,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=75, theta=-88, zoom=1.52, target_offset=open_pos, run_time=1.7, hold=1.0)],
        return_to_sheet=False,
    )
    author_dashboard(b, closed_dashboard, time=open_time, feedback=True)
    b.add_element_morph(
        WORLD_ID,
        world_target(open_time, feedback=True, stage="correction"),
        run_time=1.2,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=69, theta=-76, zoom=1.50, target_offset=open_pos, run_time=1.4, hold=0.8)],
        return_to_sheet=False,
    )
    response_plot_id = author_response(b, response)

    # Advance the deterministic state: car motion, measured speed, command,
    # and response cursor all come from the same authored time.
    recovered_time = 14.0
    b.add_element_morph(
        WORLD_ID,
        world_target(recovered_time, feedback=True, stage="recovery"),
        run_time=2.2,
    )
    recovered_pos = car_position(recovered_time)
    b.add_camera_inspect(
        WORLD_ID,
        path=[
            b.inspect_shot(phi=75, theta=-92, zoom=1.42, target_offset=recovered_pos, run_time=1.7, hold=0.65),
            b.inspect_shot(phi=64, theta=-70, zoom=0.76, target_offset=(0.0, 0.0, 0.1), run_time=2.3, hold=1.0),
        ],
        return_to_sheet=False,
    )
    response.add_element_morph(response_plot_id, response_target(recovered_time), run_time=1.0)
    response.add_body(
        "The hill remains. Error shrinks because the controller changed the input.",
        style={"width": 9.4, "align": "center", "margin-bottom": 0.12},
    )
    author_comparison(b, comparison)

    b.add_element_morph(
        WORLD_ID,
        world_target(20.0, feedback=True, stage="recovery"),
        run_time=1.7,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=66, theta=-72, zoom=0.72, target_offset=(0.0, 0.0, 0.15), run_time=2.0, hold=1.0)],
        return_to_sheet=False,
    )
    author_finale(b, finale)
    return b


class FeedbackControl(CanvasScene):
    def __init__(self, **kwargs):
        super().__init__(dsl=build_production().build(), **kwargs)
