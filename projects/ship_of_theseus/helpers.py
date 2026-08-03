"""Structured identity criteria and procedural ship states."""

from __future__ import annotations

BG = "#0b1120"
WHITE = "#f5f7fb"
MUTED = "#8090a6"
ORIGINAL = "#62b6ff"
REPLACEMENT = "#ffbe55"
SUPPORT = "#62d6a7"
OBJECTION = "#ff718b"
QUESTION = "#b58cff"

DEFINITIONS = [
    (
        "QUALITATIVE SAMENESS",
        "sharing properties or looking alike; more than one object can qualify",
    ),
    (
        "NUMERICAL IDENTITY",
        "being one and the very same object; identity is one-to-one",
    ),
]

ACCOUNTS = [
    {
        "criterion": "ORIGINAL MATTER",
        "supports": "Saved planks preserve the ship’s original material.",
        "objection": "If one repair destroys identity, ordinary persistence becomes fragile.",
    },
    {
        "criterion": "CONTINUOUS CAREER",
        "supports": "The repaired ship keeps sailing through one continuous history.",
        "objection": "Continuity may preserve identity after every original plank is gone.",
    },
    {
        "criterion": "FORM + FUNCTION",
        "supports": "The organized, working ship persists through repair.",
        "objection": "Two ships can share the same design and function.",
    },
    {
        "criterion": "CAUSAL HISTORY",
        "supports": "Each repaired stage develops directly from the previous one.",
        "objection": "The stored planks also acquire a history leading to reconstruction.",
    },
]

TRANSFER_CASES = [
    ("BODY", "cells and implants change while a life continues"),
    ("ORGANIZATION", "members change while roles and records persist"),
    ("DIGITAL FILE", "storage bits move while informational continuity is tracked"),
]


def _node(
    node_id: str,
    label: str,
    position: tuple[float, float],
    color: str,
    *,
    width: float = 1.35,
    height: float = 0.68,
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


def ship_nodes(replaced: int, *, prefix: str = "ship") -> list[dict[str, object]]:
    """Five addressable planks plus mast; ``replaced`` is clamped to 0..5."""

    count = max(0, min(5, replaced))
    nodes = [
        _node(
            f"{prefix}_plank_{index}",
            f"P{index}",
            (-3.0 + index * 1.5, -0.35),
            REPLACEMENT if index <= count else ORIGINAL,
        )
        for index in range(1, 6)
    ]
    nodes.append(_node(f"{prefix}_mast", "MAST", (0.0, 1.0), MUTED, width=1.1))
    return nodes


def replacement_storyboard() -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []
    for row, (label, replaced) in enumerate((("S₀ · 0/5", 0), ("S₂ · 2/5", 2), ("S₅ · 5/5", 5))):
        y = 1.8 - row * 1.8
        nodes.append(_node(f"stage_{row}", label, (-5.1, y), QUESTION, width=1.8))
        for index in range(1, 6):
            color = REPLACEMENT if index <= replaced else ORIGINAL
            nodes.append(
                _node(
                    f"stage_{row}_plank_{index}",
                    f"P{index}",
                    (-3.3 + index * 1.45, y),
                    color,
                    width=1.1,
                    height=0.58,
                    font_size=14,
                )
            )
    return nodes


def rival_claimants() -> list[dict[str, object]]:
    nodes = [
        _node("ship_a_label", "A · CONTINUOUS\nWORKING SHIP", (-4.7, 1.3), SUPPORT, width=2.4),
        _node("ship_b_label", "B · REBUILT\nORIGINAL PLANKS", (-4.7, -1.3), ORIGINAL, width=2.4),
    ]
    for index in range(1, 6):
        x = -1.8 + index * 1.35
        nodes.append(_node(f"a_{index}", f"R{index}", (x, 1.3), REPLACEMENT, width=1.0))
        nodes.append(_node(f"b_{index}", f"P{index}", (x, -1.3), ORIGINAL, width=1.0))
    return nodes
