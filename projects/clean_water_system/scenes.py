"""Flagship authoring pass: a multi-barrier drinking-water system."""

from __future__ import annotations

from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

from .helpers import DISTURBANCE, STAGES


def part_reverse_journey(tape) -> None:
    tape.add_heading("What stands behind one glass of water?", style={"align": "center"})
    tape.add_body(
        "Trace the tap backward: building pipe → distribution main → storage → treatment plant → source. "
        "Safe delivery is a monitored system, not one magical filter."
    )


def part_barriers(tape, builder: CanvasBuilder) -> None:
    tape.add_heading("Different barriers do different work")
    for index in range(0, len(STAGES), 4):
        tape.add_flex_row(
            [
                builder.text_spec(f"{name}\n{purpose}", style={"width": 3.35, "wrap": True})
                for name, purpose in STAGES[index : index + 4]
            ],
            gap=0.25,
        )
    tape.add_body(
        "Suspended particles, dissolved substances, and microorganisms are not interchangeable. "
        "Treatment design and operating targets depend on source water and local regulation."
    )


def part_disturbance(tape, builder: CanvasBuilder) -> None:
    tape.add_heading("Monitoring closes an operational loop")
    tape.add_flex_row(
        [
            builder.text_spec(f"{place}\n{action}", style={"width": 3.3, "wrap": True})
            for place, action in DISTURBANCE
        ],
        gap=0.25,
    )
    tape.add_body(
        "Storage buffers demand and pumps maintain pressure, while sampling and sensors inform action. "
        "Wastewater collection and treatment form a separate downstream system."
    )


def part_synthesis(tape) -> None:
    tape.add_heading("Ordinary at the tap, coordinated underneath")
    tape.add_body(
        "Source protection, particle removal, disinfection, storage, pressure, and monitoring work as "
        "multiple barriers. No compact diagram should be used as plant-specific operating guidance."
    )


class CleanWaterSystem(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(title="How a City Gets Clean Water")
        builder = CanvasBuilder(canvas_settings=settings)
        tape = builder.add_tape("main")
        part_reverse_journey(tape)
        part_barriers(tape, builder)
        part_disturbance(tape, builder)
        part_synthesis(tape)
        super().__init__(dsl=builder.build(), **kwargs)
