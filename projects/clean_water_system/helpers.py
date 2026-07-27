"""Process stages and disturbance trace for the clean-water flagship."""

from __future__ import annotations

STAGES = [
    ("Source", "screens remove large debris"),
    ("Coagulation", "charge is destabilized so small particles can meet"),
    ("Flocculation", "gentle mixing grows removable floc"),
    ("Settling", "gravity separates dense floc"),
    ("Filtration", "media remove remaining particles"),
    ("Disinfection", "a controlled barrier inactivates pathogens"),
    ("Storage", "covered capacity buffers changing demand"),
    ("Distribution", "pressure and monitoring carry water to taps"),
]

DISTURBANCE = [
    ("sensor", "turbidity rises"),
    ("control room", "alarm is verified"),
    ("treatment", "dose and flow are adjusted"),
    ("sampling", "quality is checked before release"),
]
