"""Deterministic chemistry data for the SN2 flagship explanation.

The molecule is an intentionally generic tetrahedral stereocentre. ``R¹``,
``R²``, and ``R³`` preserve substituent identity while the 2D projection makes
Walden inversion inspectable. The drawing is a mechanistic teaching model, not
an optimized molecular geometry or a claim that bonds behave as springs.
"""

from __future__ import annotations

import math

import numpy as np
from manim import (
    PI,
    RIGHT,
    Arrow3D,
    Dot3D,
    Line3D,
    Rectangle,
    RoundedRectangle,
    Sphere,
    Text,
    VGroup,
)

from canvas import register_object_kind

BG = "#07131d"
WHITE = "#f5f8fb"
SOFT = "#b7c6d6"
CARBON = "#9aa4ad"
OXYGEN = "#ef5350"
BROMINE = "#8f354d"
HYDROGEN = "#f7f7f2"
FORMING = "#5ce1c6"
BREAKING = "#ff9f5a"
ENERGY = "#ffd166"
GROUP_1 = HYDROGEN
GROUP_2 = "#67b7ff"
GROUP_3 = "#78e08f"

STATE_X = {
    "reactants": 0.0,
    "transition": 0.5,
    "products": 1.0,
}

WORLD_SCALE = 1.18


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


# ---------------------------------------------------------------------------
# Project-local 3D reaction world
# ---------------------------------------------------------------------------


def reaction_world_state(
    progress: float,
    *,
    show_lone_pairs: bool = True,
    cue: str = "identity",
    show_energy: bool = False,
    show_reference_plane: bool = False,
    comparison: bool = False,
) -> dict[str, object]:
    """Serializable state for one spatial SN2 teaching model.

    ``progress`` is a reaction coordinate used to coordinate the same three
    authored states with the energy tape.  It is not molecular dynamics and
    does not claim a physically uniform time parameterization.
    """

    value = float(progress)
    if not 0.0 <= value <= 1.0:
        raise ValueError("SN2 reaction progress must be between 0 and 1")
    return {
        "progress": value,
        "show_lone_pairs": bool(show_lone_pairs),
        "cue": str(cue),
        "show_energy": bool(show_energy),
        "show_reference_plane": bool(show_reference_plane),
        "comparison": bool(comparison),
    }


def _sphere_at(point, radius: float, color: str, opacity: float = 0.92):
    return (
        Sphere(radius=radius, resolution=(18, 12))
        .set_fill(color, opacity=opacity)
        .set_stroke(color, width=0.7, opacity=min(opacity + 0.05, 1.0))
        .move_to(np.array(point, dtype=float))
    )


def _bond_between(start, end, color: str, *, thickness: float, opacity: float = 1.0):
    bond = Line3D(
        start=np.array(start, dtype=float),
        end=np.array(end, dtype=float),
        thickness=thickness,
        color=color,
        resolution=12,
    )
    bond.set_opacity(opacity)
    return bond


def _lone_pair_cluster(center, *, color: str, outward: float = 1.0):
    center = np.array(center, dtype=float)
    pairs = VGroup()
    for direction in (
        np.array([0.0, 0.72, 0.55]),
        np.array([0.0, -0.72, 0.55]),
        np.array([0.0, 0.0, -0.9]),
    ):
        anchor = center + outward * direction * 0.42
        tangent = np.array([0.0, -direction[2], direction[1]])
        tangent /= np.linalg.norm(tangent)
        pairs.add(
            Dot3D(anchor + tangent * 0.065, radius=0.035, color=color, resolution=(6, 6)),
            Dot3D(anchor - tangent * 0.065, radius=0.035, color=color, resolution=(6, 6)),
        )
    return pairs


def _standing_label(
    text: str,
    position,
    color: str = WHITE,
    *,
    font_size: int = 24,
    width: float | None = None,
    fill_opacity: float = 0.94,
) -> VGroup:
    """A high-contrast label facing the production's locked side camera."""

    label = Text(
        text,
        font="DejaVu Sans",
        font_size=font_size,
        weight="BOLD",
        color=color,
    )
    if width is not None and label.width > width - 0.24:
        label.scale_to_fit_width(width - 0.24)
    panel = RoundedRectangle(
        width=width or label.width + 0.34,
        height=label.height + 0.22,
        corner_radius=0.1,
        color=color,
        stroke_width=1.4,
        fill_color=BG,
        fill_opacity=fill_opacity,
    )
    group = VGroup(panel, label)
    group.rotate(PI / 2, axis=RIGHT)
    group.move_to(np.array(position, dtype=float))
    return group


