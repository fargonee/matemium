"""Mobile-first SN2 flagship: one event, one locked spatial reference.

The key mechanism stays in a persistent project-local 3D world. One ordinary
tape is used only for the closing synthesis; it is not falsely composited over
the molecule. Molecular geometry and the energy marker are generated from the
same authored reaction-progress state.
"""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

from .helpers import (
    BG,
    ENERGY,
    FORMING,
    GROUP_3,
    SOFT,
    reaction_world_state,
)

WORLD_ID = "sn2_world"

# After one short establishing move, every chemically important change uses
# this exact camera. The C--Br axis therefore remains a stable screen-space
# reference and molecular inversion cannot be mistaken for camera rotation.
LOCKED_SHOT = {
    "phi": 76.0,
    "theta": -78.0,
    "zoom": 1.08,
    "run_time": 0.35,
    "hold": 0.0,
}


def world_target(
    progress: float,
    *,
    cue: str,
    show_energy: bool = False,
    show_reference_plane: bool = False,
    comparison: bool = False,
) -> CanvasElement:
    return CanvasElement(
        id=WORLD_ID,
        type="SN2ReactionWorld",
        content=reaction_world_state(
            progress,
            cue=cue,
            show_energy=show_energy,
            show_reference_plane=show_reference_plane,
            comparison=comparison,
        ),
        auto_focus=False,
    )


def add_locked_hold(b: CanvasBuilder, seconds: float) -> None:
    shot = dict(LOCKED_SHOT)
    shot["run_time"] = 0.20
    shot["hold"] = seconds
    b.add_camera_inspect(WORLD_ID, path=[shot], return_to_sheet=False)


def author_final_tape(b: CanvasBuilder, tape) -> None:
    tape.add_heading(
        "ONE CONCERTED EVENT:",
        id="final_title",
        style={"width": 7.2, "align": "center", "font-size": 43, "margin-bottom": 0.48},
    )
    tape.add_body(
        [
            b.run("BACKSIDE ATTACK", color=FORMING, bold=True, font_size=32),
            b.run("  ·  ", color=SOFT, font_size=30),
            b.run("SIMULTANEOUS BOND CHANGE", color=ENERGY, bold=True, font_size=32),
            b.run("\nINVERSION", color=GROUP_3, bold=True, font_size=32),
        ],
        id="final_synthesis",
        style={"width": 7.2, "height": 1.50, "align": "center", "margin-bottom": 0.34},
    )


def build_production() -> CanvasBuilder:
    b = CanvasBuilder(
        canvas_settings=CanvasSettings.for_reels(
            title="Inside an SN2 Reaction",
            background_color=BG,
        )
    )
    finale = b.add_tape("finale", frame_width=7.5, frame_height=4.4)

    # 1. Enter directly into the persistent molecule. Its first state carries
    # the large reaction identity and atom labels inside the spatial world.
    b.add_object(
        "SN2ReactionWorld",
        id=WORLD_ID,
        content=reaction_world_state(0.0, cue="identity"),
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[
            b.inspect_shot(phi=66, theta=-48, zoom=0.90, run_time=1.15, hold=0.30),
            b.inspect_shot(**LOCKED_SHOT),
        ],
        return_to_sheet=False,
    )
    add_locked_hold(b, 1.35)

    # 2. Establish the axis, its two sides, the attack arrow, and 180 degrees.
    b.add_element_morph(
        WORLD_ID,
        world_target(0.0, cue="alignment"),
        run_time=0.75,
    )
    add_locked_hold(b, 2.55)

    # 3. Keep the camera fixed while both bonds and the umbrella geometry
    # change. The transition state freezes with two equally prominent dashes.
    b.add_element_morph(
        WORLD_ID,
        world_target(0.22, cue="concerted", show_reference_plane=True),
        run_time=1.25,
    )
    b.add_element_morph(
        WORLD_ID,
        world_target(0.50, cue="concerted", show_reference_plane=True),
        run_time=1.65,
    )
    add_locked_hold(b, 1.15)
    b.add_element_morph(
        WORLD_ID,
        world_target(0.78, cue="concerted", show_reference_plane=True),
        run_time=1.25,
    )
    b.add_element_morph(
        WORLD_ID,
        world_target(1.0, cue="concerted", show_reference_plane=True),
        run_time=1.20,
    )
    add_locked_hold(b, 0.45)

    # 4. Replay the same authored progress with a large energy coordinate in
    # the same registered world. The dot and molecular state share `progress`.
    for progress, run_time, hold in (
        (0.0, 0.80, 0.10),
        (0.25, 0.90, 0.0),
        (0.50, 1.05, 0.55),
        (0.75, 0.90, 0.0),
        (1.0, 0.90, 0.20),
    ):
        b.add_element_morph(
            WORLD_ID,
            world_target(progress, cue="energy", show_energy=True),
            run_time=run_time,
        )
        if hold:
            add_locked_hold(b, hold)

    # 5. Clear the graph back to the product before opening the fixed-camera,
    # fixed-plane comparison. This avoids a graph-to-stereochemistry tangle
    # and does not ask the viewer to remember a prior rotating view.
    b.add_element_morph(
        WORLD_ID,
        world_target(1.0, cue="inversion", show_reference_plane=True),
        run_time=0.60,
    )
    b.add_element_morph(
        WORLD_ID,
        world_target(1.0, cue="inversion", comparison=True),
        run_time=0.80,
    )
    add_locked_hold(b, 2.65)

    # 6. End with exactly the requested synthesis, at mobile scale.
    author_final_tape(b, finale)
    return b


class SN2Reaction(CanvasScene):
    def __init__(self, **kwargs):
        super().__init__(dsl=build_production().build(), **kwargs)
