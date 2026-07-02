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
        # Pose the main tape in 3D space (tilts the plane itself). Camera in tape-scroll
        # mode will automatically look straight down the local normal (from above).
        builder.set_tape_pose(rotation=(20, 10, 0))

        part_intro(builder)
        part_conclusion(builder)

        # Example secondary tape + mixed observation (newest patterns)
        info = builder.add_tape("side_panel", position=(4, 0, 0), rotation=(0, 30, 0))
        with builder.in_object_space(info):
            builder.add_body("Side notes (local to tilted tape)")

        # Switch behaviors explicitly:
        builder.observe_object(info, run_time=1.5)  # pure 3D view of secondary tape
        builder.scroll_tape(local_y=2.0)            # tape-scroll on main (posed) tape

        super().__init__(dsl=builder.build(), **kwargs)