def _attached_label(
    text: str,
    anchor,
    position,
    color: str,
    *,
    width: float,
    font_size: int = 23,
) -> VGroup:
    leader = Line3D(
        np.array(anchor, dtype=float),
        np.array(position, dtype=float),
        thickness=0.012,
        color=color,
        resolution=6,
    ).set_opacity(0.82)
    return VGroup(
        leader,
        _standing_label(text, position, color, font_size=font_size, width=width),
    )


def _dashed_bond(start, end, color: str, *, opacity: float) -> VGroup:
    """Seven cylindrical dashes with stable topology across reaction states."""

    start_v = np.array(start, dtype=float)
    delta = np.array(end, dtype=float) - start_v
    segments = VGroup()
    for index in range(7):
        a = (index + 0.10) / 7.0
        b = (index + 0.66) / 7.0
        segments.add(
            _bond_between(
                start_v + delta * a,
                start_v + delta * b,
                color,
                thickness=0.052,
                opacity=opacity,
            )
        )
    return segments


def _reference_plane() -> Rectangle:
    plane = Rectangle(
        width=3.15,
        height=3.45,
        stroke_color=ENERGY,
        stroke_width=1.5,
        fill_color=ENERGY,
        fill_opacity=0.07,
    )
    plane.rotate(PI / 2, axis=np.array([0.0, 1.0, 0.0]))
    return plane


def _main_molecule(content: dict[str, object]) -> tuple[VGroup, dict[str, VGroup]]:
    progress = float(content.get("progress", 0.0))
    cue = str(content.get("cue", "identity"))
    carbon = np.array([0.0, 0.0, 0.0])
    oxygen = np.array([-3.10 + 1.43 * progress, 0.0, 0.0])
    oxygen_h = oxygen + np.array([0.0, 0.12, 0.82])
    bromine = np.array([1.67 + 1.43 * progress, 0.0, 0.0])

    # A generic chiral carbon bears H, CH3, and CH2CH3. Their signed x-offset
    # crosses a fixed plane at the transition state: the umbrella inversion.
    umbrella_x = 0.58 * (1.0 - 2.0 * progress)
    substituent_points = (
        np.array([umbrella_x, 1.10, 0.92]),
        np.array([umbrella_x, -1.28, 0.42]),
        np.array([umbrella_x, 0.10, -1.34]),
    )

    carbon_atom = _sphere_at(carbon, 0.34, CARBON)
    oxygen_atom = _sphere_at(oxygen, 0.43, OXYGEN)
    oxygen_h_atom = _sphere_at(oxygen_h, 0.23, HYDROGEN)
    bromine_atom = _sphere_at(bromine, 0.49, BROMINE)
    r1 = _sphere_at(substituent_points[0], 0.27, GROUP_1)
    r2 = _sphere_at(substituent_points[1], 0.34, GROUP_2)
    r3 = _sphere_at(substituent_points[2], 0.37, GROUP_3)
    atoms = VGroup(carbon_atom, oxygen_atom, oxygen_h_atom, bromine_atom, r1, r2, r3)

    substituent_bonds = VGroup(
        *[
            _bond_between(carbon, point, SOFT, thickness=0.048, opacity=0.94)
            for point in substituent_points
        ],
        _bond_between(oxygen, oxygen_h, HYDROGEN, thickness=0.035, opacity=0.92),
    )

    # Full bonds fade into dashed partial bonds and back into a full product
    # bond. At progress=0.5 both partial bonds are equally prominent.
    partial_strength = max(0.0, math.sin(math.pi * progress))
    reactant_strength = max(0.0, 1.0 - 2.0 * progress)
    product_strength = max(0.0, 2.0 * progress - 1.0)
    forming_full = _bond_between(
        oxygen,
        carbon,
        FORMING,
        thickness=0.064,
        opacity=product_strength,
    )
    breaking_full = _bond_between(
        carbon,
        bromine,
        BROMINE,
        thickness=0.064,
        opacity=reactant_strength,
    )
    forming_partial = _dashed_bond(oxygen, carbon, FORMING, opacity=partial_strength)
    breaking_partial = _dashed_bond(carbon, bromine, BREAKING, opacity=partial_strength)
    forming_bond = VGroup(forming_full, forming_partial)
    breaking_bond = VGroup(breaking_full, breaking_partial)

    lone_pairs = _lone_pair_cluster(oxygen, color=OXYGEN, outward=1.0)
    if not bool(content.get("show_lone_pairs", True)):
        lone_pairs.set_opacity(0.0)

    reference = VGroup()
    if bool(content.get("show_reference_plane", False)):
        reference.add(_reference_plane())

    alignment = VGroup()
    if cue == "alignment":
        axis = _dashed_bond([-3.45, 0.0, 0.0], [3.0, 0.0, 0.0], SOFT, opacity=0.58)
        arrow = Arrow3D(
            start=[-3.55, -0.02, -0.72],
            end=[-0.72, -0.02, -0.72],
            color=FORMING,
            thickness=0.04,
            height=0.23,
            base_radius=0.075,
            resolution=10,
        )
        alignment.add(
            axis,
            arrow,
            _standing_label("BACKSIDE", [-2.55, -0.78, -1.18], FORMING, width=1.65),
            _standing_label(
                "LG SIDE",
                [2.00, -0.78, -1.18],
                BROMINE,
                width=1.48,
                font_size=23,
            ),
            _standing_label("180°", [0.0, -0.80, 1.72], ENERGY, width=1.25, font_size=26),
        )

    labels = VGroup()
    if cue in {"identity", "alignment"}:
        labels.add(
            _attached_label("C*", carbon, [0.05, -0.86, 0.67], CARBON, width=0.82),
            _attached_label("O", oxygen, [oxygen[0] + 0.32, -0.86, 0.72], OXYGEN, width=0.72),
            _attached_label("H", oxygen_h, [oxygen_h[0] + 0.45, -0.86, 1.22], HYDROGEN, width=0.72),
            _attached_label("Br", bromine, [bromine[0] - 0.38, -0.86, 0.78], BROMINE, width=0.88),
        )
    if cue == "identity":
        labels.add(
            _standing_label(
                "SN2 · ONE STEP",
                [0.0, -0.92, 2.42],
                ENERGY,
                width=3.25,
                font_size=31,
            ),
            _standing_label(
                "HO⁻ + R—Br  →  R—OH + Br⁻",
                [0.0, -0.92, -2.08],
                WHITE,
                width=4.95,
                font_size=25,
            ),
        )

    bond_labels = VGroup()
    if cue == "concerted" and 0.32 <= progress <= 0.68:
        bond_labels.add(
            _standing_label("FORMING", [-1.06, -0.90, -0.72], FORMING, width=1.55, font_size=22),
            _standing_label("BREAKING", [1.03, -0.90, -0.72], BREAKING, width=1.65, font_size=22),
            _standing_label(
                "[ HO···C···Br ]‡",
                [0.0, -0.92, 2.03],
                ENERGY,
                width=3.25,
                font_size=28,
            ),
        )

    molecule = VGroup(
        reference,
        alignment,
        substituent_bonds,
        forming_bond,
        breaking_bond,
        atoms,
        lone_pairs,
        labels,
        bond_labels,
    )
    parts = {
        "carbon": VGroup(carbon_atom),
        "oxygen": VGroup(oxygen_atom, oxygen_h_atom),
        "bromine": VGroup(bromine_atom),
        "r1": VGroup(r1),
        "r2": VGroup(r2),
        "r3": VGroup(r3),
        "substituents": VGroup(r1, r2, r3),
        "forming_bond": forming_bond,
        "breaking_bond": breaking_bond,
        "lone_pairs": lone_pairs,
        "axis": alignment,
        "labels": labels,
        "reference_plane": reference,
        "energy": VGroup(),
    }
    return molecule, parts


