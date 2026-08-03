"""Reviewed, deterministic July Crisis data for the history flagship."""

from __future__ import annotations

BG = "#09131d"
WHITE = "#f4f8fc"
MUTED = "#71879a"
TRIGGER = "#ff6b6b"
DIPLOMACY = "#ffd166"
MOBILIZATION = "#c779ff"
WAR = "#ff9f5a"
ALTERNATIVE = "#5ce1a8"

EVENTS = [
    {"date": "28 JUN", "day": 0, "place": "Sarajevo", "event": "Franz Ferdinand and Sophie are assassinated", "kind": "trigger"},
    {"date": "05 JUL", "day": 7, "place": "Berlin", "event": "Germany promises strong support to Austria-Hungary", "kind": "decision"},
    {"date": "23 JUL", "day": 25, "place": "Vienna → Belgrade", "event": "Austria-Hungary delivers an ultimatum to Serbia", "kind": "decision"},
    {"date": "25 JUL", "day": 27, "place": "Belgrade", "event": "Serbia replies; mobilization begins", "kind": "mobilization"},
    {"date": "28 JUL", "day": 30, "place": "Vienna", "event": "Austria-Hungary declares war on Serbia", "kind": "war"},
    {"date": "30 JUL", "day": 32, "place": "St Petersburg", "event": "Russia orders general mobilization", "kind": "mobilization"},
    {"date": "01 AUG", "day": 34, "place": "Berlin", "event": "Germany declares war on Russia", "kind": "war"},
    {"date": "03 AUG", "day": 36, "place": "Berlin → Paris", "event": "Germany declares war on France", "kind": "war"},
    {"date": "04 AUG", "day": 37, "place": "Belgium / London", "event": "Germany invades Belgium; Britain declares war", "kind": "war"},
]

CAUSAL_LAYERS = [
    ("TRIGGER", "Sarajevo assassination", TRIGGER),
    ("STRUCTURES", "nationalism, imperial rivalry, militarization", MUTED),
    ("CONSTRAINTS", "alliances, credibility fears, mobilization plans", MOBILIZATION),
    ("DECISIONS", "support, ultimatum, mobilization, declarations", DIPLOMACY),
]

CONTINGENCIES = [
    ("ULTIMATUM", "Terms and Serbia’s reply left a diplomatic decision, not an automatic treaty action."),
    ("MEDIATION", "From 24 July, Britain proposed an international conference; escalation was still contested."),
    ("MOBILIZATION", "Plans made delay look dangerous, but orders remained consequential human choices."),
]


def event_color(kind: str) -> str:
    return {
        "trigger": TRIGGER,
        "decision": DIPLOMACY,
        "mobilization": MOBILIZATION,
        "war": WAR,
    }[kind]


def _node(
    node_id: str,
    label: str,
    position: tuple[float, float],
    color: str,
    *,
    width: float = 2.2,
) -> dict[str, object]:
    return {
        "id": node_id,
        "label": label,
        "position": list(position),
        "shape": "rounded",
        "width": width,
        "height": 0.9,
        "color": color,
        "fill_color": color,
        "fill_opacity": 0.2,
        "font_size": 18,
    }


def decision_network() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    nodes = [
        _node("germany", "GERMANY", (-4.5, 1.6), DIPLOMACY),
        _node("austria", "AUSTRIA-\nHUNGARY", (-1.5, 1.6), WAR),
        _node("serbia", "SERBIA", (1.5, 1.6), TRIGGER),
        _node("russia", "RUSSIA", (4.5, 1.6), MOBILIZATION),
        _node("france", "FRANCE", (4.5, -1.3), DIPLOMACY),
        _node("belgium", "BELGIUM", (0.8, -1.3), ALTERNATIVE),
        _node("britain", "BRITAIN", (-3.0, -1.3), MUTED),
    ]
    # Relationships are stated beside the node map in the scene. Keeping the
    # semantic nodes connector-free avoids arrowheads obscuring compact labels.
    return nodes, []


def geography_nodes() -> list[dict[str, object]]:
    """Schematic relative geography; deliberately not a 1914 border map."""

    return [
        _node("london", "LONDON", (-4.8, 1.7), MUTED, width=1.8),
        _node("paris", "PARIS", (-3.2, 0.0), DIPLOMACY, width=1.8),
        _node("berlin", "BERLIN", (-0.8, 1.1), DIPLOMACY, width=1.8),
        _node("vienna", "VIENNA", (1.2, 0.1), WAR, width=1.8),
        _node("belgrade", "BELGRADE", (2.6, -1.4), TRIGGER, width=2.0),
        _node("sarajevo", "SARAJEVO", (1.0, -2.0), TRIGGER, width=2.0),
        _node("petersburg", "ST PETERSBURG", (4.8, 1.6), MOBILIZATION, width=2.6),
    ]
