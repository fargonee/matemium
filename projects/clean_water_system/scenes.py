"""General-education flagship: a conventional multi-barrier water system."""

from __future__ import annotations

from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

from .helpers import (
    BG,
    BOUNDARY,
    CHALLENGES,
    CLEAN,
    CONTROL,
    DISTURBANCE,
    STAGES,
    disturbance_nodes,
    overview_network,
    stage_color,
    treatment_train,
)


def part_opening(b: CanvasBuilder) -> None:
    b.add_heading("WHAT STANDS BEHIND ONE GLASS OF CITY WATER?", style={"width": 12.6, "margin-bottom": 0.35})
    b.add_body(
        "Trace the tap backward: pipe network → pressure and pumping → storage → treatment plant → source.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.4},
    )
    nodes, edges = overview_network()
    b.add_diagram(
        nodes,
        edges,
        id="city_water_overview",
        style={"width": 13.2, "height": 3.6, "margin-bottom": 0.3},
        run_time=1.5,
    )
    b.add_body(
        "Safe delivery is a monitored system of barriers—not one magical filter.",
        style={"width": 11.5, "align": "center", "margin-bottom": 0.75},
    )


def part_challenges(b: CanvasBuilder) -> None:
    b.add_heading("01  “WHAT IS IN THE WATER?” HAS MORE THAN ONE ANSWER", style={"margin-top": 2.4, "margin-bottom": 0.35})
    b.add_flex_row(
        [
            b.text_spec(f"{title}\n{detail}", style={"width": 3.75, "wrap": True, "color": color})
            for title, detail, color in CHALLENGES
        ],
        gap=0.35,
        justify_content="center",
        style={"margin-bottom": 0.5},
    )
    b.add_body(
        "Clear-looking water is not evidence that every health risk has been controlled.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_train(b: CanvasBuilder) -> None:
    b.add_heading("02  A CONVENTIONAL SURFACE-WATER TREATMENT TRAIN", style={"margin-top": 2.4, "margin-bottom": 0.35})
    nodes, edges = treatment_train()
    train_id = b.add_diagram(
        nodes,
        edges,
        id="treatment_train",
        style={"width": 12.8, "height": 5.7, "margin-bottom": 0.35},
        run_time=1.7,
    )
    for stage in STAGES:
        target = f"{train_id}::node:{stage['id']}"
        b.add_state_transition([{"target_id": target, "changes": {"scale": 1.06}}], run_time=0.28)
        b.add_state_transition([{"target_id": target, "changes": {"scale": 1.0}}], run_time=0.18)
    b.add_body(
        "1  →  2  →  3  →  4  →  5  →  6  →  7  →  8",
        style={"width": 10.8, "align": "center", "margin-bottom": 0.18},
    )
    b.add_body(
        "Flow follows the numbered path. Real utilities choose and order processes according to source water, risk, infrastructure, and regulation.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_purposes(b: CanvasBuilder) -> None:
    b.add_heading("03  EACH STAGE HAS A DIFFERENT JOB", style={"margin-top": 2.4, "margin-bottom": 0.35})
    for stage in STAGES:
        b.add_body(
            [
                b.run(str(stage["name"]), color=stage_color(str(stage["kind"])), bold=True, font_size=28),
                b.run(f"   ·   {stage['purpose']}"),
            ],
            style={"width": 12.0, "align": "left", "margin-bottom": 0.16},
        )
    b.add_body(
        "No stage shown here removes every possible contaminant.",
        style={"width": 11.5, "align": "center", "margin-bottom": 0.7},
    )


def part_monitoring(b: CanvasBuilder) -> None:
    b.add_heading("04  MONITORING TURNS A READING INTO A CHECKED RESPONSE", style={"margin-top": 2.4, "margin-bottom": 0.35})
    response_id = b.add_diagram(
        disturbance_nodes(),
        [],
        id="monitoring_response",
        style={"width": 12.4, "height": 3.4, "margin-bottom": 0.3},
        run_time=1.4,
    )
    for index in range(len(DISTURBANCE)):
        b.add_state_transition(
            [{"target_id": f"{response_id}::node:response_{index}", "changes": {"scale": 1.07}}],
            run_time=0.35,
        )
        b.add_state_transition(
            [{"target_id": f"{response_id}::node:response_{index}", "changes": {"scale": 1.0}}],
            run_time=0.2,
        )
    b.add_body(
        "A changed reading is not an automatic chemical command. Instruments, context, procedures, operator judgment, and confirmation all matter.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_boundaries(b: CanvasBuilder) -> None:
    b.add_heading("05  KEEP THE SYSTEM BOUNDARIES HONEST", style={"margin-top": 2.4, "margin-bottom": 0.35})
    b.add_flex_row(
        [
            b.text_spec(
                "DRINKING WATER\nSource → treatment → storage → distribution → tap",
                style={"width": 5.7, "wrap": True, "color": CLEAN},
            ),
            b.text_spec(
                "WASTEWATER\nCollection and treatment after use form a separate downstream system",
                style={"width": 5.7, "wrap": True, "color": BOUNDARY},
            ),
        ],
        gap=0.45,
        justify_content="center",
        style={"margin-bottom": 0.45},
    )
    b.add_body(
        "This is an educational system model—not household treatment advice, a plant design, or proof that any particular water is safe.",
        id="water_boundary",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.65},
    )
    b.add_camera_focus(
        "water_boundary",
        mode="isolate",
        zoom=1.12,
        hold_time=0.9,
        run_time=0.6,
        reset_run_time=0.5,
    )


class CleanWaterSystem(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(
            title="How a City Gets Clean Water",
            background_color=BG,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        part_opening(builder)
        part_challenges(builder)
        part_train(builder)
        part_purposes(builder)
        part_monitoring(builder)
        part_boundaries(builder)
        super().__init__(dsl=builder.build(), **kwargs)
