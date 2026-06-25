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
def part_intro(b: CanvasBuilder) -> None:
    b.add_heading("Your title here")
    b.add_body("Start your mathematical reasoning...")
    b.add_math(r"x^2 - 5x + 6 = 0")
    b.add_observation("We look for two numbers that multiply to 6 and add to -5.")


def part_conclusion(b: CanvasBuilder) -> None:
    b.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")
    b.add_3d("z = x^2 - y^2")
    b.add_text("Conclusion: x = 2 or x = 3", after_3d=True)


# ---DIV: Main scene---
class MyVideo(CanvasScene):
    """Main scene for PROJECT_SLUG."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="MyVideo")
        part_intro(builder)
        part_conclusion(builder)
        super().__init__(dsl=builder.build(), **kwargs)