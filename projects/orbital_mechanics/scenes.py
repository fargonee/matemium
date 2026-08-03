"""Cinematic flagship: orbit as continuous free fall.

The production alternates between one persistent spatial model and three
camera-facing tapes. A tape closes over the free 3D world like a curtain,
presents one readable analytical context, then opens back to the world.
"""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

from .helpers import (
    ACCELERATION_CORAL,
    ALTITUDE_KM,
    EARTH_BLUE,
    ELLIPSE_VIOLET,
    ESCAPE_GOLD,
    ORBIT_CYAN,
    REENTRY_CORAL,
    VELOCITY_GOLD,
    circular_speed,
    gravity_at_altitude,
    gravity_fraction,
    orbital_world_state,
)

BG = "#030914"
WHITE = "#f4f8ff"
SOFT = "#b9c7da"
WORLD_ID = "orbital_world"


def world_target(
    regime: str,
    *,
    vectors: bool = True,
    animate_satellite: bool | None = None,
) -> CanvasElement:
    """Morph target for the registered project-local spatial model."""

    return CanvasElement(
        id=WORLD_ID,
        type="OrbitalWorld",
        content=orbital_world_state(
            regime,
            vectors=vectors,
            animate_satellite=animate_satellite,
        ),
        auto_focus=False,
    )


def metric_card(
    b: CanvasBuilder,
    label: str,
    value: str,
    color: str,
    *,
    width: float = 2.7,
) -> dict:
    return b.text_spec(
        [b.run(f"{label}\n{value}", color=color, bold=True, font_size=22)],
        style={"width": width, "height": 1.05, "wrap": True},
    )


def author_title_tape(b: CanvasBuilder, tape) -> None:
    tape.add_heading(
        [
            b.run("WHY AN ORBIT IS A ", color=WHITE, bold=True, font_size=31),
            b.run("CONTINUOUS FALL", color=ORBIT_CYAN, bold=True, font_size=31),
        ],
        id="hero_title",
        style={"width": 6.1, "margin-bottom": 0.28},
    )
    tape.add_body(
        "Gravity never switches off. Sideways motion keeps moving the miss.",
        id="hero_premise",
        style={"width": 5.6, "align": "center", "margin-bottom": 0.32},
    )
    tape.add_solid(
        "sphere",
        id="embedded_earth",
        size=0.72,
        color=EARTH_BLUE,
        opacity=0.9,
        lift=0.24,
        style={"width": 1.15, "height": 1.15, "margin-bottom": 0.2},
    )
    tape.add_solid_rotation(
        "embedded_earth",
        path=[
            b.rotate_shot(axis="x", angle=18, run_time=0.55),
            b.rotate_shot(axis="y", angle=105, run_time=0.85, hold=0.25),
        ],
    )


def author_telemetry_tape(b: CanvasBuilder, tape) -> None:
    gravity = gravity_at_altitude()
    fraction = gravity_fraction()
    speed = circular_speed()
    tape.add_heading(
        "LOW-ORBIT TELEMETRY",
        id="telemetry_title",
        style={"width": 5.8, "margin-bottom": 0.25},
    )
    tape.add_flex_row(
        [
            metric_card(
                b,
                f"ALTITUDE {ALTITUDE_KM:.0f} km",
                f"g = {gravity:.2f} m/s²",
                ACCELERATION_CORAL,
            ),
            metric_card(
                b,
                "SURFACE GRAVITY",
                f"{100.0 * fraction:.0f}% remains",
                EARTH_BLUE,
            ),
        ],
        gap=0.28,
        justify_content="center",
        style={"margin-bottom": 0.25},
    )
    tape.add_math(
        r"v_{\rm circular}=\sqrt{\frac{GM}{r}}",
        id="speed_law",
        style={"width": 4.5, "margin-bottom": 0.2},
        run_time=1.0,
    )
    tape.add_body(
        f"At this altitude: {speed:.2f} km/s",
        id="speed_value",
        style={"width": 4.8, "align": "center", "margin-bottom": 0.15},
    )


def author_regime_heading(b: CanvasBuilder, tape) -> None:
    tape.add_heading(
        "ONE LAUNCH POINT · ONLY SPEED CHANGES",
        id="regime_title",
        style={"width": 6.0, "margin-bottom": 0.26},
    )
    tape.add_body(
        [
            b.run(
                "Normalized two-body model · altitude exaggerated · drag omitted",
                color=SOFT,
                font_size=18,
            )
        ],
        id="model_disclosure",
        style={"width": 6.0, "height": 0.52, "align": "center", "margin-bottom": 0.25},
    )


def author_regime_result(
    b: CanvasBuilder,
    tape,
    *,
    element_id: str,
    label: str,
    outcome: str,
    color: str,
) -> None:
    tape.add_body(
        [
            b.run(f"{label}\n", color=color, bold=True, font_size=25),
            b.run(outcome, color=SOFT, font_size=21),
        ],
        id=element_id,
        style={
            "width": 5.5,
            "height": 0.92,
            "align": "center",
            "margin-bottom": 0.22,
        },
    )


