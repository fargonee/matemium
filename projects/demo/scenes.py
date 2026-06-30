"""Built-in demo project — use ``matemium demo`` to render."""

from __future__ import annotations

from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder


class PortraitDemo(CanvasScene):
    """Portrait 9:16 test demo (Reels / Shorts)."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Portrait Demo")
        builder.add_heading("Matemium — Portrait Demo")
        builder.add_math(
            r"\int_{-\infty}^{\infty} e^{-x^2} \, dx = \sqrt{\pi}",
            style={"margin-bottom": 1.0},
        )
        builder.add_3d("z = x^2 - y^2", pitch=50)
        builder.add_text(
            "The canvas is infinite. The reasoning continues forever.",
            after_3d=True,
        )
        builder.add_body(
            "Note: long explanatory text wraps at the safe viewport width, "
            "keeping spacing and scroll rhythm correct on portrait reels.",
            style={"margin-top": 1.0, "margin-bottom": 1.0},
        )
        super().__init__(dsl=builder.build(), **kwargs)


class LandscapeDemo(CanvasScene):
    """Landscape 16:9 test demo (YouTube)."""

    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(title="Landscape Demo")
        builder = CanvasBuilder(title="Landscape Demo", canvas_settings=settings)
        builder.add_heading("Matemium")
        builder.add_text("Now in landscape for YouTube", style={"margin-bottom": 1.0})
        builder.add_math(
            r"\nabla \times \vec{E} = -\frac{\partial \vec{B}}{\partial t}",
            style={"margin-bottom": 1.2},
        )
        builder.add_flex_row(
            [
                builder.text_spec("Side-by-side: ", style={"align": "right"}),
                builder.math_spec(r"a^2 + b^2 = c^2", style={"width": 3.2}),
            ],
            gap=0.7,
            justify_content="center",
            style={"margin-bottom": 1.5, "align": "center"},
        )
        builder.add_3d("z = x^2 - y^2", pitch=42, style={"width": 4.8})
        super().__init__(dsl=builder.build(), **kwargs)


class BuilderDemo(CanvasScene):
    """Showcase flex layout + semantic builder helpers."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(
            title="Builder Demo",
            background_color="#0a0a0a",
        )
        builder.add_heading("Matemium — Builder Demo", style={"align": "center"})
        builder.add_math(
            r"\int_{-\infty}^{\infty} e^{-x^2} \, dx = \sqrt{\pi}",
            style={"margin-bottom": 1.4, "width": 6.5, "align": "left"},
        )
        builder.add_flex_row(
            [
                builder.text_spec("Flex: ", style={"align": "left"}),
                builder.math_spec(r"\sin^2 + \cos^2 = 1", style={"width": 3.8}),
            ],
            gap=0.9,
            justify_content="space-between",
            style={"margin-bottom": 1.8},
        )
        builder.add_flex_row(
            [
                builder.text_spec("Step 1", style={"width": 1.6, "align": "center"}),
                builder.text_spec("Observe", style={"width": 1.8, "align": "center"}),
                builder.text_spec("Derive", style={"width": 1.6, "align": "center"}),
                builder.text_spec("Verify", style={"width": 1.5, "align": "center"}),
            ],
            gap=0.2,
            justify_content="space-between",
            style={"margin-bottom": 1.6},
        )
        builder.add_3d(
            r"z = \sin(x) \cos(y)",
            style={"margin": "0.3 0 1.8 0", "width": 5.2, "align": "center"},
        )
        builder.add_text(
            "The canvas is infinite. The reasoning continues forever.",
            style={"margin-top": 0.8, "align": "right"},
        )
        super().__init__(dsl=builder.build(), **kwargs)


