"""Reviewed structured data for one English–Uzbek sentence transformation."""

from __future__ import annotations

BG = "#091421"
WHITE = "#f4f8fc"
MUTED = "#7f93a8"
ACTOR = "#61b8ff"
ACTION = "#ffbf5a"
OBJECT = "#c58cff"
TIME = "#5ed6a7"
MARKER = "#ff718b"

ROLE_COLORS = {
    "actor": ACTOR,
    "action": ACTION,
    "object": OBJECT,
    "time": TIME,
}

SENTENCES = {
    "english": {
        "language": "ENGLISH",
        "text": "The student is reading the book today.",
        "order": ["actor", "action", "object", "time"],
        "tokens": {
            "actor": "the student",
            "action": "is reading",
            "object": "the book",
            "time": "today",
        },
        "pattern": "ACTOR — ACTION — OBJECT — TIME",
        "note": "In this neutral example, position helps identify subject and object.",
    },
    "uzbek": {
        "language": "UZBEK",
        "text": "Talaba bugun kitobni o‘qiyapti.",
        "order": ["actor", "time", "object", "action"],
        "tokens": {
            "actor": "talaba",
            "action": "o‘qiyapti",
            "object": "kitobni",
            "time": "bugun",
        },
        "pattern": "ACTOR — TIME — OBJECT-ni — ACTION",
        "note": "This neutral order is verb-final; -ni marks the definite direct object.",
    },
}

MORPHEMES = [
    {
        "surface": "kitob-ni",
        "parts": "kitob  +  -ni",
        "gloss": "book  +  definite direct-object marker",
    },
    {
        "surface": "o‘qi-yap-ti",
        "parts": "o‘qi  +  -yap  +  -ti",
        "gloss": "read  +  progressive  +  third-person form",
    },
]

READING_STEPS = [
    ("1", "Talaba", "actor"),
    ("2", "bugun", "time"),
    ("3", "kitobni", "object"),
    ("4", "o‘qiyapti", "action"),
]


def _node(
    node_id: str,
    label: str,
    position: tuple[float, float],
    color: str,
    *,
    width: float = 2.5,
    height: float = 1.05,
    font_size: int = 17,
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


def sentence_nodes(language: str) -> list[dict[str, object]]:
    sentence = SENTENCES[language]
    order = list(sentence["order"])
    tokens = dict(sentence["tokens"])
    x_positions = (-4.5, -1.5, 1.5, 4.5)
    return [
        _node(
            role,
            f"{role.upper()}\n{tokens[role]}",
            (x_positions[index], 0.0),
            ROLE_COLORS[role],
        )
        for index, role in enumerate(order)
    ]


def contrast_nodes() -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []
    for row, language in enumerate(("english", "uzbek")):
        sentence = SENTENCES[language]
        y = 1.45 if row == 0 else -1.45
        nodes.append(_node(f"{language}_label", str(sentence["language"]), (-5.7, y), MUTED, width=1.7))
        for index, role in enumerate(sentence["order"]):
            nodes.append(
                _node(
                    f"{language}_{role}",
                    str(sentence["tokens"][role]),
                    (-3.6 + index * 2.45, y),
                    ROLE_COLORS[str(role)],
                    width=2.05,
                    height=0.8,
                    font_size=15,
                )
            )
    return nodes


def meaning_nodes() -> list[dict[str, object]]:
    meanings = {
        "actor": "student",
        "action": "read",
        "object": "book",
        "time": "today",
    }
    return [
        _node(
            f"meaning_{role}",
            f"{role.upper()}\n{meanings[role]}",
            (-4.5 + index * 3.0, 0.0),
            ROLE_COLORS[role],
        )
        for index, role in enumerate(("actor", "action", "object", "time"))
    ]


def reading_nodes() -> list[dict[str, object]]:
    return [
        _node(
            f"reading_{role}",
            f"{number} · {token}",
            (-4.5 + index * 3.0, 0.0),
            ROLE_COLORS[role],
            width=2.45,
            height=0.85,
        )
        for index, (number, token, role) in enumerate(READING_STEPS)
    ]
