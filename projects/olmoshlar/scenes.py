"""Default scenes.py template for new Matemium desktop projects.

Copy to: <workspace>/scenes.py
Markers: # ---DIV: Title---  (editor section fences; valid Python comments)
"""

from __future__ import annotations

from canvas import CanvasScene
from canvas.builder import CanvasBuilder
from canvas.dsl import WorldPoint


# ---DIV: Scene parts---
def part_intro(tape) -> None:
    tape.add_heading("Your title here")
    tape.add_body("Start your mathematical reasoning...")
    tape.add_math(r"x^2 - 5x + 6 = 0")
    tape.add_body("We look for two numbers that multiply to 6 and add to -5.")


def part_conclusion(tape, b: CanvasBuilder) -> None:
    tape.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")
    b.add_3d("z = x^2 - y^2")
    tape.add_text("Conclusion: x = 2 or x = 3", after_3d=True)

    # Additional 3D objects + camera tour (newest authoring). Pose already set at top.
    b.add_object("Solid3D", id="root_sphere", position=(2.5, 0, 2), content={"shape": "sphere", "size": 0.5})

    b.observe_object("root_sphere", run_time=2.0)
    b.add_camera_keyframe(target=WorldPoint(position=(0, 1, 7)), duration=1.8)


# ---DIV: Main scene---
class MyScene(CanvasScene):
    """Main scene for this project. Now uses the 3D world + tape model."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="My Scene")
        tape = builder.add_tape("main")

        part_intro(tape)
        part_conclusion(tape, builder)
        super().__init__(dsl=builder.build(), **kwargs)