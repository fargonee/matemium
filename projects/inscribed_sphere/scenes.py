"""Sphere inscribed in a cube — 3D solids, lift, and camera orbit test scene.

Project slug: inscribed_sphere
Render:       matemium render inscribed_sphere
Output:       outputs/inscribed_sphere/media/
"""

from __future__ import annotations

from canvas import CanvasScene
from canvas.builder import CanvasBuilder

from .helpers import (
    add_inscribed_pair,
    inscribed_edge_corner_path,
    inscribed_full_inspect_tour,
    inscribed_orbit_finale_path,
    inscribed_tangency_study_path,
)


class InscribedSphere(CanvasScene):
    """When does a sphere fit exactly inside a cube?"""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Inscribed Sphere")

        # Pose the main tape in 3D space (tilts the plane itself). Camera in tape-scroll
        # mode will automatically look straight down the local normal (from above).
        builder.set_tape_pose(rotation=(18, 22, 0))

        builder.add_heading(
            "Sphere inscribed in a cube",
            style={"align": "center", "margin-bottom": 0.45},
        )
        builder.add_math(
            r"2r = s \quad\Rightarrow\quad r = \frac{s}{2}",
            style={"align": "center", "margin-bottom": 0.55},
        )
        builder.add_body(
            "A sphere is inscribed in a cube when it touches every face — "
            "no gaps, no overlap. The sphere's diameter must equal the cube's side length.",
            style={"margin-bottom": 0.65},
        )

        solid_id = add_inscribed_pair(
            builder,
            id="inscribed_pair",
            cube_side=2.4,
            style={"align": "center", "margin-bottom": 0.4},
        )

        builder.add_body(
            "On the tape the solid straddles z = 0. Lift it, then we walk a multi-act "
            "camera path — face holds, corner zooms, and a sweeping finale.",
            style={"margin-bottom": 0.5},
        )

        builder.add_solid_lift(solid_id, lift=1.8, run_time=1.3)

        # Act I–II: tangency study — stay in inspect view for next phase
        builder.add_camera_inspect(
            solid_id,
            path=inscribed_tangency_study_path(builder),
            curve="linear",
            return_to_sheet=False,
        )

        builder.add_body(
            "Six faces, six tangent points — the sphere kisses each face at exactly one spot.",
            style={"margin-bottom": 0.45},
        )

        # Act III: edge & corner close-ups (camera returns to sheet for text, then re-lift)
        builder.add_solid_lift(solid_id, lift=2.1, run_time=1.0)
        builder.add_camera_inspect(
            solid_id,
            path=inscribed_edge_corner_path(builder),
            curve="linear",
            return_to_sheet=False,
        )

        builder.add_body(
            "At every edge the sphere is tangent to two faces; at every vertex, to three. "
            "Zoom and offset shots make those contacts visible without any formulas.",
            style={"margin-bottom": 0.45},
        )

        # Act IV: full sweep finale → back to sheet for the math
        builder.add_camera_inspect(
            solid_id,
            path=inscribed_orbit_finale_path(builder),
            curve="linear",
            return_to_sheet=True,
            return_run_time=1.2,
        )

        builder.add_observation(
            "The orange sphere touches all six faces of the blue cube — "
            "that is exactly what inscribed means.",
            style={"margin-top": 0.35, "margin-bottom": 0.45},
        )
        builder.add_math(
            r"V_{\text{sphere}} = \frac{4}{3}\pi r^3 = \frac{\pi}{6}\,s^3",
            style={"align": "center", "margin-bottom": 0.35},
        )
        builder.add_math(
            r"\frac{V_{\text{sphere}}}{V_{\text{cube}}} = \frac{\pi}{6} \approx 0.524",
            style={"align": "center"},
        )

        # Additional 3D object + camera tour (pose was set at top of method)
        builder.add_object("Solid3D", id="demo_cube", position=(3, 0.8, 2), content={"shape": "cube", "size": 0.9})

        # Normal 3D view of the solid (tape as 3D object)
        builder.observe_object("demo_cube", run_time=2.2)

        # Enter tape scroll mode on the posed tape
        builder.scroll_tape(local_y=5.0, run_time=2.8)

        super().__init__(dsl=builder.build(), **kwargs)


class InscribedSphereFullTour(CanvasScene):
    """Stress-test: one continuous inspect path (all acts, ~30 keyframes)."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Inscribed Sphere — Full Tour")

        # Pose the main tape in 3D space (tilts the plane itself). Camera in tape-scroll
        # mode will automatically look straight down the local normal (from above).
        builder.set_tape_pose(rotation=(18, 22, 0))

        builder.add_heading("Sphere inscribed in a cube", style={"align": "center", "margin-bottom": 0.4})
        builder.add_body(
            "Single continuous camera path — tangency, corners, sweep — no cuts.",
            style={"margin-bottom": 0.55},
        )

        solid_id = add_inscribed_pair(builder, id="inscribed_pair", cube_side=2.4, style={"align": "center"})
        builder.add_solid_lift(solid_id, lift=1.9, run_time=1.2)
        builder.add_camera_inspect(
            solid_id,
            path=inscribed_full_inspect_tour(builder),
            curve="linear",
            return_to_sheet=True,
            return_run_time=1.4,
        )
        builder.add_math(r"2r = s", style={"align": "center"})

        super().__init__(dsl=builder.build(), **kwargs)


from .scenes_labels import InscribedSphereLabels  # noqa: E402, F401
from .scenes_rotate import InscribedSphereRotate  # noqa: E402, F401