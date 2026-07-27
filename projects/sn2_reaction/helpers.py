"""Deterministic chemistry data for the SN2 flagship explanation.

The molecule is an intentionally generic tetrahedral stereocentre. ``R¹``,
``R²``, and ``R³`` preserve substituent identity while the 2D projection makes
Walden inversion inspectable. The drawing is a mechanistic teaching model, not
an optimized molecular geometry or a claim that bonds behave as springs.
"""

from __future__ import annotations

import math

BG = "#07131d"
WHITE = "#f5f8fb"
SOFT = "#b7c6d6"
CARBON = "#d7e0e8"
OXYGEN = "#ff6b6b"
BROMINE = "#c779ff"
FORMING = "#5ce1c6"
BREAKING = "#ff9f5a"
ENERGY = "#ffd166"
GROUP_1 = "#67b7ff"
GROUP_2 = "#78e08f"
GROUP_3 = "#f6c56f"

STATE_X = {
    "reactants": 0.0,
    "transition": 0.5,
    "products": 1.0,
}


def activation_energy(x: float) -> float:
    """Normalized one-step profile with one maximum and lower products."""

    return 4.0 * x * (1.0 - x) - 0.18 * x


def energy_points(samples: int = 81) -> list[list[float]]:
    return [
        [i / (samples - 1), activation_energy(i / (samples - 1))]
        for i in range(samples)
    ]


def energy_plot_series() -> list[dict[str, object]]:
    return [
        {
            "id": "profile",
            "points": energy_points(),
            "color": ENERGY,
            "stroke_width": 6,
            "smooth": True,
        }
    ]


def energy_marker(state: str) -> list[dict[str, object]]:
    x = STATE_X[state]
    return [
        {
            "id": "progress",
            "point": [x, activation_energy(x)],
            "color": WHITE,
            "radius": 0.11,
        }
    ]


def _atom(
    atom_id: str,
    label: str,
    position: tuple[float, float],
    color: str,
    *,
    size: float = 0.72,
    font_size: int = 22,
) -> dict[str, object]:
    return {
        "id": atom_id,
        "label": label,
        "position": list(position),
        "shape": "circle",
        "width": size,
        "height": size,
        "color": color,
        "fill_color": color,
        "fill_opacity": 0.3,
        "font_size": font_size,
    }


def _bond(
    bond_id: str,
    source: str,
    target: str,
    color: str = SOFT,
    *,
    width: float = 5,
    label: str | None = None,
) -> dict[str, object]:
    bond: dict[str, object] = {
        "id": bond_id,
        "from": source,
        "to": target,
        "directed": False,
        "buff": 0.37,
        "color": color,
        "stroke_width": width,
    }
    if label:
        bond["label"] = label
        bond["font_size"] = 17
    return bond


def mechanism_diagram(
    state: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Return a stable-ID 2D projection of three concerted SN2 states."""

    if state not in STATE_X:
        raise ValueError(f"Unknown SN2 state: {state}")

    if state == "reactants":
        nu_x, br_x = -3.0, 1.75
        group_positions = {
            "r1": (0.0, 1.55),
            "r2": (-1.15, -1.15),
            "r3": (1.0, -1.2),
        }
    elif state == "transition":
        nu_x, br_x = -1.75, 1.75
        group_positions = {
            "r1": (0.0, 1.65),
            "r2": (-1.35, -0.9),
            "r3": (1.35, -0.9),
        }
    else:
        nu_x, br_x = -1.75, 3.0
        group_positions = {
            "r1": (0.0, -1.55),
            "r2": (-1.15, 1.15),
            "r3": (1.0, 1.2),
        }

    nodes = [
        _atom("nu", "HO⁻", (nu_x, 0.0), OXYGEN, size=0.9),
        _atom("center", "C*", (0.0, 0.0), CARBON, size=0.84),
        _atom("leaving", "Br", (br_x, 0.0), BROMINE, size=0.86),
        _atom("r1", "R¹", group_positions["r1"], GROUP_1),
        _atom("r2", "R²", group_positions["r2"], GROUP_2),
        _atom("r3", "R³", group_positions["r3"], GROUP_3),
    ]
    edges = [
        _bond("r1", "center", "r1"),
        _bond("r2", "center", "r2"),
        _bond("r3", "center", "r3"),
    ]
    if state == "reactants":
        edges.append(_bond("leaving", "center", "leaving", BROMINE, width=6))
    elif state == "transition":
        edges.extend(
            [
                _bond("forming", "nu", "center", FORMING, width=3, label="partial"),
                _bond(
                    "leaving",
                    "center",
                    "leaving",
                    BREAKING,
                    width=3,
                    label="partial",
                ),
            ]
        )
    else:
        edges.append(_bond("forming", "nu", "center", FORMING, width=6))
    return nodes, edges


def steric_access_diagram(
    crowded: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Backside-access comparison using the same general diagram vocabulary."""

    nodes = [
        _atom("nu", "Nu⁻", (-3.0, 0.0), FORMING, size=0.9),
        _atom("center", "C", (0.0, 0.0), CARBON, size=0.84),
        _atom("leaving", "LG", (2.0, 0.0), BROMINE, size=0.9),
    ]
    edges = [_bond("leaving", "center", "leaving", BROMINE, width=5)]
    radii = 1.45 if crowded else 1.15
    group_size = 1.3 if crowded else 0.72
    for index, angle in enumerate((math.pi / 2, 7 * math.pi / 6, 11 * math.pi / 6), 1):
        group_id = f"g{index}"
        nodes.append(
            _atom(
                group_id,
                "bulky" if crowded else "H",
                (radii * math.cos(angle), radii * math.sin(angle)),
                BREAKING if crowded else GROUP_2,
                size=group_size,
                font_size=17,
            )
        )
        edges.append(_bond(group_id, "center", group_id, width=4))
    edges.append(
        {
            "id": "approach",
            "from": "nu",
            "to": "center",
            "directed": True,
            "buff": 0.45,
            "color": BREAKING if crowded else FORMING,
            "stroke_width": 6,
            "label": "hindered" if crowded else "accessible",
            "font_size": 17,
        }
    )
    return nodes, edges
