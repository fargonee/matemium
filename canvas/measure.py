"""Unified measurement and mobject construction for Matemium.

Renderer-agnostic by design:
- Layout decisions (positions + sizes) can be driven by any MeasurementBackend.
- The default is Manim-backed (for final video fidelity).
- The desktop preview can use (or request measurements via) a KaTeX / manim-web compatible backend
  so that the manim-web player sees *exactly* the same metrics used for authoring layout.

This is the foundation that lets us have a true 1-1 manim-web powered live preview.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, TYPE_CHECKING

from manim import UP, MathTex, Mobject, Text, VGroup, WHITE

from .diagrams import (
    grid_dimensions,
    make_grid_board,
    make_grid_mark,
    parse_grid_content,
)
from .plots import (
    attach_plot_parts,
    make_quadratic_plot,
    make_quadratic_plot_pair,
    pair_dimensions,
    parse_plot_spec,
)
from .dsl import CanvasElement, LayoutBox
from .rich_text import build_plain_or_rich_mobject, is_rich_content, plain_text_for_content
from .solid_labels import attach_labels_to_solid
from .solids import make_solid, make_solid_group, parse_solid_content, solid_footprint_size
from .surfaces import make_surface_from_equation

if TYPE_CHECKING:
    from .measurement import MeasurementBackend, BoundingBox3D
from .measurement import BoundingBox3D

DEFAULT_TEXT_FONT_SIZE = 36
DEFAULT_MATH_SCALE = 0.9

# Pluggable backend (renderer agnostic support)
_CURRENT_BACKEND: Optional["MeasurementBackend"] = None

# Extension point for custom / lesson-specific element types.
# This is how we avoid constantly patching the core engine for every new
# visualization pattern (plots, diagrams, solids, etc.).
#
# Preferred usage: register from project helpers or a small shared layer.
# The goal is to keep canvas/ focused on the generic sheet + styling + layout
# machinery.
_CUSTOM_BUILDERS: dict[str, Callable[[CanvasElement, bool, Optional[float], SurfaceFactory], Optional[Mobject]]] = {}

# Phase 9: full registration for object kinds to support extensibility in 3D world + sheet.
# Allows registering new viz types without patching core.
_OBJECT_KINDS: dict[str, dict] = {}


def register_object_kind(
    name: str,
    *,
    build: Optional[Callable] = None,
    measure: Optional[Callable] = None,
    observe: Optional[Callable] = None,
    preview: Optional[Callable] = None,
) -> None:
    """Register a custom object kind for the 3D world / sheet model (Phase 9).

    Example:
        def build_my_viz(elem, ...): ...
        def measure_my_viz(obj, ...): ...
        def observe_my_viz(target, ...): ...
        register_object_kind("MyDiagram", build=build_my_viz, measure=measure_my_viz, observe=observe_my_viz)

    Then use: builder.add_object("MyDiagram", position=..., ...)
    """
    _OBJECT_KINDS[name] = {
        "build": build,
        "measure": measure,
        "observe": observe,
        "preview": preview,
    }
    if build:
        _CUSTOM_BUILDERS[name] = build


def register_element_builder(
    type_name: str,
    builder: Callable[[CanvasElement, bool, Optional[float], SurfaceFactory], Optional[Mobject]],
) -> None:
    """Register a builder for a custom CanvasElement type (legacy compat).

    Example (in a project helpers.py):
        def _build_my_viz(elem, wrap, tw, factory):
            ...
        register_element_builder("MySpecialPlot", _build_my_viz)
    """
    _CUSTOM_BUILDERS[type_name] = builder


def set_measurement_backend(backend: "MeasurementBackend") -> None:
    """Inject a different measurement backend (e.g. one using browser KaTeX metrics)."""
    global _CURRENT_BACKEND
    _CURRENT_BACKEND = backend


def get_measurement_backend() -> Optional["MeasurementBackend"]:
    return _CURRENT_BACKEND

def measure_object_bounds(obj: Any, **kwargs: Any) -> BoundingBox3D:
    """Phase 6: get 3D bounds using backend, fallback.
    Phase 5: surface info now includes world orientation for rotated tapes/objects.
    """
    if hasattr(obj, 'get_surface_info'):
        surf = obj.get_surface_info()
        if surf and surf.get('is_planar'):
            w = surf.get('width', 9.0)
            h = surf.get('height', 16.0)
            # Local bounds for layout/measurement; for oriented (rotated) tapes use world_transform
            # separately (as done in scene placement and camera transforms)
            return BoundingBox3D(min=(-w/2, -h/2, 0), max=(w/2, h/2, 0.01))
    backend = get_measurement_backend()
    if backend and hasattr(backend, 'measure_bounding_box'):
        try:
            return backend.measure_bounding_box(obj, **kwargs)
        except:
            pass
    # fallback
    return BoundingBox3D(min=(0,0,0), max=(1,1,1))

# Legacy keys that used to live inside ``content`` before LayoutBox existed.
_LEGACY_LAYOUT_KEYS = frozenset({"_target_width", "_target_height", "width"})

SurfaceFactory = Callable[[Optional[str]], Mobject]


@dataclass
class NormalizedContent:
    """Pure element payload with layout keys stripped."""

    text: Optional[str] = None
    equation: Optional[str] = None


def normalize_content(elem: CanvasElement) -> NormalizedContent:
    """Extract author content from an element, ignoring legacy layout hints."""
    content = elem.content
    if content is None:
        return NormalizedContent()
    if isinstance(content, str):
        if elem.type == "MathTex":
            return NormalizedContent(text=content)
        if elem.type in ("ThreeDGraph", "Surface"):
            return NormalizedContent(equation=content)
        return NormalizedContent(text=content)
    if isinstance(content, list):
        if elem.type == "Text":
            return NormalizedContent(text=plain_text_for_content(content))
        return NormalizedContent(text=str(content))
    if isinstance(content, dict):
        if elem.type == "Text" and is_rich_content(content):
            return NormalizedContent(text=plain_text_for_content(content))
        text = content.get("text")
        equation = content.get("equation")
        if elem.type == "MathTex" and text is None and equation is not None:
            text = equation
        if elem.type in ("ThreeDGraph", "Surface") and equation is None and text is not None:
            equation = text
        return NormalizedContent(text=text, equation=equation)
    return NormalizedContent(text=str(content))


def strip_layout_from_content(content: Any) -> Any:
    """Return content without legacy layout keys (for clean DSL output)."""
    if not isinstance(content, dict):
        return content
    cleaned = {k: v for k, v in content.items() if k not in _LEGACY_LAYOUT_KEYS}
    if "text" in cleaned and len(cleaned) == 1:
        return cleaned["text"]
    if "equation" in cleaned and len(cleaned) == 1:
        return cleaned["equation"]
    return cleaned if cleaned else None


def resolve_layout(elem: CanvasElement) -> Optional[LayoutBox]:
    """Return resolved layout, falling back to legacy content hints."""
    if elem.layout is not None:
        return elem.layout
    if not isinstance(elem.content, dict):
        return None
    c = elem.content
    tw = c.get("_target_width") or c.get("width")
    th = c.get("_target_height")
    if tw is None and th is None:
        return None
    return LayoutBox(
        width=float(tw) if tw is not None else 1.0,
        height=float(th) if th is not None else 1.0,
        wrap=bool(c.get("width")),
        align="center",
    )


def wrap_text_to_lines(text: str, max_width: float, font_size: float = DEFAULT_TEXT_FONT_SIZE) -> str:
    """Break text into newline-separated lines that fit within ``max_width``.

    Manim's ``Text(width=...)`` scales single-line glyphs; it does not wrap.
    """
    words = str(text).split()
    if not words:
        return str(text)

    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial_words = current + [word]
        trial = " ".join(trial_words)
        probe = Text(trial, font_size=font_size, color=WHITE)
        if probe.width > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current = trial_words
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def default_wrap_for_text(text: str, explicit: Optional[bool]) -> bool:
    """Default wrap policy when the author does not set ``wrap`` in style."""
    if explicit is not None:
        return explicit
    word_count = len(text.split())
    has_punct = any(ch in text for ch in ".!?,")
    return word_count > 7 or has_punct or len(text) > 60


def make_preview_surface(equation: Optional[str] = None) -> Mobject:
    """Low-resolution surface for fast layout measurement."""
    return make_surface_from_equation(equation, preview=True)


def make_render_surface(equation: Optional[str] = None) -> Mobject:
    """Render-quality surface parsed from the author's equation."""
    return make_surface_from_equation(equation, preview=False)


