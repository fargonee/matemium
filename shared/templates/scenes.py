"""Default scenes.py template for new Matemium desktop projects.

Copy to: <workspace>/scenes.py
Markers: # ---DIV: Title---  (editor section fences; valid Python comments)
"""

from __future__ import annotations

from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder


# ---DIV: Scene parts---
def part_intro(b: CanvasBuilder) -> None:
    b.add_heading("Your title here")
    b.add_body("Start your mathematical reasoning...")
    b.add_math(r"x^2 - 5x + 6 = 0")
    b.add_observation("We look for two numbers that multiply to 6 and add to -5.")


def part_conclusion(b: CanvasBuilder) -> None:
    b.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")
    b.add_text("Conclusion: x = 2 or x = 3")


def part_compare_tapes(b: CanvasBuilder) -> None:
    left = b.add_tape("method_tape")
    left.add_heading("Method")
    left.add_body("Use factoring to rewrite the expression.")
    left.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")

    right = b.add_tape("check_tape")
    right.add_heading("Check")
    right.add_body("Substitute each root back into the original equation.")
    right.add_math(r"x=2:\;4-10+6=0")
    right.add_math(r"x=3:\;9-15+6=0")

    left.add_observation("When content returns to this tape, the engine switches the visible tape context automatically.")


# ---DIV: Main scene---
class MyScene(CanvasScene):
    """Main scene for this project."""

    def __init__(self, **kwargs):
        # Default: portrait 9:16 (Reels / Shorts). For YouTube 16:9 use:
        # CanvasBuilder(title="My Scene", canvas_settings=CanvasSettings.for_youtube())
        builder = CanvasBuilder(
            title="My Scene",
            canvas_settings=CanvasSettings.for_reels(title="My Scene"),
        )
        part_intro(builder)
        part_conclusion(builder)
        part_compare_tapes(builder)
        super().__init__(dsl=builder.build(), **kwargs)
