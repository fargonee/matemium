"""Short billboard-label test — fast render, 3D point labels face the camera.

Project slug: inscribed_sphere
Render:       matemium render inscribed_sphere InscribedSphereLabels
"""

from __future__ import annotations

from canvas import CanvasScene
from canvas.builder import CanvasBuilder

from .helpers import add_labeled_inscribed_pair, short_billboard_inspect_path


class InscribedSphereLabels(CanvasScene):
    """Billboard labels on an inscribed sphere — always readable during inspect."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="Billboard Labels")

        builder.add_heading(
            "Labels face the camera",
            style={"align": "center", "margin-bottom": 0.4},
        )
        builder.add_body(
            "Point labels on the 3D solid stay front-facing as the inspect path moves — "
            "no twisted or edge-on text.",
            style={"margin-bottom": 0.5},
        )

        solid_id = add_labeled_inscribed_pair(
            builder,
            id="labeled_pair",
            cube_side=2.2,
            style={"align": "center", "margin-bottom": 0.35},
        )

        builder.add_solid_lift(solid_id, lift=1.6, run_time=1.0)
        builder.add_camera_inspect(
            solid_id,
            path=short_billboard_inspect_path(builder),
            curve="linear",
            return_to_sheet=True,
            return_run_time=0.9,
        )

        builder.add_observation(
            "Tangent, face, and center markers remain legible from every inspect angle.",
            style={"margin-top": 0.3},
        )

        super().__init__(dsl=builder.build(), **kwargs)