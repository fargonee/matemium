"""Parse ``z = f(x, y)`` equations into Manim 3D surfaces."""

from __future__ import annotations

import ast
import math
import operator
import re
from typing import Callable, Optional

import numpy as np
from manim import DEGREES, UP, Mobject, Surface

# Default fallback when parsing fails (distinct from the old always-saddle bug path).
_FALLBACK_EXPR = "x**2 - y**2"

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_FUNCS = {
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "exp": np.exp,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "log": np.log,
}

_NAMES = {
    "pi": math.pi,
    "e": math.e,
}


def _strip_z_equals(equation: str) -> str:
    text = equation.strip()
    match = re.match(r"^z\s*=\s*(.+)$", text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else text


def _latex_to_python(expr: str) -> str:
    s = expr.strip()
    replacements = [
        (r"\\sin", "sin"),
        (r"\\cos", "cos"),
        (r"\\tan", "tan"),
        (r"\\sqrt", "sqrt"),
        (r"\\pi", "pi"),
        (r"\\cdot", "*"),
        (r"\\times", "*"),
        (r"\\left", ""),
        (r"\\right", ""),
    ]
    for pattern, repl in replacements:
        s = re.sub(pattern, repl, s)
    s = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
    s = s.replace("^", "**")
    return s


def _insert_implicit_multiplication(expr: str) -> str:
    s = expr
    s = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", s)
    s = re.sub(r"([a-zA-Z])(\()", r"\1*\2", s)
    s = re.sub(r"(\))\s*(\()", r")\1*\2", s)
    s = re.sub(r"(\))\s+([a-z])", r")\1*\2", s)
    s = re.sub(r"(\))([a-zA-Z])", r")\1*\2", s)
    # Single-letter variables only (avoid breaking sin/cos/tan/exp/sqrt).
    s = re.sub(r"(?<![a-zA-Z])([xy])(?=[xy])", r"\1*", s)
    return s


class _SafeEval(ast.NodeVisitor):
    """Evaluate simple scalar math expressions in x and y."""

    def __init__(self, x: float, y: float):
        self._x = x
        self._y = y

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id == "x":
                return self._x
            if node.id == "y":
                return self._y
            if node.id in _NAMES:
                return _NAMES[node.id]
            raise ValueError(f"Unknown name: {node.id}")
        if isinstance(node, ast.BinOp):
            op = _BINOPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op)}")
            return op(self.visit(node.left), self.visit(node.right))
        if isinstance(node, ast.UnaryOp):
            op = _BINOPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op)}")
            return op(self.visit(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only simple function calls are supported")
            fn = _FUNCS.get(node.func.id)
            if fn is None:
                raise ValueError(f"Unsupported function: {node.func.id}")
            args = [self.visit(arg) for arg in node.args]
            return float(fn(*args))
        raise ValueError(f"Unsupported expression node: {type(node)}")


def compile_z_equation(equation: Optional[str]) -> Callable[[float, float], float]:
    """Compile ``z = f(x, y)`` into a callable. Falls back to a saddle on parse errors."""
    raw = _strip_z_equals(equation or _FALLBACK_EXPR)
    py_expr = _insert_implicit_multiplication(_latex_to_python(raw))
    try:
        tree = ast.parse(py_expr, mode="eval")
    except SyntaxError:
        py_expr = _FALLBACK_EXPR
        tree = ast.parse(py_expr, mode="eval")

    def evaluate(x: float, y: float) -> float:
        try:
            value = float(_SafeEval(x, y).visit(tree))
            if not math.isfinite(value):
                raise ValueError("non-finite")
            return value
        except Exception:
            return float(_SafeEval(x, y).visit(ast.parse(_FALLBACK_EXPR, mode="eval")))

    return evaluate


def _z_scale(func: Callable[[float, float], float], xy_span: float = 2.5) -> float:
    """Scale raw z values so the surface fits nicely in the viewport."""
    xs = np.linspace(-xy_span, xy_span, 18)
    ys = np.linspace(-xy_span, xy_span, 18)
    values = []
    for x in xs:
        for y in ys:
            try:
                z = func(float(x), float(y))
                if math.isfinite(z):
                    values.append(z)
            except Exception:
                continue
    if not values:
        return 0.35
    z_min, z_max = min(values), max(values)
    span = max(z_max - z_min, abs(z_max), abs(z_min), 1e-3)
    target = 1.6
    return min(1.2, target / span)


def make_surface_from_equation(
    equation: Optional[str],
    *,
    preview: bool = False,
) -> Mobject:
    """Build a Manim ``Surface`` from a ``z = f(x, y)`` equation string."""
    func = compile_z_equation(equation)
    z_scale = _z_scale(func)
    xy_span = 2.2 if preview else 2.5
    resolution = (8, 8) if preview else (16, 16)

    def param_surface(u: float, v: float) -> np.ndarray:
        z = func(u, v) * z_scale
        return np.array([u, v, z], dtype=float)

    surf = Surface(
        param_surface,
        u_range=[-xy_span, xy_span],
        v_range=[-xy_span, xy_span],
        resolution=resolution,
        fill_color="#3388ff",
        fill_opacity=0.65,
        stroke_width=0.8 if preview else 1.0,
        stroke_color="#aaddff",
    )
    if not preview:
        surf.scale(0.85)
        surf.rotate(18 * DEGREES, axis=UP)
    return surf