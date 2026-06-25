"""Diagram primitives — grids, board marks, and other spatial visuals."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from manim import Circle, Line, Mobject, Text, VGroup, WHITE


def grid_dimensions(rows: int, cols: int, cell_size: float) -> tuple[float, float]:
    return cols * cell_size, rows * cell_size


def grid_cell_center(
    board_center: tuple[float, float, float],
    row: int,
    col: int,
    rows: int,
    cols: int,
    cell_size: float,
) -> tuple[float, float, float]:
    """Return canvas (x, y, z) for the center of cell (row, col). Row 0 = top."""
    x0, y0, z = board_center
    width, height = grid_dimensions(rows, cols, cell_size)
    x = x0 - width / 2 + (col + 0.5) * cell_size
    y = y0 + height / 2 - (row + 0.5) * cell_size
    return (x, y, z)


def parse_grid_content(content: Any) -> Dict[str, Any]:
    if isinstance(content, dict):
        return content
    return {}


def make_grid_board(
    rows: int = 3,
    cols: int = 3,
    cell_size: float = 1.0,
    *,
    stroke_color: str = "#888888",
    stroke_width: float = 4.0,
    draw_border: bool = True,
) -> VGroup:
    """Build a centered grid (origin = board center)."""
    width, height = grid_dimensions(rows, cols, cell_size)
    left = -width / 2
    right = width / 2
    top = height / 2
    bottom = -height / 2

    lines = VGroup()
    for i in range(1, cols):
        x = left + i * cell_size
        lines.add(Line([x, top, 0], [x, bottom, 0], color=stroke_color, stroke_width=stroke_width))
    for j in range(1, rows):
        y = top - j * cell_size
        lines.add(Line([left, y, 0], [right, y, 0], color=stroke_color, stroke_width=stroke_width))

    if draw_border:
        lines.add(Line([left, top, 0], [right, top, 0], color=stroke_color, stroke_width=stroke_width))
        lines.add(Line([right, top, 0], [right, bottom, 0], color=stroke_color, stroke_width=stroke_width))
        lines.add(Line([right, bottom, 0], [left, bottom, 0], color=stroke_color, stroke_width=stroke_width))
        lines.add(Line([left, bottom, 0], [left, top, 0], color=stroke_color, stroke_width=stroke_width))

    return lines


def make_grid_mark(symbol: str, cell_size: float) -> Mobject:
    """X or O mark sized for a grid cell."""
    sym = (symbol or "X").upper()
    if sym == "O":
        return Circle(
            radius=cell_size * 0.28,
            color="#5eb3ff",
            stroke_width=max(3.0, cell_size * 4),
        )
    return Text(
        "X",
        font_size=max(28, int(cell_size * 62)),
        color="#ff6b6b",
        weight="BOLD",
    )