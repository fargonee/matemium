"""Solid rotation test — turn in place with holds, then inspect.

Render: matemium render inscribed_sphere InscribedSphereRotate
"""

from __future__ import annotations

from canvas import CanvasScene
from canvas.builder import CanvasBuilder

from .helpers import (
    add_labeled_inscribed_pair,
    cube_face_rotation_path,
    short_billboard_inspect_path,
)


class InscribedSphereRotate(CanvasScene):
    """Rotate a solid on the tape (center fixed), hold at each pose, then inspect."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Solid Rotation")

        builder.add_heading(
            "Rotate on the tape",
            style={"align": "center", "margin-bottom": 0.4},
        )
        builder.add_body(
            "The solid turns about its center — z anchor unchanged. "
            "Each step can hold so learners read labels and faces.",
            style={"margin-bottom": 0.5},
        )

        solid_id = add_labeled_inscribed_pair(
            builder,
            id="rotating_pair",
            cube_side=2.2,
            style={"align": "center", "margin-bottom": 0.35},
        )

        builder.add_solid_lift(solid_id, lift=1.5, run_time=0.9)

        # One-shot preset
        builder.add_solid_rotate(solid_id, preset="show_right", preset_kwargs={"hold": 1.0})

        # Multi-step path with holds
        builder.add_solid_rotation(
            solid_id,
            path=cube_face_rotation_path(builder),
        )

        # Camera inspect while object stays at last rotation
        builder.add_camera_inspect(
            solid_id,
            path=short_billboard_inspect_path(builder)[:4],
            curve="linear",
            return_to_sheet=True,
        )

        builder.add_observation(
            "Rotation and inspect compose: turn the object, pause, then walk the camera.",
            style={"margin-top": 0.3},
        )

        super().__init__(dsl=builder.build(), **kwargs)