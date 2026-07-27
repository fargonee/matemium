"""Flagship authoring pass: the July Crisis as chronology plus decisions."""

from __future__ import annotations

from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

from .helpers import CAUSAL_LAYERS, EVENTS


def part_before(tape) -> None:
    tape.add_heading("How did a regional crisis become a European war?", style={"align": "center"})
    tape.add_body(
        "The assassination at Sarajevo was a trigger inside an already tense system. Alliances mattered, "
        "but they did not operate as automatic dominoes."
    )


def part_timeline(tape, builder: CanvasBuilder) -> None:
    tape.add_heading("Thirty-eight days of choices and deadlines")
    for date, place, event in EVENTS:
        tape.add_flex_row(
            [
                builder.text_spec(date, style={"width": 2.0}),
                builder.text_spec(place, style={"width": 3.0}),
                builder.text_spec(event, style={"width": 9.0, "wrap": True}),
            ],
            gap=0.25,
            style={"margin-bottom": 0.18},
        )


def part_causes(tape, builder: CanvasBuilder) -> None:
    tape.add_heading("Cause has layers, not one total explanation")
    tape.add_flex_column(
        [
            builder.text_spec(f"{name.upper()}: {description}")
            for name, description in CAUSAL_LAYERS.items()
        ],
        gap=0.3,
        align_items="start",
    )
    tape.add_body(
        "Alternatives still existed around the ultimatum, partial mobilization, and mediation proposals. "
        "Mobilization plans made delay appear dangerous, but leaders still made consequential decisions."
    )


def part_synthesis(tape) -> None:
    tape.add_heading("From Balkan conflict to multiple fronts")
    tape.add_body(
        "Chronology shows what happened; a decision network shows who knew and chose what; geography shows "
        "how declarations and plans widened the conflict. Interpretation begins where the evidence is connected."
    )


class WWIChainReaction(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(title="The Chain Reaction That Began World War I")
        builder = CanvasBuilder(canvas_settings=settings)
        tape = builder.add_tape("main")
        part_before(tape)
        part_timeline(tape, builder)
        part_causes(tape, builder)
        part_synthesis(tape)
        super().__init__(dsl=builder.build(), **kwargs)
