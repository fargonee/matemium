"""Structured conventional surface-water treatment teaching model."""

from __future__ import annotations

BG = "#071721"
WHITE = "#f4f9fb"
MUTED = "#7f96a3"
RAW = "#b47b4f"
PROCESS = "#54b7e8"
PARTICLE = "#e6a64c"
MICROBE = "#ce72df"
CONTROL = "#ffcc5c"
CLEAN = "#58d6b0"
BOUNDARY = "#ff7485"

STAGES = [
    {
        "id": "source",
        "name": "1 · SOURCE + INTAKE",
        "purpose": "Source protection and intake screening begin the system.",
        "kind": "context",
    },
    {
        "id": "coagulation",
        "name": "2 · COAGULATION",
        "purpose": "Coagulants destabilize charges on fine suspended particles.",
        "kind": "particle",
    },
    {
        "id": "flocculation",
        "name": "3 · FLOCCULATION",
        "purpose": "Gentle mixing helps particles form larger floc.",
        "kind": "particle",
    },
    {
        "id": "sedimentation",
        "name": "4 · SEDIMENTATION",
        "purpose": "Heavier floc settles away from the water moving onward.",
        "kind": "particle",
    },
    {
        "id": "filtration",
        "name": "5 · FILTRATION",
        "purpose": "Filter media remove remaining particles and reduce germs.",
        "kind": "barrier",
    },
    {
        "id": "disinfection",
        "name": "6 · DISINFECTION",
        "purpose": "A controlled treatment inactivates susceptible pathogens.",
        "kind": "barrier",
    },
    {
        "id": "storage",
        "name": "7 · STORAGE",
        "purpose": "Protected capacity helps the system meet changing demand.",
        "kind": "delivery",
    },
    {
        "id": "distribution",
        "name": "8 · DISTRIBUTION",
        "purpose": "Pipes, pressure, monitoring, and maintenance carry water to taps.",
        "kind": "delivery",
    },
]

CHALLENGES = [
    ("SUSPENDED PARTICLES", "The conventional sequence gathers, settles, and filters them.", PARTICLE),
    ("MICROORGANISMS", "Filtration and disinfection act as distinct microbial barriers.", MICROBE),
    ("DISSOLVED CHEMICALS", "Source-specific risks may require processes not shown here.", MUTED),
]

DISTURBANCE = [
    ("SENSE", "a turbidity reading changes"),
    ("VERIFY", "staff check the instrument and conditions"),
    ("RESPOND", "operators follow plant procedures"),
    ("CONFIRM", "downstream quality data checks the response"),
]


def stage_color(kind: str) -> str:
    return {
        "context": RAW,
        "particle": PARTICLE,
        "barrier": PROCESS,
        "delivery": CLEAN,
    }[kind]


def _node(
    node_id: str,
    label: str,
    position: tuple[float, float],
    color: str,
    *,
    width: float = 2.1,
    height: float = 0.9,
    font_size: int = 16,
) -> dict[str, object]:
    return {
        "id": node_id,
        "label": label,
        "position": list(position),
        "shape": "rounded",
        "width": width,
        "height": height,
        "color": color,
        "fill_color": color,
        "fill_opacity": 0.2,
        "font_size": font_size,
    }


def overview_network() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    nodes = [
        _node("source", "SOURCE", (-5.2, 0.0), RAW, width=1.8),
        _node("plant", "TREATMENT\nPLANT", (-3.1, 0.0), PROCESS, width=2.0),
        _node("storage", "STORAGE", (-0.7, 0.0), CLEAN, width=1.8),
        _node("pump", "PUMP / PRESSURE", (1.7, 0.0), CONTROL, width=2.2),
        _node("network", "PIPE NETWORK", (4.1, 0.0), CLEAN, width=2.0),
        _node("tap", "TAP", (6.0, 0.0), WHITE, width=1.35),
    ]
    # The adjacent text states direction. Current compact Diagram arrowheads
    # terminate at node centers and obscure labels, so the semantic overview is
    # intentionally connector-free.
    return nodes, []


def treatment_train() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Eight-stage snake layout with a single non-crossing flow path."""

    positions = [
        (-4.8, 1.5),
        (-1.6, 1.5),
        (1.6, 1.5),
        (4.8, 1.5),
        (4.8, -1.5),
        (1.6, -1.5),
        (-1.6, -1.5),
        (-4.8, -1.5),
    ]
    nodes = [
        _node(
            str(stage["id"]),
            str(stage["name"]).replace(" · ", "\n"),
            positions[index],
            stage_color(str(stage["kind"])),
            width=2.45,
            height=0.9,
            font_size=14,
        )
        for index, stage in enumerate(STAGES)
    ]
    return nodes, []


def disturbance_nodes() -> list[dict[str, object]]:
    return [
        _node(
            f"response_{index}",
            f"{title}\n{detail}",
            (-4.6 + index * 3.05, 0.0),
            CONTROL if index < 3 else CLEAN,
            width=2.55,
            height=1.35,
            font_size=14,
        )
        for index, (title, detail) in enumerate(DISTURBANCE)
    ]
