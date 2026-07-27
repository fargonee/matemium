"""Landscape economics flagship: a negative supply shock as a causal model."""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings, LayoutBox
from canvas.builder import CanvasBuilder

from .helpers import (
    ADAPT,
    BG,
    DEMAND,
    EQUILIBRIUM,
    MUTED,
    PERSIST,
    RECOVERY,
    SHOCK,
    SUPPLY,
    WHITE,
    assumptions_diagram,
    causal_chain,
    equilibrium_marker,
    market_series,
    price_paths,
    scenarios,
)

MARKET_OPTIONS = {
    "x_range": [0.0, 80.0, 10.0],
    "y_range": [20.0, 110.0, 10.0],
    "width": 9.8,
    "height": 4.5,
    "tips": False,
}


def market_target(name: str) -> CanvasElement:
    return CanvasElement(
        id=f"market_{name}",
        type="DataPlot",
        content={
            "series": market_series(name),
            "markers": equilibrium_marker(name),
            **MARKET_OPTIONS,
        },
        layout=LayoutBox(width=10.0, height=4.7, margin_bottom=0.5),
    )


def part_opening(b: CanvasBuilder) -> None:
    b.add_heading(
        [
            b.run("SUPPLY SHOCK", color=SHOCK, bold=True),
            b.run("  /  FOLLOW THE CAUSAL CHAIN", color=WHITE, bold=True),
        ],
        style={"width": 13.0, "margin-bottom": 0.4},
    )
    b.add_body(
        "A fictional grain market begins at P = 60 and Q = 40. Then productive capacity falls.",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.45},
    )
    nodes, edges = causal_chain()
    chain_id = b.add_diagram(
        nodes,
        edges,
        id="causal_chain",
        style={"width": 12.8, "height": 3.2, "margin-bottom": 0.45},
        run_time=1.5,
    )
    b.add_body(
        "HARVEST  →  AVAILABILITY  →  SUPPLY  →  EQUILIBRIUM  →  RESPONSE",
        style={"width": 12.2, "align": "center", "margin-bottom": 0.35},
    )
    b.add_body(
        "The graph will organize this mechanism. It will not replace institutions, timing, or human choices.",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.8},
    )


def part_baseline(b: CanvasBuilder) -> None:
    b.add_heading(
        "01  BASELINE: TWO RELATIONSHIPS, ONE INTERSECTION",
        style={"margin-top": 2.6, "margin-bottom": 0.65},
    )
    market_id = b.add_data_plot(
        market_series("baseline"),
        markers=equilibrium_marker("baseline"),
        id="market_model",
        style={"width": 10.0, "height": 4.7, "margin-bottom": 0.65},
        run_time=1.6,
        **MARKET_OPTIONS,
    )
    b.add_flex_row(
        [
            b.math_spec(r"P=100-Q", style={"width": 4.2}, run_time=1.0),
            b.math_spec(r"P=Q+20", style={"width": 4.2}, run_time=1.0),
            b.text_spec("E₀  P=60  Q=40", style={"width": 3.2}),
        ],
        gap=0.5,
        justify_content="center",
        style={"margin-bottom": 0.7},
    )


