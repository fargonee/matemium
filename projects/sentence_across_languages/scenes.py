"""Language-learning flagship: stable meaning, reordered grammar."""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings, LayoutBox
from canvas.builder import CanvasBuilder

from .helpers import (
    BG,
    MARKER,
    MORPHEMES,
    MUTED,
    SENTENCES,
    contrast_nodes,
    meaning_nodes,
    reading_nodes,
    sentence_nodes,
)


def sentence_target(language: str) -> CanvasElement:
    return CanvasElement(
        id=f"{language}_sentence_target",
        type="Diagram",
        content={"nodes": sentence_nodes(language), "edges": []},
        layout=LayoutBox(width=12.5, height=3.1, margin_bottom=0.35),
    )


def part_meaning(b: CanvasBuilder) -> None:
    b.add_heading(
        "ONE EVENT — MORE THAN ONE GRAMMATICAL PACKAGE",
        style={"width": 12.6, "margin-bottom": 0.35},
    )
    b.add_body(
        "Start with roles, not English word order: a student is performing a reading action on a definite book today.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.4},
    )
    b.add_diagram(
        meaning_nodes(),
        [],
        id="meaning_roles",
        style={"width": 12.4, "height": 2.5, "margin-bottom": 0.7},
        run_time=1.2,
    )


def part_transform(b: CanvasBuilder) -> None:
    b.add_heading("01  KEEP THE ROLES; REARRANGE THEIR EXPRESSIONS", style={"margin-top": 2.4, "margin-bottom": 0.35})
    sentence_id = b.add_diagram(
        sentence_nodes("english"),
        [],
        id="sentence_transform",
        style={"width": 12.5, "height": 3.1, "margin-bottom": 0.25},
        run_time=1.4,
    )
    b.add_body(
        str(SENTENCES["english"]["text"]),
        style={"width": 11.8, "align": "center", "margin-bottom": 0.2},
    )
    b.add_element_morph(sentence_id, sentence_target("uzbek"), run_time=1.5)
    b.add_body(
        str(SENTENCES["uzbek"]["text"]),
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_compare(b: CanvasBuilder) -> None:
    b.add_heading("02  THE CONTRAST REMAINS VISIBLE", style={"margin-top": 2.4, "margin-bottom": 0.35})
    b.add_diagram(
        contrast_nodes(),
        [],
        id="sentence_contrast",
        style={"width": 12.8, "height": 4.8, "margin-bottom": 0.3},
        run_time=1.5,
    )
    b.add_flex_row(
        [
            b.text_spec(str(SENTENCES["english"]["pattern"]), style={"width": 5.8, "color": MUTED}),
            b.text_spec(str(SENTENCES["uzbek"]["pattern"]), style={"width": 5.8, "color": MUTED}),
        ],
        gap=0.45,
        justify_content="center",
        style={"margin-bottom": 0.65},
    )


def part_morphology(b: CanvasBuilder) -> None:
    b.add_heading("03  SMALL ENDINGS CARRY GRAMMATICAL WORK", style={"margin-top": 2.4, "margin-bottom": 0.35})
    for item in MORPHEMES:
        b.add_body(
            [
                b.run(str(item["surface"]), color=MARKER, bold=True, font_size=31),
                b.run(f"   →   {item['parts']}"),
            ],
            style={"width": 11.5, "align": "center", "margin-bottom": 0.12},
        )
        b.add_body(
            str(item["gloss"]),
            style={"width": 10.8, "align": "center", "margin-bottom": 0.35},
        )
    b.add_body(
        "The gloss explains selected structure; it is not a word-for-word natural English sentence.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_reading_path(b: CanvasBuilder) -> None:
    b.add_heading("04  A TIMED READING PATH — AUDIO OPTIONAL", style={"margin-top": 2.4, "margin-bottom": 0.35})
    path_id = b.add_diagram(
        reading_nodes(),
        [],
        id="reading_path",
        style={"width": 12.2, "height": 2.4, "margin-bottom": 0.35},
        run_time=1.2,
    )
    for role in ("actor", "time", "object", "action"):
        target = f"{path_id}::node:reading_{role}"
        b.add_state_transition(
            [{"target_id": target, "changes": {"scale": 1.08}}],
            run_time=0.35,
        )
        b.add_state_transition(
            [{"target_id": target, "changes": {"scale": 1.0}}],
            run_time=0.2,
        )
    b.add_body(
        "The visual cue sequence demonstrates timing without shipping audio. Pronunciation audio must be recorded and reviewed separately before it is synchronized.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_variation(b: CanvasBuilder) -> None:
    b.add_heading("05  A PATTERN IS NOT A PRISON", style={"margin-top": 2.4, "margin-bottom": 0.35})
    b.add_flex_row(
        [
            b.text_spec("ENGLISH\nThis neutral example uses subject–verb–object order.", style={"width": 5.7, "wrap": True}),
            b.text_spec("UZBEK\nIts neutral order is verb-final, but context and emphasis can permit variation.", style={"width": 5.7, "wrap": True}),
        ],
        gap=0.45,
        justify_content="center",
        style={"margin-bottom": 0.5},
    )
    b.add_body(
        "Neither one sentence nor one gloss defines an entire language.",
        id="language_synthesis",
        style={"width": 11.5, "align": "center", "margin-bottom": 0.65},
    )
    b.add_camera_focus(
        "language_synthesis",
        mode="isolate",
        zoom=1.15,
        hold_time=0.9,
        run_time=0.6,
        reset_run_time=0.5,
    )


class SentenceAcrossLanguages(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(
            title="How One Thought Changes Across Languages",
            background_color=BG,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        part_meaning(builder)
        part_transform(builder)
        part_compare(builder)
        part_morphology(builder)
        part_reading_path(builder)
        part_variation(builder)
        super().__init__(dsl=builder.build(), **kwargs)
