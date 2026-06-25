"""Inline text runs — letter, word, or phrase granularity with per-run styling.

Authors pass a list of runs to ``add_text`` instead of a plain string. Each run is
an atomic styled unit (one letter, one word, or a longer phrase). The layout
engine measures and wraps the composed mobject like any other text block.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union

from manim import DOWN, LEFT, RIGHT, BackgroundRectangle, Mobject, Text, VGroup, WHITE

DEFAULT_TEXT_FONT_SIZE = 36

RunInput = Union[str, Dict[str, Any]]
RichInput = Union[str, Sequence[RunInput], Dict[str, Any]]

DEFAULT_HIGHLIGHT_FILL = "#3d3520"
DEFAULT_HIGHLIGHT_OPACITY = 0.92

_RUN_STYLE_KEYS = frozenset({
    "color",
    "font_size",
    "highlight",
    "underline",
    "bold",
    "italic",
    "opacity",
})


@dataclass(frozen=True)
class TextRun:
    """One styled fragment — as small as a single letter or as large as a sentence."""

    text: str
    color: str = "#FFFFFF"
    font_size: float = DEFAULT_TEXT_FONT_SIZE
    highlight: Optional[Union[bool, str]] = None
    underline: bool = False
    bold: bool = False
    italic: bool = False
    opacity: float = 1.0


def is_rich_content(content: Any) -> bool:
    if isinstance(content, dict) and "runs" in content:
        return True
    return isinstance(content, list)


def parse_runs(data: Sequence[RunInput]) -> List[TextRun]:
    runs: List[TextRun] = []
    for item in data:
        if isinstance(item, str):
            if item:
                runs.append(TextRun(text=item))
            continue
        if not isinstance(item, dict):
            runs.append(TextRun(text=str(item)))
            continue
        text = str(item.get("text") or item.get("t") or "")
        if not text:
            continue
        kwargs: Dict[str, Any] = {}
        for key in _RUN_STYLE_KEYS:
            if key in item:
                val = item[key]
                if key == "color":
                    val = str(val)
                kwargs[key] = val
        runs.append(TextRun(text=text, **kwargs))
    return runs


def normalize_rich_input(content: RichInput) -> Optional[List[TextRun]]:
    if isinstance(content, str):
        return None
    if isinstance(content, dict):
        raw = content.get("runs")
        if not raw:
            return None
        return parse_runs(raw)
    if isinstance(content, (list, tuple)):
        return parse_runs(content)
    return None


def runs_plain_text(runs: Sequence[TextRun]) -> str:
    return "".join(r.text for r in runs)


def _run_mobject(run: TextRun) -> Mobject:
    kwargs: Dict[str, Any] = {
        "font_size": run.font_size,
        "color": run.color,
    }
    if run.bold:
        kwargs["weight"] = "BOLD"
    if run.italic:
        kwargs["slant"] = "ITALIC"
    if run.underline:
        kwargs["underline"] = True

    mob = Text(run.text, **kwargs)
    if run.opacity != 1.0:
        mob.set_opacity(run.opacity)

    if run.highlight:
        fill = DEFAULT_HIGHLIGHT_FILL if run.highlight is True else str(run.highlight)
        bg = BackgroundRectangle(
            mob,
            color=fill,
            fill_opacity=DEFAULT_HIGHLIGHT_OPACITY,
            buff=0.05,
            corner_radius=0.04,
        )
        bg.set_stroke(width=0)
        return VGroup(bg, mob)
    return mob


def _line_width(line: Sequence[Mobject]) -> float:
    if not line:
        return 0.0
    return VGroup(*line).arrange(RIGHT, buff=0.0, aligned_edge=DOWN).width


def _runs_to_line_mobjects(runs: Sequence[TextRun]) -> Mobject:
    parts = [_run_mobject(r) for r in runs]
    if not parts:
        return Text(" ", font_size=DEFAULT_TEXT_FONT_SIZE, color=WHITE)
    if len(parts) == 1:
        return parts[0]
    return VGroup(*parts).arrange(RIGHT, buff=0.0, aligned_edge=DOWN)


def _break_runs_to_lines(runs: Sequence[TextRun], max_width: float) -> List[List[TextRun]]:
    """Wrap at run boundaries; split a single run on spaces when it alone overflows."""
    if max_width <= 0:
        return [list(runs)]

    lines: List[List[TextRun]] = []
    current: List[TextRun] = []

    def flush() -> None:
        nonlocal current
        if current:
            lines.append(current)
            current = []

    for run in runs:
        trial = current + [run]
        if _line_width([_run_mobject(r) for r in trial]) <= max_width:
            current = trial
            continue

        if current:
            flush()

        solo = _run_mobject(run)
        if solo.width <= max_width or " " not in run.text:
            current = [run]
            continue

        words = run.text.split(" ")
        chunk: List[str] = []
        base_style = {
            "color": run.color,
            "font_size": run.font_size,
            "highlight": run.highlight,
            "underline": run.underline,
            "bold": run.bold,
            "italic": run.italic,
            "opacity": run.opacity,
        }
        for word in words:
            piece = (" " if chunk else "") + word
            trial_text = "".join(chunk) + piece
            trial_run = TextRun(text=trial_text, **base_style)
            if _run_mobject(trial_run).width <= max_width:
                chunk.append(piece)
            else:
                if chunk:
                    current = [TextRun(text="".join(chunk), **base_style)]
                    flush()
                chunk = [word]
        if chunk:
            current = [TextRun(text="".join(chunk), **base_style)]
            flush()

    flush()
    return lines or [list(runs)]


def build_rich_text_mobject(
    runs: Sequence[TextRun],
    *,
    max_width: Optional[float] = None,
    wrap: bool = False,
    default_font_size: float = DEFAULT_TEXT_FONT_SIZE,
) -> Mobject:
    """Compose runs into one mobject, optionally wrapped to ``max_width``."""
    if not runs:
        return Text(" ", font_size=default_font_size, color=WHITE)

    normalized = [
        TextRun(
            text=r.text,
            color=r.color,
            font_size=r.font_size if r.font_size != DEFAULT_TEXT_FONT_SIZE else default_font_size,
            highlight=r.highlight,
            underline=r.underline,
            bold=r.bold,
            italic=r.italic,
            opacity=r.opacity,
        )
        for r in runs
    ]

    if wrap and max_width and max_width > 0:
        line_runs = _break_runs_to_lines(normalized, max_width)
    else:
        line_runs = [list(normalized)]

    line_mobs = [_runs_to_line_mobjects(lr) for lr in line_runs if lr]
    if not line_mobs:
        return Text(" ", font_size=default_font_size, color=WHITE)
    if len(line_mobs) == 1:
        mob = line_mobs[0]
    else:
        mob = VGroup(*line_mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.12)

    if max_width and not wrap and mob.width > max_width and mob.width > 0:
        mob.set_width(float(max_width))
    return mob


def build_plain_or_rich_mobject(
    content: Any,
    *,
    wrap: bool,
    target_width: Optional[float],
    font_size: float = DEFAULT_TEXT_FONT_SIZE,
) -> Mobject:
    """Build Text from a plain string or rich run list/dict."""
    runs = normalize_rich_input(content)
    if runs is not None:
        return build_rich_text_mobject(
            runs,
            max_width=target_width,
            wrap=wrap,
            default_font_size=font_size,
        )

    if isinstance(content, dict):
        txt = str(content.get("text") or "")
    else:
        txt = str(content or "Text")

    if target_width and wrap:
        from .measure import wrap_text_to_lines

        wrapped = wrap_text_to_lines(txt, float(target_width), font_size=font_size)
        return Text(wrapped, font_size=font_size, color=WHITE)
    mob = Text(txt, font_size=font_size, color=WHITE)
    if target_width and mob.width > 0:
        mob.set_width(float(target_width))
    return mob


def plain_text_for_content(content: Any) -> str:
    """Plain string for wrap heuristics and search."""
    runs = normalize_rich_input(content)
    if runs is not None:
        return runs_plain_text(runs)
    if isinstance(content, dict):
        return str(content.get("text") or "")
    return str(content or "")