def part_shift(b: CanvasBuilder) -> None:
    b.add_heading(
        "02  CAPACITY LOSS SHIFTS SUPPLY",
        style={"margin-top": 2.6, "margin-bottom": 0.65},
    )
    shock_id = b.add_data_plot(
        market_series("baseline"),
        markers=equilibrium_marker("baseline"),
        id="shock_model",
        style={"width": 10.0, "height": 4.7, "margin-bottom": 0.55},
        run_time=1.5,
        **MARKET_OPTIONS,
    )
    b.add_element_morph(shock_id, market_target("shock"), run_time=1.2)
    b.add_state_transition(
        [
            {
                "target_id": f"{shock_id}::series:supply",
                "changes": {"stroke_color": SHOCK, "stroke_width": 10},
            },
            {
                "target_id": f"{shock_id}::marker:equilibrium",
                "changes": {"scale": 1.5},
            },
        ],
        run_time=0.9,
    )
    b.add_body(
        "SHIFT: less is offered at every price. MOVEMENT: the new intersection selects one point on the shifted curve.",
        style={"width": 12.2, "align": "center", "margin-bottom": 0.35},
    )
    b.add_math(
        r"P=Q+20\;\longrightarrow\;P=Q+40",
        style={"width": 8.4, "margin-bottom": 0.25},
        run_time=1.1,
    )
    b.add_body(
        "NEW EQUILIBRIUM  E₁:  P=70, Q=30",
        style={"width": 8.4, "align": "center", "margin-bottom": 0.7},
    )


def part_scenarios(b: CanvasBuilder) -> None:
    b.add_heading(
        "03  THE NEXT PATH DEPENDS ON ADJUSTMENT",
        style={"margin-top": 2.6, "margin-bottom": 0.65},
    )
    paths_id = b.add_data_plot(
        price_paths(),
        markers=[],
        id="price_paths",
        x_range=[0.0, 6.0, 1.0],
        y_range=[55.0, 75.0, 5.0],
        width=10.6,
        height=4.0,
        tips=False,
        style={"width": 10.8, "height": 4.2, "margin-bottom": 0.8},
        run_time=1.6,
    )
    for name, color in (
        ("quick_recovery", RECOVERY),
        ("persistent", PERSIST),
        ("adaptation", ADAPT),
    ):
        b.add_state_transition(
            [
                {
                    "target_id": f"{paths_id}::series:{name}",
                    "changes": {"stroke_color": color, "stroke_width": 10},
                }
            ],
            run_time=0.55,
        )
    b.add_body(
        "green quick recovery  ·  violet persistent disruption  ·  mint demand adaptation",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.45},
    )
    b.add_flex_row(
        [
            b.text_spec(
                f"{case['name']}\nP={case['price']:.0f}  Q={case['quantity']:.0f}",
                style={"width": 3.8},
            )
            for case in scenarios()
        ],
        gap=0.55,
        justify_content="center",
        style={"margin-bottom": 0.7},
    )


def part_boundary(b: CanvasBuilder) -> None:
    b.add_heading(
        "04  WHAT THE MODEL HOLDS STILL",
        style={"margin-top": 2.6, "margin-bottom": 0.45},
    )
    nodes, edges = assumptions_diagram()
    b.add_diagram(
        nodes,
        edges,
        id="model_boundary",
        style={"width": 11.5, "height": 4.5, "margin-bottom": 0.5},
        run_time=1.5,
    )
    b.add_body(
        "One product's relative price change is not the same claim as economy-wide inflation.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.75},
    )


def part_finale(b: CanvasBuilder) -> None:
    b.add_heading(
        "MODEL THE MECHANISM — NOT CERTAINTY",
        style={"margin-top": 2.6, "margin-bottom": 0.35},
    )
    b.add_body(
        "CAPACITY ↓  →  SUPPLY SHIFTS  →  P ↑, Q ↓  →  CHOICES ADAPT",
        id="market_chain",
        style={"width": 12.5, "align": "center", "margin-bottom": 0.55},
    )
    b.add_body(
        "Change the assumptions, and the path can change. The causal accounting must remain visible.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )
    b.add_camera_focus(
        "market_chain",
        mode="isolate",
        zoom=1.14,
        hold_time=0.9,
        run_time=0.65,
        reset_run_time=0.55,
    )


class SupplyShock(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(
            title="How a Supply Shock Moves Through a Market",
            background_color=BG,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        part_opening(builder)
        part_baseline(builder)
        part_shift(builder)
        part_scenarios(builder)
        part_boundary(builder)
        part_finale(builder)
        super().__init__(dsl=builder.build(), **kwargs)
