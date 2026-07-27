"""Reviewed linguistic data for the language-learning flagship."""

from __future__ import annotations

SENTENCES = [
    {
        "language": "English",
        "text": "The student reads the book today.",
        "roles": ["ACTOR", "ACTION", "OBJECT", "TIME"],
        "tokens": ["The student", "reads", "the book", "today"],
        "note": "Position carries much of the role information.",
    },
    {
        "language": "Uzbek",
        "text": "Talaba bugun kitobni o‘qiydi.",
        "roles": ["ACTOR", "TIME", "OBJECT", "ACTION"],
        "tokens": ["Talaba", "bugun", "kitob-ni", "o‘qiydi"],
        "note": "-ni marks the definite direct object; the verb is sentence-final.",
    },
]

MORPHEMES = [("kitob", "book"), ("-ni", "definite direct-object marker")]
