"""Template for a new Matemium video project.

Project slug: PROJECT_SLUG
Render:       matemium render PROJECT_SLUG
Output:       outputs/PROJECT_SLUG/media/

Desktop app:  one scenes.py per project; # ---DIV: ...--- markers define editor sections.
"""

from __future__ import annotations

from canvas import CanvasScene
from canvas.builder import CanvasBuilder

# ---DIV: Scene parts---
def part_intro(tape) -> None:
    tape.add_heading("Your title here")
    tape.add_body("Start your mathematical reasoning...")
    tape.add_math(r"x^2 - 5x + 6 = 0")


def part_conclusion(tape, b: CanvasBuilder) -> None:
    tape.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")
    b.add_object("Solid3D", id="demo_cube", position=(3, 0, 1), content={"shape": "cube"})
    tape.add_text("Conclusion: x = 2 or x = 3")


# ---DIV: Main scene---
class MyVideo(CanvasScene):
    """Main scene for PROJECT_SLUG."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="MyVideo")
        tape = builder.add_tape("main")

        part_intro(tape)
        part_conclusion(tape, builder)

        # Example secondary tape
        info = builder.add_tape("side_panel")
        info.add_heading("Side notes")
        info.add_body("This cleanly context-switches the entire layout!")

        super().__init__(dsl=builder.build(), **kwargs)
