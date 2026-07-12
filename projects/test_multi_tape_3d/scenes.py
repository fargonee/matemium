from __future__ import annotations

from canvas import CanvasScene
from canvas.builder import CanvasBuilder

class MultiTape3DTest(CanvasScene):
    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Multi Tape 3D Test")
        
        tape_a = builder.add_tape('tape_a')
        tape_a.add_heading("Tape A - Horizontal")
        tape_a.add_body("This is the primary horizontal tape.")
        tape_a.add_math(r"\sin^2 \theta + \cos^2 \theta = 1")
        tape_a.add_observation("We switch between horizontal tape, vertical tape, and scattered 3D objects.")

        tape_b = builder.add_tape("tape_b")
        tape_b.add_heading("Tape B - Vertical")
        tape_b.add_body("This tape stands vertically. Its content is local to the upright plane.")
        tape_b.add_math(r"\nabla \cdot \vec{B} = 0")

        builder.add_object(
            "Solid3D",
            id="big_cube_right",
            position=(14, 2, 10),
            content={"shape": "cube", "size": 4.5},
        )
        builder.add_object(
            "Solid3D",
            id="large_sphere_left",
            position=(-13, 4, 5),
            content={"shape": "sphere", "size": 3.8},
        )

        builder.observe_object("big_cube_right", run_time=1.5)
        
        tape_a.add_body("And we are back to Tape A automatically!")

        builder.observe_object("large_sphere_left", run_time=1.5)

        tape_b.add_body("And back to Tape B!")

        super().__init__(dsl=builder.build(), **kwargs)
