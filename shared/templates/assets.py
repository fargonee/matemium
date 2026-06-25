"""Default assets.py template for Matemium agent-mode workspaces.

The Engine Room: computations, coordinate arrays, LaTeX strings, mesh data.
Imported by scenes.py — not the other way around.
"""

from __future__ import annotations


def example_values() -> tuple[float, float]:
    """Sample numeric helper for scenes.py."""
    return 2.0, 3.0


def example_latex() -> str:
    """Sample LaTeX string for add_math()."""
    return r"x^2 - 5x + 6 = 0"