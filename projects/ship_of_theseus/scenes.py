"""Flagship authoring pass: Ship of Theseus argument map."""

from __future__ import annotations

from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

from .helpers import ACCOUNTS


def part_intuition(tape) -> None:
    tape.add_heading("When does a repaired object stop being the same object?", style={"align": "center"})
    tape.add_body(
        "Replace one damaged plank: identity seems continuous. Repeat until no original plank remains: "
        "the same intuition is now under pressure."
    )
    tape.add_math(r"S_0\rightarrow S_1\rightarrow\cdots\rightarrow S_n")


def part_rival(tape, builder: CanvasBuilder) -> None:
    tape.add_heading("Now rebuild the saved original planks")
    tape.add_flex_row(
        [
            builder.text_spec("A: continuously repaired\nworking ship", style={"width": 6.5}),
            builder.text_spec("B: reconstructed\noriginal material", style={"width": 6.5}),
        ],
        gap=0.6,
    )
    tape.add_body("Which is numerically the very same ship—not merely qualitatively similar to it?")


def part_map(tape, builder: CanvasBuilder) -> None:
    tape.add_heading("Four criteria, each tested by an objection")
    for account in ACCOUNTS:
        tape.add_flex_row(
            [
                builder.text_spec(account["criterion"], style={"width": 3.2}),
                builder.text_spec("SUPPORT\n" + account["supports"], style={"width": 5.0, "wrap": True}),
                builder.text_spec("OBJECTION\n" + account["objection"], style={"width": 5.0, "wrap": True}),
            ],
            gap=0.3,
        )


def part_transfer(tape) -> None:
    tape.add_heading("The structure travels")
    tape.add_body(
        "A repaired body, a long-lived organization, and a migrated digital file reproduce parts of the "
        "same conflict. The puzzle exposes a choice among matter, continuity, organization, and causal history."
    )


class ShipOfTheseus(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(title="The Ship of Theseus as an Argument Map")
        builder = CanvasBuilder(canvas_settings=settings)
        tape = builder.add_tape("main")
        part_intuition(tape)
        part_rival(tape, builder)
        part_map(tape, builder)
        part_transfer(tape)
        super().__init__(dsl=builder.build(), **kwargs)