def _energy_panel(progress: float) -> VGroup:
    """A large, camera-facing energy coordinate driven by molecular progress."""

    x0, width = -3.10, 6.20
    z0, height = -3.30, 2.10

    def point(x: float, y: float) -> np.ndarray:
        normalized_y = (y + 0.22) / 1.24
        return np.array([x0 + width * x, 0.0, z0 + height * normalized_y])

    axes = VGroup(
        Arrow3D(
            start=[x0, 0.0, z0],
            end=[x0, 0.0, z0 + height + 0.18],
            color=SOFT,
            thickness=0.022,
            height=0.14,
            base_radius=0.045,
            resolution=7,
        ),
        Arrow3D(
            start=[x0, 0.0, z0],
            end=[x0 + width + 0.18, 0.0, z0],
            color=SOFT,
            thickness=0.022,
            height=0.14,
            base_radius=0.045,
            resolution=7,
        ),
    )
    # Forty-one samples are visually smooth at portrait scale without making
    # every world morph align an unnecessarily dense forest of 3D cylinders.
    samples = energy_points(41)
    curve = VGroup(
        *[
            _bond_between(point(x1, y1), point(x2, y2), ENERGY, thickness=0.025, opacity=0.98)
            for (x1, y1), (x2, y2) in zip(samples, samples[1:])
        ]
    )
    marker = _sphere_at(point(progress, activation_energy(progress)), 0.13, WHITE)
    labels = VGroup(
        _standing_label("POTENTIAL ENERGY", [-1.48, -0.58, z0 + height + 0.52], WHITE, width=3.15, font_size=26),
        _standing_label("REACTION PROGRESS →", [0.0, -0.58, z0 - 0.52], WHITE, width=3.75, font_size=26),
        _standing_label("REACTANTS", [x0 + 0.58, -0.55, z0 + 0.42], SOFT, width=1.78, font_size=21),
        _standing_label("TRANSITION STATE", [0.0, -0.55, z0 + height + 0.05], ENERGY, width=2.65, font_size=21),
        _standing_label("PRODUCTS", [x0 + width - 0.54, -0.55, z0 + 0.16], FORMING, width=1.68, font_size=21),
    )
    return VGroup(axes, curve, marker, labels)