def _ttt_scenario(
    builder: CanvasBuilder,
    *,
    section: str,
    title: str,
    commentary: str,
    moves: list[tuple[str, int, int]],
    takeaway: str,
) -> None:
    """One tutorial beat: heading → flex(board|notes) → moves → punchline."""
    board_id = f"board_{section}"
    builder.add_heading(title, style={"margin-top": 0.6, "margin-bottom": 0.35})
    builder.add_flex_row(
        [
            builder.grid_board_spec(
                rows=3,
                cols=3,
                cell_size=0.9,
                id=board_id,
                style={"width": 2.7},
            ),
            builder.text_spec(commentary, style={"width": 3.6, "wrap": True}),
        ],
        gap=0.85,
        justify_content="center",
        align_items="center",
        style={"margin-bottom": 0.35},
    )
    if moves:
        builder.add_grid_moves(board_id, moves, run_time=0.55)
    builder.add_body(takeaway, style={"margin-top": 0.25, "margin-bottom": 0.4})


class TicTacToeTutorial(CanvasScene):
    """Multi-scenario tic-tac-toe tutorial with flex layout and camera scrolling."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Tic-Tac-Toe Tutorial")

        # ---- Intro (rules) ----
        builder.add_heading("Tic-Tac-Toe Tutorial", style={"align": "center", "margin-bottom": 0.5})
        builder.add_body(
            "Two players — X and O — take turns on a 3×3 grid. "
            "First to get three in a row (horizontal, vertical, or diagonal) wins. "
            "Perfect play always ends in a draw, but mistakes are punishable.",
            style={"margin-bottom": 0.6},
        )
        builder.add_flex_row(
            [
                builder.text_spec("Row 0 = top", style={"width": 2.2, "align": "center"}),
                builder.text_spec("Col 0 = left", style={"width": 2.2, "align": "center"}),
                builder.text_spec("Center = (1,1)", style={"width": 2.4, "align": "center"}),
            ],
            gap=0.4,
            justify_content="space-between",
            style={"margin-bottom": 0.5},
        )
        # ---- Scenario 1: Center opening ----
        _ttt_scenario(
            builder,
            section="center",
            title="1. Take the center",
            commentary=(
                "If you go first, the center is the strongest opening.\n\n"
                "It sits on four lines at once —\n"
                "more winning chances than any corner."
            ),
            moves=[("X", 1, 1), ("O", 0, 0), ("X", 2, 2)],
            takeaway="Center + opposite corner gives X a strong position.",
        )

        # ---- Scenario 2: Corner fork ----
        _ttt_scenario(
            builder,
            section="fork",
            title="2. The fork (two threats)",
            commentary=(
                "A fork is one move that creates\n"
                "TWO winning lines at once.\n\n"
                "Watch X threaten row 0 AND column 0."
            ),
            moves=[("X", 0, 0), ("O", 1, 1), ("X", 0, 2)],
            takeaway="O must block immediately — only one square can stop both lines.",
        )

        # ---- Scenario 3: Blocking ----
        _ttt_scenario(
            builder,
            section="block",
            title="3. Block the threat",
            commentary=(
                "Defending is as important as attacking.\n\n"
                "O plays (0,1) and kills\n"
                "X's top-row win."
            ),
            moves=[("X", 0, 0), ("O", 1, 1), ("X", 0, 2), ("O", 0, 1)],
            takeaway="Always scan for opponent forks before making your own plan.",
        )

        # ---- Scenario 4: Diagonal win ----
        _ttt_scenario(
            builder,
            section="win",
            title="4. Finish the diagonal",
            commentary=(
                "When the center is yours and corners are split,\n"
                "a diagonal can close the game.\n\n"
                "X seals the ↘ diagonal."
            ),
            moves=[
                ("X", 1, 1),
                ("O", 0, 0),
                ("X", 0, 2),
                ("O", 2, 1),
                ("X", 2, 2),
            ],
            takeaway="X wins — three on the main diagonal.",
        )

        # ---- Scenario 5: Draw (cat's game) ----
        _ttt_scenario(
            builder,
            section="draw",
            title="5. Perfect play = draw",
            commentary=(
                "When both sides block every threat,\n"
                "the board fills with no winner.\n\n"
                "This is the famous cat's game."
            ),
            moves=[
                ("X", 0, 0), ("O", 1, 1),
                ("X", 2, 2), ("O", 0, 2),
                ("X", 2, 0), ("O", 0, 1),
                ("X", 1, 2), ("O", 2, 1),
                ("X", 1, 0),
            ],
            takeaway="No three in a row — a draw. Tic-tac-toe is solved: perfect play never loses.",
        )

        # ---- Outro (final scroll target) ----
        builder.add_heading("Summary", style={"align": "center", "margin-top": 0.4})
        builder.add_flex_column(
            [
                builder.text_spec("① Center first when you can", style={"width": 5.5}),
                builder.text_spec("② Watch for forks — block early", style={"width": 5.5}),
                builder.text_spec("③ Corners beat edges in the opening", style={"width": 5.5}),
                builder.text_spec("④ Perfect play → draw", style={"width": 5.5}),
            ],
            gap=0.35,
            align_items="center",
            style={"margin-bottom": 0.6},
        )
        builder.add_body(
            "The canvas scrolls as the lesson continues — "
            "each scenario is its own row on the infinite tape.",
            style={"align": "center", "margin-bottom": 0.8},
        )

        super().__init__(dsl=builder.build(), **kwargs)


# Backward-compatible alias (short flex demo name)
FlexTicTacToeDemo = TicTacToeTutorial
# Backward-compatible alias (short flex demo name)
FlexTicTacToeDemo = TicTacToeTutorial


# --- Phase 10: 3D Space Demo ---
from canvas.dsl import WorldObject, WorldTransform, Vector3, CanvasElement, ObjectAnchor, TapeScroll, WorldPoint


class Space3DDemo(CanvasScene):
    """Phase 10 demo: mixed 3D world with rotated TapeObject, floating 3D solids,
    relative positioning, and camera keyframes moving between them.

    Showcases the unified 3D space where the "tape" is just one object.
    """

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="3D Space Demo")

        # Tape content in its local space (old sheet ergonomics preserved)
        builder.add_heading("3D World Demo", style={"align": "center"})
        builder.add_body(
            "The infinite tape is now a TapeObject inside 3D space. "
            "It can be rotated and positioned arbitrarily.",
            style={"margin-bottom": 0.8},
        )
        builder.add_math(r"\vec{r} = (x, y, z)", style={"margin-bottom": 0.5})

        # Rotate the root tape in 3D (XZ ground, Y up)
        builder.set_tape_pose(rotation=(35, 15, 0))  # pitch ~35°, yaw 15°

        builder.add_body(
            "Content inside the tape still uses familiar flex, styling, and lazy reveal — "
            "but the whole plane lives in 3D.",
            style={"margin-top": 0.4, "margin-bottom": 0.8},
        )

        # Floating 3D solid outside the tape (using high-level add_object + registry dispatch)
        builder.add_object(
            "Solid3D",
            id="cube1",
            position=(4.5, 1.5, 3.0),
            content={"shape": "cube", "size": 1.2},
        )

        # Another object positioned relative to the cube (using Phase 4 APIs)
        label_solid = CanvasElement(
            id="label_on_cube",
            type="Text",
            content="3D object in world space",
        )
        builder.add_relative(
            "cube1",
            label_solid,
            local_offset=(0, 2.0, 0),
            anchor="top",
        )

        # Another free object: axes as example of registered kind in world space
        builder.add_object(
            "Axes",
            position=(0, 0.5, -4.0),
            scale=0.7,
        )

        # Camera keyframe: look at the floating cube
        builder.add_camera_keyframe(
            target=ObjectAnchor(object_id="cube1", anchor="center"),
            duration=3.0,
        )

        # Camera keyframe: scroll along the (rotated) tape
        builder.add_camera_keyframe(
            target=TapeScroll(tape_id="root_tape", local_y=4.0, framing_mode="sheet"),
            duration=4.0,
        )

        # Back to world point
        builder.add_camera_keyframe(
            target=WorldPoint(position=(2.0, 3.0, 4.0)),
            duration=2.5,
        )

        super().__init__(dsl=builder.build(), **kwargs)
