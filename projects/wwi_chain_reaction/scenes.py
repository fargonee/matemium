"""History flagship: the July Crisis as chronology, network, and causation."""

from __future__ import annotations

from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

from .helpers import (
    ALTERNATIVE,
    BG,
    CAUSAL_LAYERS,
    CONTINGENCIES,
    EVENTS,
    decision_network,
    event_color,
    geography_nodes,
)


def part_opening(b: CanvasBuilder) -> None:
    b.add_heading(
        "HOW DID A REGIONAL CRISIS BECOME A EUROPEAN WAR?",
        style={"width": 12.5, "margin-bottom": 0.35},
    )
    b.add_body(
        "The Sarajevo assassination was a trigger inside an already tense system. Alliances constrained choices; they did not operate as automatic dominoes.",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.45},
    )
    b.add_flex_row(
        [
            b.text_spec("28 JUNE\nREGIONAL TRIGGER", style={"width": 3.4}),
            b.text_spec("JULY\nDECISIONS + DEADLINES", style={"width": 3.8}),
            b.text_spec("4 AUGUST\nEUROPEAN WAR", style={"width": 3.4}),
        ],
        gap=0.45,
        justify_content="center",
        style={"margin-bottom": 0.7},
    )


def part_timeline(b: CanvasBuilder) -> None:
    b.add_heading("01  THIRTY-EIGHT DAYS OF CHOICES", style={"margin-top": 2.4, "margin-bottom": 0.45})
    for event in EVENTS:
        color = event_color(str(event["kind"]))
        b.add_body(
            [
                b.run(str(event["date"]), color=color, bold=True),
                b.run(f"  ·  {str(event['place']).upper()}  ·  {event['event']}"),
            ],
            style={"width": 12.0, "align": "left", "margin-bottom": 0.14},
        )
    b.add_body(
        "Evidence key: red = trigger · gold = diplomatic decision · violet = mobilization · orange = declaration or invasion",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.7},
    )


def part_network(b: CanvasBuilder) -> None:
    b.add_heading("02  RELATIONSHIPS SHAPED — BUT DID NOT REPLACE — DECISIONS", style={"margin-top": 2.4, "margin-bottom": 0.45})
    nodes, edges = decision_network()
    b.add_diagram(
        nodes,
        edges,
        id="decision_network",
        style={"width": 11.8, "height": 5.1, "margin-bottom": 0.35},
        run_time=1.5,
    )
    b.add_body(
        "GERMANY → AUSTRIA-HUNGARY: backing  ·  AUSTRIA-HUNGARY → SERBIA: ultimatum  ·  RUSSIA → SERBIA: support",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.18},
    )
    b.add_body(
        "GERMANY → BELGIUM: western plan  ·  BELGIAN NEUTRALITY → BRITAIN: entry decision  ·  FRANCE ↔ RUSSIA: alignment",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.18},
    )
    b.add_body(
        "Selected relationships only. This is a decision network, not a complete alliance chart.",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.7},
    )


def part_geography(b: CanvasBuilder) -> None:
    b.add_heading("03  THE CRISIS WIDENED ACROSS CONNECTED PLACES", style={"margin-top": 2.4, "margin-bottom": 0.45})
    b.add_diagram(
        geography_nodes(),
        [],
        id="schematic_geography",
        style={"width": 11.5, "height": 4.7, "margin-bottom": 0.35},
        run_time=1.3,
    )
    b.add_body(
        "SCHEMATIC RELATIVE GEOGRAPHY — not a 1914 border map. Sarajevo and Belgrade anchor the Balkan crisis; decisions in Vienna, Berlin, St Petersburg, Paris, Belgium, and London widen it.",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.7},
    )


def part_contingency(b: CanvasBuilder) -> None:
    b.add_heading("04  THREE PLACES WHERE “AUTOMATIC” FAILS", style={"margin-top": 2.4, "margin-bottom": 0.45})
    b.add_flex_row(
        [
            b.text_spec(f"{title}\n{detail}", style={"width": 3.9, "wrap": True})
            for title, detail in CONTINGENCIES
        ],
        gap=0.4,
        justify_content="center",
        style={"margin-bottom": 0.65},
    )


def part_causes(b: CanvasBuilder) -> None:
    b.add_heading("05  CAUSE HAS LAYERS", style={"margin-top": 2.4, "margin-bottom": 0.45})
    b.add_flex_row(
        [
            b.text_spec(f"{name}\n{description}", style={"width": 2.9, "color": color, "wrap": True})
            for name, description, color in CAUSAL_LAYERS
        ],
        gap=0.35,
        justify_content="center",
        style={"margin-bottom": 0.45},
    )
    b.add_body(
        "Chronology establishes order. Networks show relationships. Geography shows widening. Causal interpretation connects them without pretending that one layer is the whole explanation.",
        id="history_synthesis",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )
    b.add_camera_focus(
        "history_synthesis",
        mode="isolate",
        zoom=1.1,
        hold_time=0.8,
        run_time=0.6,
        reset_run_time=0.5,
    )


class WWIChainReaction(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(
            title="The Chain Reaction That Began World War I",
            background_color=BG,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        part_opening(builder)
        part_timeline(builder)
        part_network(builder)
        part_geography(builder)
        part_contingency(builder)
        part_causes(builder)
        super().__init__(dsl=builder.build(), **kwargs)
