"""Flagship authoring pass: one event packaged by two languages."""

from __future__ import annotations

from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

from .helpers import MORPHEMES, SENTENCES


def part_meaning(tape, builder: CanvasBuilder) -> None:
    tape.add_heading("One event, more than one grammatical package", style={"align": "center"})
    tape.add_flex_row(
        [
            builder.text_spec("ACTOR\nstudent", style={"width": 3.0}),
            builder.text_spec("ACTION\nread", style={"width": 3.0}),
            builder.text_spec("OBJECT\nbook", style={"width": 3.0}),
            builder.text_spec("TIME\ntoday", style={"width": 3.0}),
        ]
    )
    tape.add_body("Begin with semantic roles so no language is treated as the default shape of thought.")


def part_sentences(tape, builder: CanvasBuilder) -> None:
    for sentence in SENTENCES:
        tape.add_heading(sentence["language"])
        tape.add_body(sentence["text"])
        tape.add_flex_row(
            [
                builder.text_spec(f"{role}\n{token}", style={"width": 3.1})
                for role, token in zip(sentence["roles"], sentence["tokens"])
            ],
            gap=0.25,
        )
        tape.add_body(sentence["note"])


def part_morphology(tape, builder: CanvasBuilder) -> None:
    tape.add_heading("A small ending can carry a large job")
    tape.add_flex_row(
        [builder.text_spec(f"{form}\n{meaning}", style={"width": 6.0}) for form, meaning in MORPHEMES],
        gap=0.6,
    )
    tape.add_body(
        "Literal position-by-position alignment fails: Uzbek packages object marking in -ni and usually "
        "places the verb last. Pronunciation must be reviewed and synchronized separately from spelling."
    )


def part_synthesis(tape) -> None:
    tape.add_heading("Structure changed; intended event remained")
    tape.add_body(
        "Grammar offers language-specific choices for packaging roles, emphasis, and timing. "
        "These examples are neutral sentences, not claims that either language has only one word order."
    )


class SentenceAcrossLanguages(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(title="How One Thought Changes Across Languages")
        builder = CanvasBuilder(canvas_settings=settings)
        tape = builder.add_tape("main")
        part_meaning(tape, builder)
        part_sentences(tape, builder)
        part_morphology(tape, builder)
        part_synthesis(tape)
        super().__init__(dsl=builder.build(), **kwargs)