def _inversion_model(progress: float, shift_x: float, title: str) -> VGroup:
    carbon = np.array([shift_x, 0.0, 0.0])
    umbrella_x = shift_x + 0.48 * (1.0 - 2.0 * progress)
    points = (
        np.array([umbrella_x, 0.88, 0.86]),
        np.array([umbrella_x, -1.00, 0.30]),
        np.array([umbrella_x, 0.08, -1.05]),
    )
    plane = _reference_plane().scale(0.78).move_to(carbon)
    atoms = VGroup(
        _sphere_at(carbon, 0.28, CARBON),
        _sphere_at(points[0], 0.23, GROUP_1),
        _sphere_at(points[1], 0.28, GROUP_2),
        _sphere_at(points[2], 0.31, GROUP_3),
    )
    bonds = VGroup(
        *[_bond_between(carbon, item, SOFT, thickness=0.043, opacity=0.96) for item in points]
    )
    return VGroup(
        plane,
        bonds,
        atoms,
        _standing_label(title, [shift_x, -0.84, 1.78], ENERGY, width=1.75, font_size=28),
        _standing_label("H", [shift_x - 0.25, -0.82, 1.22], GROUP_1, width=0.66, font_size=21),
        _standing_label("CH₃", [shift_x - 0.32, -0.82, 0.02], GROUP_2, width=0.96, font_size=20),
        _standing_label("CH₂CH₃", [shift_x - 0.12, -0.82, -1.48], GROUP_3, width=1.42, font_size=19),
    )


def _inversion_comparison() -> VGroup:
    arrow = Arrow3D(
        start=[-0.72, 0.0, 0.0],
        end=[0.72, 0.0, 0.0],
        color=FORMING,
        thickness=0.038,
        height=0.22,
        base_radius=0.07,
        resolution=9,
    )
    return VGroup(
        _inversion_model(0.0, -2.15, "BEFORE"),
        arrow,
        _inversion_model(1.0, 2.15, "AFTER"),
        _standing_label(
            "SAME CAMERA · SAME REFERENCE PLANE",
            [0.0, -0.86, -2.30],
            WHITE,
            width=4.95,
            font_size=25,
        ),
    )


def _build_sn2_world(elem, wrap, target_width, surface_factory):
    content = dict(elem.content or {})
    molecule, parts = _main_molecule(content)
    energy = VGroup()
    comparison = VGroup()

    # Keep three stable top-level slots while constructing expensive graph and
    # comparison geometry only for frames where it is visible. This avoids both
    # pathological root-group alignment and per-frame work on invisible solids.
    if bool(content.get("comparison", False)):
        molecule.scale(0.01).move_to(np.zeros(3)).set_opacity(0.0)
        comparison = _inversion_comparison().scale(1.08)
        parts["labels"] = comparison
        parts["reference_plane"] = comparison
    elif bool(content.get("show_energy", False)):
        molecule.scale(0.88).shift(np.array([0.0, 0.0, 2.45]))
        energy = _energy_panel(float(content.get("progress", 0.0)))
    else:
        molecule.scale(WORLD_SCALE)
    world = VGroup(molecule, energy, comparison)
    parts["energy"] = energy
    world.matemium_parts = parts
    return world


def _validate_sn2_world(content: object) -> list[str]:
    if not isinstance(content, dict):
        return ["content must be a mapping"]
    try:
        progress = float(content.get("progress", -1.0))
    except (TypeError, ValueError):
        return ["progress must be a number between 0 and 1"]
    if not 0.0 <= progress <= 1.0:
        return ["progress must be between 0 and 1"]
    cue = str(content.get("cue", "identity"))
    if cue not in {"identity", "alignment", "concerted", "energy", "inversion"}:
        return ["cue must be identity, alignment, concerted, energy, or inversion"]
    return []


def _sn2_world_parts(content: object) -> set[str]:
    return {
        "carbon",
        "oxygen",
        "bromine",
        "r1",
        "r2",
        "r3",
        "substituents",
        "forming_bond",
        "breaking_bond",
        "lone_pairs",
        "axis",
        "labels",
        "reference_plane",
        "energy",
    }


register_object_kind(
    "SN2ReactionWorld",
    build=_build_sn2_world,
    validate=_validate_sn2_world,
    parts=_sn2_world_parts,
)
