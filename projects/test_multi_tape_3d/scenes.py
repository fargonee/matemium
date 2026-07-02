"""Test project: 2 tapes + switching with distant large 3D objects.

Project slug: test_multi_tape_3d
Render:       matemium render test_multi_tape_3d
Output:       outputs/test_multi_tape_3d/media/
"""

from __future__ import annotations

from canvas import CanvasScene
from canvas.builder import CanvasBuilder
from canvas.dsl import WorldPoint


class MultiTape3DTest(CanvasScene):
    """Short test of 2 tapes + free 3D objects far away in a real 3D world.
    Demonstrates continuous camera switching between tape-scroll and 3D objects.
    """

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Multi Tape 3D Test")

        # === Main tape (horizontal, default) ===
        builder.add_heading("Tape A — Horizontal")
        builder.add_body("This is the primary horizontal tape. Content is laid flat in world space.")
        builder.add_math(r"\sin^2 \theta + \cos^2 \theta = 1")
        builder.add_observation("We switch between horizontal tape, vertical tape, and scattered 3D objects.")

        # === Secondary tape (vertical, near the first one) ===
        sec_tape = builder.add_tape(
            "sec_tape",
            position=(0, 0, -2.5),
            rotation=(90, 0, 0),  # makes the tape plane vertical
        )
        with builder.in_object_space(sec_tape):
            builder.add_heading("Tape B — Vertical")
            builder.add_body("This tape stands vertically. Its content is local to the upright plane.")
            builder.add_math(r"\nabla \cdot \vec{B} = 0")

        # === Free 3D objects — scattered around like a real 3D world ===
        # Different directions, distances, heights
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
        builder.add_object(
            "Solid3D",
            id="tall_cube_back",
            position=(3, 1, 18),
            content={"shape": "cube", "size": 3.5},
        )
        builder.add_object(
            "Solid3D",
            id="sphere_high",
            position=(-6, 9, -9),
            content={"shape": "sphere", "size": 3.0},
        )
        builder.add_object(
            "Solid3D",
            id="cube_far_side",
            position=(20, 3, -15),
            content={"shape": "cube", "size": 4.0},
        )

        # === Camera tour as specified: observe 3D, Tape A (show content), another 3D, Tape B, Tape A ===
        # The 3D world is fixed. Camera moves/orients through the space to observe.
        # 1. Observe a 3D object
        builder.observe_object("big_cube_right", run_time=1.5)

        # 2. Move to Tape A and show something in it
        builder.scroll_tape(local_y=4.0, run_time=1.8)

        # 3. Move to another 3D object
        builder.observe_object("large_sphere_left", run_time=1.5)

        # 4. Move to Tape B
        builder.observe_object(sec_tape, run_time=1.3)
        builder.scroll_tape(local_y=2.0, tape_id=sec_tape, run_time=1.5)

        # 5. Move to Tape A
        builder.scroll_tape(local_y=7.0, run_time=1.5)

        super().__init__(dsl=builder.build(), **kwargs)