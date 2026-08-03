"""Philosophy flagship: the Ship of Theseus as structured reasoning."""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings, LayoutBox
from canvas.builder import CanvasBuilder

from .helpers import (
    ACCOUNTS,
    BG,
    DEFINITIONS,
    MUTED,
    OBJECTION,
    ORIGINAL,
    QUESTION,
    REPLACEMENT,
    SUPPORT,
    TRANSFER_CASES,
    rival_claimants,
    replacement_storyboard,
    ship_nodes,
)


def ship_target(replaced: int) -> CanvasElement:
    return CanvasElement(
        id=f"ship_state_{replaced}",
        type="Diagram",
        content={"nodes": ship_nodes(replaced), "edges": []},
        layout=LayoutBox(width=10.8, height=3.3, margin_bottom=0.4),
    )


def part_opening(b: CanvasBuilder) -> None:
    b.add_heading(
        "WHEN DOES A REPAIRED OBJECT STOP BEING THE SAME OBJECT?",
        style={"width": 12.8, "margin-bottom": 0.35},
    )
    b.add_body(
        "Replace one damaged plank: identity seems continuous. Repeat the repair until no original plank remains—and that intuition comes under pressure.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.4},
    )
    ship_id = b.add_diagram(
        ship_nodes(0),
        [],
        id="changing_ship",
        style={"width": 10.8, "height": 3.3, "margin-bottom": 0.25},
        run_time=1.2,
    )
    b.add_element_morph(ship_id, ship_target(2), run_time=1.0)
    b.add_element_morph(ship_id, ship_target(5), run_time=1.0)
    b.add_body(
        [
            b.run("BLUE", color=ORIGINAL, bold=True),
            b.run(" = original plank   ·   "),
            b.run("GOLD", color=REPLACEMENT, bold=True),
            b.run(" = replacement plank"),
        ],
        style={"width": 10.5, "align": "center", "margin-bottom": 0.75},
    )


def part_sequence(b: CanvasBuilder) -> None:
    b.add_heading("01  CHANGE IS GRADUAL, NOT A SINGLE MAGIC MOMENT", style={"margin-top": 2.4, "margin-bottom": 0.35})
    b.add_diagram(
        replacement_storyboard(),
        [],
        id="replacement_storyboard",
        style={"width": 12.2, "height": 6.0, "margin-bottom": 0.3},
        run_time=1.5,
    )
    b.add_math(
        r"S_0\rightarrow S_1\rightarrow\cdots\rightarrow S_5",
        style={"width": 8.2, "margin-bottom": 0.7},
    )


def part_rival(b: CanvasBuilder) -> None:
    b.add_heading("02  SAVING THE OLD PLANKS CREATES A RIVAL", style={"margin-top": 2.4, "margin-bottom": 0.35})
    b.add_diagram(
        rival_claimants(),
        [],
        id="rival_claimants",
        style={"width": 12.0, "height": 4.7, "margin-bottom": 0.3},
        run_time=1.4,
    )
    b.add_body(
        "Both can resemble the earlier ship. But if A and B are now two distinct objects, they cannot both be numerically identical to the one original ship.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_vocabulary(b: CanvasBuilder) -> None:
    b.add_heading("03  TWO KINDS OF “SAME”", style={"margin-top": 2.4, "margin-bottom": 0.35})
    b.add_flex_row(
        [
            b.text_spec(
                f"{title}\n{definition}",
                style={"width": 5.8, "wrap": True, "color": QUESTION if index == 0 else SUPPORT},
            )
            for index, (title, definition) in enumerate(DEFINITIONS)
        ],
        gap=0.5,
        justify_content="center",
        style={"margin-bottom": 0.7},
    )


def part_argument_map(b: CanvasBuilder) -> None:
    b.add_heading("04  FOUR CRITERIA — EACH MEETS AN OBJECTION", style={"margin-top": 2.4, "margin-bottom": 0.35})
    for account in ACCOUNTS:
        b.add_body(
            [b.run(str(account["criterion"]), color=QUESTION, bold=True, font_size=30)],
            style={"width": 11.8, "align": "left", "margin-bottom": 0.08},
        )
        b.add_flex_row(
            [
                b.text_spec(f"SUPPORT\n{account['supports']}", style={"width": 5.7, "wrap": True, "color": SUPPORT}),
                b.text_spec(f"OBJECTION\n{account['objection']}", style={"width": 5.7, "wrap": True, "color": OBJECTION}),
            ],
            gap=0.45,
            justify_content="center",
            style={"margin-bottom": 0.35},
        )


def part_transfer(b: CanvasBuilder) -> None:
    b.add_heading("05  THE ARGUMENT STRUCTURE TRAVELS", style={"margin-top": 2.4, "margin-bottom": 0.35})
    b.add_flex_row(
        [
            b.text_spec(f"{title}\n{detail}", style={"width": 3.75, "wrap": True, "color": MUTED})
            for title, detail in TRANSFER_CASES
        ],
        gap=0.35,
        justify_content="center",
        style={"margin-bottom": 0.55},
    )
    b.add_body(
        "The examples are analogies, not solutions: each changes which material, functional, and historical facts matter.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_synthesis(b: CanvasBuilder) -> None:
    b.add_heading("NO WINNER BY ILLUSTRATION ALONE", style={"margin-top": 2.4, "margin-bottom": 0.3})
    b.add_body(
        "The puzzle does not prove that matter, continuity, organization, or causal history must win. It reveals that our ordinary word “same” can hide competing criteria.",
        id="identity_synthesis",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.65},
    )
    b.add_camera_focus(
        "identity_synthesis",
        mode="isolate",
        zoom=1.12,
        hold_time=0.9,
        run_time=0.6,
        reset_run_time=0.5,
    )


class ShipOfTheseus(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(
            title="The Ship of Theseus as an Argument Map",
            background_color=BG,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        part_opening(builder)
        part_sequence(builder)
        part_rival(builder)
        part_vocabulary(builder)
        part_argument_map(builder)
        part_transfer(builder)
        part_synthesis(builder)
        super().__init__(dsl=builder.build(), **kwargs)