def build_production() -> CanvasBuilder:
    settings = CanvasSettings.for_youtube(
        title="Why an Orbit Is a Continuous Fall",
        background_color=BG,
    )
    b = CanvasBuilder(canvas_settings=settings)

    # Tapes are foreground presentation contexts. They deliberately have no
    # world pose: the runtime closes the selected tape over the camera.
    title_tape = b.add_tape(
        "principle_panel",
        frame_width=6.6,
        frame_height=4.6,
    )
    telemetry_tape = b.add_tape(
        "telemetry_panel",
        frame_width=6.4,
        frame_height=4.8,
    )
    regime_tape = b.add_tape(
        "regime_panel",
        frame_width=6.5,
        frame_height=5.4,
    )
    closing_tape = b.add_tape(
        "closing_panel",
        frame_width=6.4,
        frame_height=4.8,
    )

    # Persistent center of the production: it exists before the first shot and
    # survives every analytical insert.
    b.add_object(
        "OrbitalWorld",
        id=WORLD_ID,
        content=orbital_world_state("circular", vectors=False),
    )
    # Establish the whole system from above the limb, then make one deliberate
    # move to the pole-on teaching view. The speed experiment stays locked there.
    b.add_camera_inspect(
        WORLD_ID,
        path=[
            b.inspect_shot(
                phi=68,
                theta=-90,
                zoom=1.15,
                hold=1.8,
                run_time=0.01,
                target_offset=(0.0, 0.0, 0.28),
            ),
            b.inspect_shot(
                phi=2,
                theta=-90,
                zoom=1.45,
                hold=1.6,
                run_time=3.2,
            ),
        ],
        return_to_sheet=False,
    )

    author_title_tape(b, title_tape)

    # Replay the same release while adding only tangential speed. Each path and
    # moving satellite comes from the same deterministic two-body integration.
    b.add_element_morph(
        WORLD_ID,
        world_target("drop", animate_satellite=True),
        run_time=0.9,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=2, theta=-90, zoom=1.45, hold=2.5, run_time=0.01)],
        return_to_sheet=False,
    )
    b.add_element_morph(
        WORLD_ID,
        world_target("short_arc", animate_satellite=True),
        run_time=0.85,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=2, theta=-90, zoom=1.45, hold=2.1, run_time=0.01)],
        return_to_sheet=False,
    )
    b.add_element_morph(
        WORLD_ID,
        world_target("long_arc", animate_satellite=True),
        run_time=0.85,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=2, theta=-90, zoom=1.45, hold=2.1, run_time=0.01)],
        return_to_sheet=False,
    )
    b.add_element_morph(
        WORLD_ID,
        world_target("reentry", animate_satellite=True),
        run_time=0.85,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=2, theta=-90, zoom=1.45, hold=2.2, run_time=0.01)],
        return_to_sheet=False,
    )
    b.add_element_morph(
        WORLD_ID,
        world_target("circular", animate_satellite=True),
        run_time=1.0,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=2, theta=-90, zoom=1.45, hold=4.0, run_time=0.01)],
        return_to_sheet=False,
    )

    author_telemetry_tape(b, telemetry_tape)

    # Continue above circular speed without changing the observation axis.
    # The first faster case is deliberately still bound; only the final state
    # exceeds escape speed and opens the trajectory.
    b.add_element_morph(
        WORLD_ID,
        world_target("ellipse", animate_satellite=True),
        run_time=1.15,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=2, theta=-90, zoom=1.15, hold=4.2, run_time=0.01)],
        return_to_sheet=False,
    )
    b.add_element_morph(
        WORLD_ID,
        world_target("escape", animate_satellite=True),
        run_time=1.15,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[
            b.inspect_shot(
                phi=2,
                theta=-90,
                zoom=0.9,
                hold=4.2,
                run_time=0.01,
                target_offset=(0.45, 0.0, 0.0),
            )
        ],
        return_to_sheet=False,
    )

    # One compact recap follows the uninterrupted visual experiment.
    author_regime_heading(b, regime_tape)
    author_regime_result(
        b,
        regime_tape,
        element_id="circular_result",
        label="CIRCULAR SPEED",
        outcome="falling inward exactly matches curvature",
        color=ORBIT_CYAN,
    )
    author_regime_result(
        b,
        regime_tape,
        element_id="ellipse_result",
        label="FASTER THAN CIRCULAR",
        outcome="the path widens, but remains bound",
        color=ELLIPSE_VIOLET,
    )
    author_regime_result(
        b,
        regime_tape,
        element_id="escape_result",
        label="ABOVE ESCAPE SPEED",
        outcome="positive energy opens the trajectory",
        color=ESCAPE_GOLD,
    )

    # Resolve the speed experiment back into the central claim and finish with
    # one stable world observation before the final tape closes.
    b.add_element_morph(
        WORLD_ID,
        world_target("circular", animate_satellite=True),
        run_time=1.25,
    )
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=2, theta=-90, zoom=1.35, hold=3.2, run_time=0.01)],
        return_to_sheet=False,
    )
    closing_tape.add_heading(
        [
            b.run("ORBIT IS ", color=WHITE, bold=True, font_size=30),
            b.run("CONTINUOUS FALL", color=ORBIT_CYAN, bold=True, font_size=30),
        ],
        id="closing_title",
        style={"width": 6.0, "margin-bottom": 0.42},
    )
    closing_tape.add_body(
        [
            b.run("FALLING INWARD", color=ACCELERATION_CORAL, bold=True, font_size=27),
            b.run(" + ", color=SOFT, bold=True, font_size=27),
            b.run("MOVING SIDEWAYS", color=VELOCITY_GOLD, bold=True, font_size=27),
            b.run("\n= CONTINUALLY MISSING EARTH", color=ORBIT_CYAN, bold=True, font_size=27),
        ],
        id="final_synthesis",
        style={"width": 6.0, "height": 1.5, "align": "center", "margin-bottom": 0.2},
    )
    return b


class OrbitalMechanics(CanvasScene):
    def __init__(self, **kwargs):
        super().__init__(dsl=build_production().build(), **kwargs)
