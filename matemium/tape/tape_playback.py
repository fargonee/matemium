from __future__ import annotations

from manim import (
    Animation,
    Circumscribe,
    Create,
    FadeIn,
    FadeOut,
    Flash,
    Indicate,
    LaggedStart,
    ReplacementTransform,
    SurroundingRectangle,
    TransformMatchingTex,
    Underline,
    VGroup,
    Write,
)

from .tape_row import TapeRow
from .tape_theme import TapeTheme


class TapePlayback:
    def __init__(self, scene, view, theme: TapeTheme) -> None:
        self.scene = scene
        self.view = view
        self.theme = theme

    def row_entry_animation(
        self,
        row: TapeRow,
        *,
        transform_from=None,
        run_time: float,
    ) -> Animation:
        if transform_from is not None:
            return TransformMatchingTex(transform_from, row.mobject, run_time=run_time)

        row_type = row.row_type
        if row_type == "problem":
            return FadeIn(row.mobject, scale=0.96, run_time=run_time)
        if row_type == "observation":
            return Write(row.mobject, run_time=run_time)
        if row_type == "math":
            return Write(row.mobject, run_time=run_time)
        if row_type == "note":
            return FadeIn(row.mobject, shift=row.mobject.get_left() * 0.1, run_time=run_time)
        if row_type == "concept":
            return FadeIn(row.mobject, scale=0.95, run_time=run_time)
        if row_type == "conclusion":
            return LaggedStart(
                FadeIn(row.mobject, scale=0.97, run_time=run_time * 0.6),
                Circumscribe(row.mobject, color=self.theme.accent_color, time_width=0.5, run_time=run_time),
                lag_ratio=0.15,
            )
        return FadeIn(row.mobject, run_time=run_time)

    def make_highlight(self, row: TapeRow, style: str = "soft"):
        if style == "underline":
            return Underline(row.mobject, color=self.theme.accent_color, buff=0.12)
        if style == "box":
            return SurroundingRectangle(
                row.mobject,
                color=self.theme.accent_color,
                buff=0.2,
                stroke_width=self.theme.stroke_widths.get("highlight", 3.0),
            )
        if style == "side_marker":
            marker = SurroundingRectangle(
                row.mobject,
                color=self.theme.accent_color,
                buff=0.25,
                corner_radius=0.08,
            )
            marker.stretch_to_fit_width(marker.width + 0.15)
            return marker
        if style == "dim_except":
            return SurroundingRectangle(
                row.mobject,
                color=self.theme.accent_color,
                buff=0.25,
                stroke_opacity=0.9,
            )
        return SurroundingRectangle(
            row.mobject,
            color=self.theme.accent_color,
            buff=0.18,
            stroke_width=self.theme.stroke_widths.get("highlight", 3.0),
        )

    def highlight_animation(self, highlight, style: str = "soft", run_time: float = 0.6) -> Animation:
        if style == "glow":
            return Indicate(highlight, color=self.theme.accent_color, scale_factor=1.02, run_time=run_time)
        if style == "underline":
            return Create(highlight, run_time=run_time)
        return Create(highlight, run_time=run_time)

    def flash_animation(self, row: TapeRow, run_time: float = 0.6) -> Animation:
        return Flash(row.mobject, color=self.theme.accent_color, run_time=run_time)

    def focus_card_animations(self, focus_group: VGroup, run_time: float = 0.8) -> tuple[Animation, Animation]:
        enter = FadeIn(focus_group, scale=0.94, run_time=run_time)
        exit_anim = FadeOut(focus_group, scale=0.98, run_time=run_time * 0.7)
        return enter, exit_anim

    def replay_row_animation(self, row: TapeRow, run_time: float) -> Animation:
        return ReplacementTransform(row.mobject.copy().set_opacity(0), row.mobject, run_time=run_time)