def _build_mathtex(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    norm = normalize_content(elem)
    tex = norm.text or r"\text{Math}"
    mob = MathTex(tex, color=WHITE).scale(DEFAULT_MATH_SCALE)
    if target_width and mob.get_width() > 0:
        mob.set_width(float(target_width))
    return mob


def _build_text(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    norm = normalize_content(elem)
    return build_plain_or_rich_mobject(
        elem.content if elem.content is not None else (norm.text or "Text"),
        wrap=wrap,
        target_width=float(target_width) if target_width else None,
        font_size=DEFAULT_TEXT_FONT_SIZE,
    )


def _build_solid3d(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    c = parse_solid_content(elem.content)
    if isinstance(c.get("parts"), list):
        body = make_solid_group(c["parts"], target_width=target_width)
    else:
        body = make_solid(c, target_width=target_width)
    return attach_labels_to_solid(body, elem.content)


def _build_surface_or_graph(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    norm = normalize_content(elem)
    eq = norm.equation
    surf = surface_factory(eq)
    label = None
    if eq:
        label = MathTex(eq, color="#aaccff").scale(0.6)
    if target_width and surf.get_width() > 0:
        surf.scale(float(target_width) / surf.get_width())
    if label:
        label.next_to(surf, UP, buff=0.3)
        grp = VGroup(surf, label)
        if target_width and grp.get_width() > 0:
            grp.set_width(float(target_width))
        return grp
    return surf


def _build_axes(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    from manim import ThreeDAxes
    ax = ThreeDAxes(
        x_range=[-4, 4, 1],
        y_range=[-4, 4, 1],
        z_range=[-2, 2, 0.5],
    )
    ax.scale(0.6)
    return ax


def _build_number_plane(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    from manim import NumberPlane
    plane = NumberPlane(
        x_range=[-6, 6, 1],
        y_range=[-6, 6, 1],
        background_line_style={"stroke_color": "#444444"},
    )
    plane.scale(0.55)
    return plane


def _build_grid_board(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    c = parse_grid_content(elem.content)
    mob = make_grid_board(
        rows=int(c.get("rows", 3)),
        cols=int(c.get("cols", 3)),
        cell_size=float(c.get("cell_size", 1.0)),
        stroke_color=str(c.get("stroke_color", "#888888")),
        stroke_width=float(c.get("stroke_width", 4.0)),
    )
    if target_width and mob.get_width() > 0:
        mob.set_width(float(target_width))
    return mob


def _build_grid_mark(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    c = parse_grid_content(elem.content)
    return make_grid_mark(
        str(c.get("symbol", "X")),
        float(c.get("cell_size", 1.0)),
    )


def _build_quadratic_plot(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    c = parse_plot_spec(elem.content)
    group, part = make_quadratic_plot(
        float(c.get("a", 1)),
        float(c.get("b", 0)),
        float(c.get("c", 0)),
        formula=c.get("formula"),
        x_range=tuple(c.get("x_range", (-3.0, 3.0))),
        plot_width=float(c.get("plot_width", 3.0)),
        plot_height=float(c.get("plot_height", 2.2)),
        x_start=float(c.get("x_start", 0)),
        show_readout=bool(c.get("show_readout", True)),
        stroke_color=str(c.get("color", "#5eb3ff")),
    )
    attach_plot_parts(group, [part])
    if target_width and group.get_width() > 0:
        group.set_width(float(target_width))
    return group


def _build_quadratic_plot_pair(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    c = parse_plot_spec(elem.content)
    left = c.get("left") or {}
    right = c.get("right") or {}
    gap = float(c.get("gap", 0.55))
    pw = float(c.get("plot_width", 2.65))
    ph = float(c.get("plot_height", 2.05))
    pair, parts = make_quadratic_plot_pair(left, right, gap=gap, plot_width=pw, plot_height=ph)
    attach_plot_parts(pair, parts)
    if target_width and pair.get_width() > 0:
        pair.set_width(float(target_width))
    return pair


def _build_unknown(elem: CanvasElement, wrap: bool, target_width: Optional[float], surface_factory: SurfaceFactory) -> Optional[Mobject]:
    from manim import Dot, Square
    return VGroup(
        Dot(radius=0.12, color="#ffcc00"),
        Square(side_length=0.6, color=WHITE, fill_opacity=0.15),
    )


def _build_raw_mobject(
    elem: CanvasElement,
    *,
    wrap: bool,
    target_width: Optional[float],
    surface_factory: SurfaceFactory,
) -> Optional[Mobject]:
    """Build an unscaled mobject for measurement or rendering.

    Phase 10: primary dispatch is via registered object kinds (builtins + custom).
    Legacy _CUSTOM_BUILDERS bridged for compat.
    """
    if elem.type in _OBJECT_KINDS and _OBJECT_KINDS[elem.type].get("build"):
        return _OBJECT_KINDS[elem.type]["build"](elem, wrap, target_width, surface_factory)
    if elem.type in _CUSTOM_BUILDERS:
        return _CUSTOM_BUILDERS[elem.type](elem, wrap, target_width, surface_factory)

    # Fallback for any unregistered (should be rare after auto-reg)
    return _build_unknown(elem, wrap, target_width, surface_factory)


def measure_element(
    elem: CanvasElement,
    *,
    usable_width: float,
    style_width: Optional[float] = None,
    style_height: Optional[float] = None,
    wrap: Optional[bool] = None,
    surface_factory: SurfaceFactory = make_preview_surface,
) -> tuple[float, float, bool]:
    """Main sizing entry point.

    If a MeasurementBackend has been injected via set_measurement_backend(),
    callers higher up (LayoutEngine) can choose to use the protocol for parity
    with manim-web / KaTeX. The current implementation remains the authoritative
    one for video rendering.
    """
    """Compute border-box (width, height, wrap) for layout.

    Returns:
        (target_width, target_height, resolved_wrap)
    """
    # Phase 10: delegate to registered kind measure if provided
    k = _OBJECT_KINDS.get(elem.type)
    if k and k.get("measure"):
        try:
            res = k["measure"](elem, usable_width=usable_width, style_width=style_width, style_height=style_height, wrap=wrap)
            if res:
                return res
        except Exception:
            pass

    if elem.type == "GridBoard":
        c = parse_grid_content(elem.content)
        rows, cols = int(c.get("rows", 3)), int(c.get("cols", 3))
        cell = float(c.get("cell_size", 1.0))
        tw, th = grid_dimensions(rows, cols, cell)
        if style_width is not None:
            tw = float(style_width)
            th = float(style_height) if style_height is not None else th * (tw / (cols * cell))
        elif style_height is not None:
            th = float(style_height)
        return tw, th, False

    if elem.type == "GridMark":
        c = parse_grid_content(elem.content)
        cell = float(c.get("cell_size", 1.0))
        size = cell * 0.72
        return size, size, False

    if elem.type == "Solid3D":
        size = solid_footprint_size(elem.content)
        tw = float(style_width) if style_width is not None else size
        th = float(style_height) if style_height is not None else size + 0.35
        return tw, th, False

    if elem.type == "QuadraticPlot":
        c = parse_plot_spec(elem.content)
        pw = float(c.get("plot_width", 3.0))
        ph = float(c.get("plot_height", 2.2))
        tw = float(style_width) if style_width is not None else pw
        th = float(style_height) if style_height is not None else ph + 0.8
        return tw, th, False

    if elem.type == "QuadraticPlotPair":
        c = parse_plot_spec(elem.content)
        pw = float(c.get("plot_width", 2.65))
        ph = float(c.get("plot_height", 2.05))
        gap = float(c.get("gap", 0.55))
        tw, th = pair_dimensions(pw, ph, gap)
        if style_width is not None:
            tw = float(style_width)
            th = float(style_height) if style_height is not None else th * (tw / pair_dimensions(pw, ph, gap)[0])
        elif style_height is not None:
            th = float(style_height)
        return tw, th, False

    is_text = elem.type == "Text"
    norm = normalize_content(elem)

    mob = _build_raw_mobject(
        elem,
        wrap=False,
        target_width=None,
        surface_factory=surface_factory,
    )
    nat_w = mob.get_width() if mob else 1.0
    nat_h = mob.get_height() if mob else 1.0

    tw = float(style_width) if style_width is not None else nat_w
    th = float(style_height) if style_height is not None else nat_h

    resolved_wrap = False
    if is_text:
        plain = plain_text_for_content(elem.content) if elem.content is not None else (norm.text or "")
        resolved_wrap = default_wrap_for_text(plain, wrap)

    if tw > usable_width:
        tw = usable_width * 0.97
        if is_text and resolved_wrap:
            mob = _build_raw_mobject(
                elem,
                wrap=True,
                target_width=tw,
                surface_factory=surface_factory,
            )
            if mob:
                tw = mob.width
                th = float(style_height) if style_height is not None else mob.height
        elif is_text:
            sc = tw / nat_w if nat_w > 0 else 1.0
            th = float(style_height) if style_height is not None else (nat_h * sc)
        else:
            sc = tw / nat_w if nat_w > 0 else 1.0
            th = float(style_height) if style_height is not None else (nat_h * sc)
    elif is_text and resolved_wrap and (style_width is not None or tw <= usable_width):
        mob = _build_raw_mobject(
            elem,
            wrap=True,
            target_width=tw,
            surface_factory=surface_factory,
        )
        if mob:
            tw = mob.width
            th = float(style_height) if style_height is not None else mob.height
    elif not (is_text and resolved_wrap) and nat_w > 0 and abs(tw - nat_w) > 1e-6:
        scale = tw / nat_w
        th = float(style_height) if style_height is not None else (nat_h * scale)

    return tw, th, resolved_wrap


def build_mobject(
    elem: CanvasElement,
    *,
    surface_factory: SurfaceFactory | None = None,
) -> Mobject | None:
    """Build the final Manim mobject for scene rendering."""
    layout = resolve_layout(elem)
    factory = surface_factory or make_render_surface

    if layout is not None:
        return _build_raw_mobject(
            elem,
            wrap=layout.wrap,
            target_width=layout.width,
            surface_factory=factory,
        )

    # Legacy path: hints still inside content dict
    tw = None
    wrap = False
    if isinstance(elem.content, dict):
        tw = elem.content.get("_target_width") or elem.content.get("width")
        wrap = bool(elem.content.get("width"))
    return _build_raw_mobject(
        elem,
        wrap=wrap,
        target_width=float(tw) if tw else None,
        surface_factory=factory,
    )


# -------------------------------------------------------------------
# Phase 10: Auto-register built-in object kinds at import time.
# This makes registry dispatch the canonical path for core types too.
# New kinds and custom viz register the same way (no if/elif patches).
# -------------------------------------------------------------------

def _auto_register_builtins():
    register_object_kind("MathTex", build=_build_mathtex)
    register_object_kind("Text", build=_build_text)
    register_object_kind("Solid3D", build=_build_solid3d)
    # "ThreeDGraph" and "Surface" share the surface builder
    register_object_kind("ThreeDGraph", build=_build_surface_or_graph)
    register_object_kind("Surface", build=_build_surface_or_graph)
    register_object_kind("Axes", build=_build_axes)
    register_object_kind("NumberPlane", build=_build_number_plane)
    register_object_kind("GridBoard", build=_build_grid_board)
    register_object_kind("GridMark", build=_build_grid_mark)
    register_object_kind("QuadraticPlot", build=_build_quadratic_plot)
    register_object_kind("QuadraticPlotPair", build=_build_quadratic_plot_pair)
    # Unknown falls back inside _build_raw_mobject but is also registered for completeness
    register_object_kind("Unknown", build=_build_unknown)


_auto_register_builtins()