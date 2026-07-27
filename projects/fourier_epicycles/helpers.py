"""Deterministic data and visual recipes for the Fourier flagship.

The engine receives only sampled, serializable paths, plots, and diagrams.
Fourier mathematics and the visual grammar stay project-local here.
"""

from __future__ import annotations

from math import cos, pi, sin
from typing import Iterable


BACKGROUND = "#07111F"
INK = "#EAF2FF"
MUTED = "#8EA3BC"
REFERENCE = "#52657A"
ACCENT = "#FFD166"
HARMONIC_COLORS = (
    "#38BDF8",  # cyan
    "#A78BFA",  # violet
    "#FB7185",  # coral
    "#34D399",  # mint
    "#FBBF24",  # amber
    "#60A5FA",  # blue
    "#F472B6",  # pink
    "#2DD4BF",  # teal
)


def square_wave_terms(count: int = 5) -> list[dict[str, float | str]]:
    """Return odd-harmonic terms for a unit square wave."""
    if count < 1:
        raise ValueError("count must be positive")
    return [
        {
            "harmonic": n,
            "amplitude": 4.0 / (pi * n),
            "phase": 0.0,
            "color": HARMONIC_COLORS[index % len(HARMONIC_COLORS)],
        }
        for index, n in enumerate(range(1, 2 * count, 2))
    ]


def partial_sum(t: float, term_count: int) -> float:
    """Evaluate the odd-harmonic square-wave partial sum."""
    return sum(
        float(term["amplitude"]) * sin(int(term["harmonic"]) * t)
        for term in square_wave_terms(term_count)
    )


def partial_sum_tex(term_count: int) -> str:
    terms = [rf"\frac{{\sin({n}t)}}{{{n}}}" for n in range(1, 2 * term_count, 2)]
    return r"s_N(t)=\frac{4}{\pi}\left(" + "+".join(terms) + r"\right)"


def sample_function(
    function,
    x_min: float,
    x_max: float,
    *,
    samples: int = 121,
) -> list[list[float]]:
    """Sample a scalar function into the generic ``DataPlot`` schema."""
    if samples < 2:
        raise ValueError("samples must be at least two")
    step = (x_max - x_min) / (samples - 1)
    return [[x := x_min + index * step, float(function(x))] for index in range(samples)]


def square_reference_points(
    x_min: float = -pi,
    x_max: float = pi,
    *,
    samples: int = 161,
) -> list[list[float]]:
    """A quiet reference square wave; samples avoid claiming a value at the jump."""
    return sample_function(
        lambda x: 1.0 if sin(x) >= 0 else -1.0,
        x_min,
        x_max,
        samples=samples,
    )


def harmonic_wave_series(
    count: int,
    *,
    x_min: float = -pi,
    x_max: float = pi,
) -> list[dict]:
    """Individual harmonic contributions with stable cross-view colors."""
    result: list[dict] = []
    for term in square_wave_terms(count):
        harmonic = int(term["harmonic"])
        amplitude = float(term["amplitude"])
        result.append(
            {
                "id": f"h{harmonic}",
                "points": sample_function(
                    lambda x, n=harmonic, a=amplitude: a * sin(n * x),
                    x_min,
                    x_max,
                ),
                "color": term["color"],
                "stroke_width": 4.0 if harmonic == 1 else 2.8,
                "smooth": True,
            }
        )
    return result


def reconstruction_plot_content(
    term_count: int,
    *,
    phase: float | None = None,
    detailed: bool = False,
) -> dict:
    """Content for a target/partial-sum plot and optional synchronized marker."""
    x_min, x_max = (-0.8, 0.8) if detailed else (-pi, pi)
    samples = 181 if detailed else 151
    content = {
        "series": [
            {
                "id": "target",
                "points": square_reference_points(x_min, x_max, samples=samples),
                "color": REFERENCE,
                "stroke_width": 2.2,
                "smooth": False,
            },
            {
                "id": "sum",
                "points": sample_function(
                    lambda x: partial_sum(x, term_count),
                    x_min,
                    x_max,
                    samples=samples,
                ),
                "color": ACCENT,
                "stroke_width": 5.2,
                "smooth": True,
            },
        ],
        "markers": [],
        "x_range": [x_min, x_max, (x_max - x_min) / 4],
        "y_range": [-1.55, 1.55, 0.5],
        "width": 7.2 if detailed else 7.6,
        "height": 3.8,
        "tips": False,
    }
    if phase is not None:
        content["markers"] = [
            {
                "id": "phase",
                "point": [phase, partial_sum(phase, term_count)],
                "color": ACCENT,
                "radius": 0.095,
            }
        ]
    return content


