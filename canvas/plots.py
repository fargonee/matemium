"""2D quadratic function plots — axes, curves, tracing dots, side-by-side compare."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from manim import (
    DOWN,
    RIGHT,
    UP,
    UR,
    Axes,
    Dot,
    MathTex,
    Mobject,
    Text,
    VGroup,
    WHITE,
    YELLOW,
)


@dataclass
class PlotPart:
    """Runtime handles for one quadratic plot inside a composite mobject."""

    group: VGroup
    axes: Axes
    curve: Mobject
    dot: Dot
    formula: MathTex
    readout: Optional[Mobject]
    a: float
    b: float
    c: float
    x_range: Tuple[float, float]

    def y_at(self, x: float) -> float:
        return self.a * x * x + self.b * x + self.c

    def point_at(self, x: float) -> np.ndarray:
        return self.axes.c2p(x, self.y_at(x))


def quad_y(a: float, b: float, c: float, x: float) -> float:
    return a * x * x + b * x + c


def format_quadratic_tex(a: float, b: float, c: float) -> str:
    """Build ``y = ax^2 + bx + c`` LaTeX from coefficients."""
    pieces: list[str] = []
    if a != 0:
        if a == 1:
            pieces.append("x^2")
        elif a == -1:
            pieces.append("-x^2")
        else:
            pieces.append(f"{a}x^2")
    if b != 0:
        if not pieces:
            pieces.append("x" if b == 1 else "-x" if b == -1 else f"{b}x")
        elif b == 1:
            pieces.append(" + x")
        elif b == -1:
            pieces.append(" - x")
        elif b > 0:
            pieces.append(f" + {b}x")
        else:
            pieces.append(f" - {abs(b)}x")
    if c != 0:
        cval = int(c) if c == int(c) else c
        if not pieces:
            pieces.append(str(cval))
        elif c > 0:
            pieces.append(f" + {cval}")
        else:
            pieces.append(f" - {abs(cval)}")
    if not pieces:
        pieces.append("0")
    return r"y = " + "".join(pieces)


def _auto_y_range(a: float, b: float, c: float, x_range: Tuple[float, float]) -> Tuple[float, float]:
    xs = np.linspace(x_range[0], x_range[1], 40)
    ys = [quad_y(a, b, c, float(x)) for x in xs]
    if a != 0:
        xv = -b / (2 * a)
        if x_range[0] <= xv <= x_range[1]:
            ys.append(quad_y(a, b, c, xv))
    y_min, y_max = min(ys), max(ys)
    pad = max(0.8, (y_max - y_min) * 0.18)
    return y_min - pad, y_max + pad


def parse_plot_spec(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def make_quadratic_plot(
    a: float,
    b: float,
    c: float,
    *,
    formula: Optional[str] = None,
    x_range: Tuple[float, float] = (-3.0, 3.0),
    plot_width: float = 2.8,
    plot_height: float = 2.0,
    x_start: float = 0.0,
    show_readout: bool = True,
    stroke_color: str = "#5eb3ff",
) -> Tuple[VGroup, PlotPart]:
    """Build one labeled quadratic plot centered at the origin."""
    y_lo, y_hi = _auto_y_range(a, b, c, x_range)
    axes = Axes(
        x_range=[x_range[0], x_range[1], 1],
        y_range=[y_lo, y_hi, max(1, round((y_hi - y_lo) / 4, 1))],
        x_length=plot_width * 0.82,
        y_length=plot_height * 0.62,
        axis_config={"color": "#666666", "stroke_width": 2, "include_tip": False},
    )

    curve = axes.plot(
        lambda x: quad_y(a, b, c, x),
        x_range=list(x_range),
        color=stroke_color,
        stroke_width=3,
    )

    dot = Dot(radius=0.07, color=YELLOW)
    x0 = float(np.clip(x_start, x_range[0], x_range[1]))
    dot.move_to(axes.c2p(x0, quad_y(a, b, c, x0)))

    tex = formula or format_quadratic_tex(a, b, c)
    formula_mob = MathTex(tex, color=WHITE).scale(0.42)
    formula_mob.next_to(axes, DOWN, buff=0.22)

    x_label = MathTex("x", color="#aaaaaa").scale(0.38)
    x_label.next_to(axes.x_axis, RIGHT, buff=0.08)
    y_label = MathTex("y", color="#aaaaaa").scale(0.38)
    y_label.next_to(axes.y_axis, UP, buff=0.08)

    readout = None
    if show_readout:
        readout = Text(
            f"x = {x0:.1f},  y = {quad_y(a, b, c, x0):.1f}",
            font_size=18,
            color="#ffdd66",
        )
        readout.next_to(dot, UR, buff=0.08)

    group = VGroup(axes, curve, dot, formula_mob, x_label, y_label)
    if readout is not None:
        group.add(readout)

    part = PlotPart(
        group=group,
        axes=axes,
        curve=curve,
        dot=dot,
        formula=formula_mob,
        readout=readout,
        a=a,
        b=b,
        c=c,
        x_range=x_range,
    )
    return group, part


def make_quadratic_plot_pair(
    left: Dict[str, Any],
    right: Dict[str, Any],
    *,
    gap: float = 0.55,
    plot_width: float = 2.65,
    plot_height: float = 2.05,
) -> Tuple[VGroup, List[PlotPart]]:
    """Two quadratic plots side by side in one composite mobject."""
    left_g, left_p = make_quadratic_plot(
        float(left.get("a", 1)),
        float(left.get("b", 0)),
        float(left.get("c", 0)),
        formula=left.get("formula"),
        x_range=tuple(left.get("x_range", (-2.5, 3.5))),
        plot_width=plot_width,
        plot_height=plot_height,
        x_start=float(left.get("x_start", 0)),
        show_readout=bool(left.get("show_readout", True)),
        stroke_color=str(left.get("color", "#5eb3ff")),
    )
    right_g, right_p = make_quadratic_plot(
        float(right.get("a", 1)),
        float(right.get("b", 0)),
        float(right.get("c", 0)),
        formula=right.get("formula"),
        x_range=tuple(right.get("x_range", (-2.5, 3.5))),
        plot_width=plot_width,
        plot_height=plot_height,
        x_start=float(right.get("x_start", 0)),
        show_readout=bool(right.get("show_readout", True)),
        stroke_color=str(right.get("color", "#ff8a65")),
    )

    pair = VGroup(left_g, right_g)
    pair.arrange(buff=gap)
    parts = [left_p, right_p]
    return pair, parts


def attach_plot_parts(mob: Mobject, parts: List[PlotPart]) -> None:
    mob._matemium_plot_parts = parts  # type: ignore[attr-defined]


def get_plot_parts(mob: Mobject) -> List[PlotPart]:
    return list(getattr(mob, "_matemium_plot_parts", ()))


def get_plot_part(mob: Mobject, index: int = 0) -> Optional[PlotPart]:
    parts = get_plot_parts(mob)
    if 0 <= index < len(parts):
        return parts[index]
    return None


def pair_dimensions(
    plot_width: float = 2.65,
    plot_height: float = 2.05,
    gap: float = 0.55,
) -> Tuple[float, float]:
    return plot_width * 2 + gap + 0.4, plot_height + 0.9