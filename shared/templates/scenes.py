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
    # Phase 9+: 3D world example
    b.set_tape_pose(rotation=(30, 0, 0))
    b.add_3d("z = x^2 - y^2")
    b.add_text("Conclusion: x = 2 or x = 3", after_3d=True)
    # Free 3D object
    from canvas.dsl import WorldObject, WorldTransform, Vector3, CanvasElement
    solid = CanvasElement(id="solid1", type="Solid3D", content={"shape": "cube"})
    wo = WorldObject(id="wo1", element=solid, transform=WorldTransform(position=Vector3(5, 0, 5)))
    b.add_world_object(wo)


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
        super().__init__(dsl=builder.build(), **kwargs)