def spectrum_plot_content(count: int = 7) -> dict:
    """A stem-like spectrum built from generic sampled series."""
    series: list[dict] = []
    for term in square_wave_terms(count):
        harmonic = int(term["harmonic"])
        series.append(
            {
                "id": f"h{harmonic}",
                "points": [[harmonic, 0.0], [harmonic, float(term["amplitude"])]],
                "color": term["color"],
                "stroke_width": 8.0,
                "smooth": False,
            }
        )
    return {
        "series": series,
        "x_range": [0, 2 * count, 2],
        "y_range": [0, 1.45, 0.25],
        "width": 8.2,
        "height": 3.7,
        "tips": False,
        "smooth": False,
    }


def epicycle_diagram_content(
    phase: float,
    *,
    term_count: int = 5,
    scale: float = 1.7,
) -> dict:
    """Build one phase of an epicycle chain as a semantic diagram.

    Each odd harmonic contributes a circle and a directed radius.  The endpoint
    of one vector is the centre of the next circle.
    """
    terms = square_wave_terms(term_count)
    nodes: list[dict] = []
    edges: list[dict] = []
    x, y = 0.0, 0.0
    for index, term in enumerate(terms):
        harmonic = int(term["harmonic"])
        amplitude = scale * float(term["amplitude"])
        color = str(term["color"])
        center_id = f"center_{harmonic}"
        tip_id = f"tip_{harmonic}"
        next_x = x + amplitude * cos(harmonic * phase)
        next_y = y + amplitude * sin(harmonic * phase)
        nodes.append(
            {
                "id": center_id,
                "label": " ",
                "position": [x, y],
                "shape": "circle",
                "width": 2 * amplitude,
                "height": 2 * amplitude,
                "color": color,
                "fill_color": color,
                "fill_opacity": 0.035,
                "font_size": 1,
            }
        )
        nodes.append(
            {
                "id": tip_id,
                "label": " ",
                "position": [next_x, next_y],
                "shape": "circle",
                "width": 0.10,
                "height": 0.10,
                "color": color,
                "fill_color": color,
                "fill_opacity": 1.0,
                "font_size": 1,
            }
        )
        edges.append(
            {
                "id": f"vector_{harmonic}",
                "from": center_id,
                "to": tip_id,
                "directed": True,
                "buff": 0.02,
                "color": color,
                "stroke_width": 4.2 if index == 0 else 3.2,
            }
        )
        x, y = next_x, next_y
    return {"nodes": nodes, "edges": edges}


def one_rotation_plot_content(phase: float) -> dict:
    """Circle-derived sine wave with a marker at the same phase."""
    return {
        "series": [
            {
                "id": "sine",
                "points": sample_function(sin, 0.0, 2 * pi, samples=121),
                "color": HARMONIC_COLORS[0],
                "stroke_width": 5.0,
                "smooth": True,
            }
        ],
        "markers": [
            {
                "id": "projection",
                "point": [phase, sin(phase)],
                "color": ACCENT,
                "radius": 0.105,
            }
        ],
        "x_range": [0, 2 * pi, pi / 2],
        "y_range": [-1.3, 1.3, 0.5],
        "width": 7.4,
        "height": 3.7,
        "tips": False,
    }


def legend_runs(terms: Iterable[dict]) -> list[dict]:
    """Inline rich text legend using the same colors as every representation."""
    runs: list[dict] = []
    for index, term in enumerate(terms):
        if index:
            runs.append({"text": "   "})
        harmonic = int(term["harmonic"])
        runs.append(
            {
                "text": f"● n={harmonic}",
                "color": str(term["color"]),
                "bold": True,
            }
        )
    return runs
