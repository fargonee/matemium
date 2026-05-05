from __future__ import annotations

from collections.abc import Iterable
from itertools import count

from manim import (
    DOWN,
    LEFT,
    ORIGIN,
    RIGHT,
    UP,
    BackgroundRectangle,
    FadeIn,
    FadeOut,
    MathTex,
    Paragraph,
    Scene,
    Text,
    VGroup,
)

from .tape_event import TapeEvent
from .tape_model import TapeModel
from .tape_playback import TapePlayback
from .tape_row import TapeRow
from .tape_theme import get_tape_theme
from .tape_view import TapeView


class SolutionTape:
    def __init__(
        self,
        scene: Scene,
        width: float = 7.0,
        viewport_height: float = 12.5,
        tape_height: float | None = None,
        difficulty: str = "easy",
        theme: str = "matemium_dark",
        viewport: str = "reel",
        row_gap: float = 0.55,
        padding: float = 0.45,
        active_y: float = -1.4,
        show_grid: bool = True,
        show_frame: bool = True,
        keep_last_n_rows_visible: int = 2,
        animate_by_default: bool = True,
        top_safe_margin: float = 0.6,
        bottom_safe_margin: float = 0.8,
        left_safe_margin: float = 0.35,
        right_safe_margin: float = 0.35,
    ) -> None:
        self.scene = scene
        self.model = TapeModel()
        self.theme = get_tape_theme(theme, difficulty)
        self.view = TapeView(
            scene,
            width=width,
            viewport_height=viewport_height,
            left_safe_margin=left_safe_margin,
            right_safe_margin=right_safe_margin,
            top_safe_margin=top_safe_margin,
            bottom_safe_margin=bottom_safe_margin,
            show_grid=show_grid,
            show_frame=show_frame,
            theme=self.theme,
        )
        self.playback = TapePlayback(scene, self.view, self.theme)

        self.width = width
        self.viewport_height = viewport_height
        self.tape_height = tape_height
        self.difficulty = difficulty
        self.viewport = viewport
        self.row_gap = row_gap
        self.padding = padding
        self.active_y = active_y
        self.keep_last_n_rows_visible = keep_last_n_rows_visible
        self.animate_by_default = animate_by_default
        self.top_safe_margin = top_safe_margin
        self.bottom_safe_margin = bottom_safe_margin
        self.left_safe_margin = left_safe_margin
        self.right_safe_margin = right_safe_margin

        self.rows = self.model.rows
        self.anchors = self.model.anchors
        self.states = self.model.states
        self.events = self.model.events

        self.current_row_index = -1
        self.current_y = self.viewport_height / 2 - self.top_safe_margin
        self.scroll_offset = 0.0
        self.current_view_center_y = 0.0
        self.highlighted_targets: dict[str, dict[str, object]] = {}
        self._suspend_event_recording = False
        self._id_counter = count()

        self.view.attach_to_scene()

    def _next_id(self, prefix: str) -> str:
        return f"{prefix}_{next(self._id_counter)}"

    def _resolve_animate(self, animate: bool | None) -> bool:
        return self.animate_by_default if animate is None else animate

    def _row_width(self) -> float:
        return self.width - self.left_safe_margin - self.right_safe_margin

    def _fit_row(self, mobject):
        max_width = self._row_width()
        if mobject.width > max_width:
            mobject.scale_to_fit_width(max_width)
        return mobject

    def _make_label(self, label: str):
        return Text(
            label,
            font_size=20,
            color=self.theme.muted_color,
        )

    def _make_text_block(self, text: str, font_size: int = 28):
        block = Paragraph(
            text,
            alignment="left",
            line_spacing=0.8,
            font_size=font_size,
            color=self.theme.text_color,
        )
        return self._fit_row(block)

    def _make_math_block(self, latex: str, font_size: int = 42):
        math = MathTex(latex, font_size=font_size, color=self.theme.math_color)
        return self._fit_row(math)

    def _stack(self, *parts, aligned_edge=LEFT, buff=0.16):
        group = VGroup(*[part for part in parts if part is not None])
        if len(group) > 1:
            group.arrange(DOWN, aligned_edge=aligned_edge, buff=buff)
        return self._fit_row(group)

    def _make_problem_group(self, text: str, subtitle: str | None, tag: str | None, difficulty_label: bool):
        parts = [self._make_text_block(text, font_size=30)]
        if subtitle:
            parts.append(self._make_text_block(subtitle, font_size=22).set_opacity(0.9))
        header_bits = []
        if tag:
            header_bits.append(Text(tag, font_size=20, color=self.theme.accent_color))
        if difficulty_label:
            header_bits.append(Text(self.difficulty.upper(), font_size=18, color=self.theme.accent_color))
        header = None
        if header_bits:
            header = VGroup(*header_bits).arrange(RIGHT, buff=0.3)
        if header is not None:
            parts.insert(0, header)
        content = self._stack(*parts)
        card = BackgroundRectangle(
            content,
            buff=0.22,
            fill_color=self.theme.grid_color,
            fill_opacity=0.18,
            stroke_opacity=0,
        )
        return VGroup(card, content)

    def _make_note_group(self, text: str, tone: str):
        content = self._make_text_block(text, font_size=24)
        stripe = BackgroundRectangle(
            content,
            buff=0.16,
            fill_color=self.theme.note_colors.get(tone, self.theme.accent_color),
            fill_opacity=0.12,
            stroke_opacity=0,
        )
        return VGroup(stripe, content)

    def _make_concept_group(self, title: str, explanation: str, formula: str | None):
        header = Text(title, font_size=24, color=self.theme.accent_color)
        body = self._make_text_block(explanation, font_size=22)
        formula_block = self._make_math_block(formula, font_size=34) if formula else None
        content = self._stack(header, body, formula_block)
        card = BackgroundRectangle(
            content,
            buff=0.22,
            fill_color=self.theme.grid_color,
            fill_opacity=0.14,
            stroke_opacity=0,
        )
        return VGroup(card, content)

    def _make_conclusion_group(self, text: str, math: str | None, emphasize: bool):
        title = Text(text, font_size=28, color=self.theme.text_color)
        formula = self._make_math_block(math, font_size=44) if math else None
        group = self._stack(title, formula)
        card = BackgroundRectangle(
            group,
            buff=0.24,
            fill_color=self.theme.accent_color,
            fill_opacity=0.08,
            stroke_opacity=0,
        )
        content = VGroup(card, group)
        if emphasize:
            frame = BackgroundRectangle(
                group,
                buff=0.3,
                fill_opacity=0,
                stroke_color=self.theme.accent_color,
                stroke_width=2.5,
            )
            content.add(frame)
        return content

    def _position_row_group(self, row_group):
        top_y = self.current_y
        x_position = (-self.width / 2) + self.left_safe_margin + (row_group.width / 2)
        row_group.move_to(RIGHT * x_position + UP * (top_y - row_group.height / 2))
        top = top_y
        center = row_group.get_center()[1]
        bottom = top - row_group.height
        self.current_y = bottom - self.row_gap
        return top, center, bottom

    def _apply_visibility(self, row: TapeRow, visible: bool) -> None:
        opacity = 1.0 if visible else 0.0
        self._set_row_opacity(row, opacity)
        row.visible = visible

    def _set_row_opacity(self, row: TapeRow, opacity: float) -> None:
        row.mobject.set_opacity(opacity)
        row.visible = opacity > 0
        row.metadata["opacity"] = opacity

    def _record_event(
        self,
        event_type: str,
        *,
        target: str | int | None,
        animation: str,
        run_time: float | None = None,
        metadata: dict[str, object] | None = None,
        start_state: str | None = None,
        end_state: str | None = None,
    ) -> TapeEvent | None:
        if self._suspend_event_recording:
            return None
        event = TapeEvent(
            id=self._next_id("event"),
            type=event_type,
            target=target,
            animation=animation,
            start_state=start_state,
            end_state=end_state,
            run_time=run_time,
            metadata=dict(metadata or {}),
        )
        self.model.add_event(event)
        return event

    def _highlight_specs(self) -> list[dict[str, object]]:
        specs: list[dict[str, object]] = []
        for row_id, highlight_data in self.highlighted_targets.items():
            specs.append(
                {
                    "row_id": row_id,
                    "style": str(highlight_data["style"]),
                    "label": highlight_data.get("label"),
                }
            )
        return specs

    def _target_scroll_for_row(self, row: TapeRow) -> float:
        desired_center = self.active_y
        return self._clamp_scroll_offset(desired_center - row.center_y)

    def _content_scroll_limits(self) -> tuple[float, float]:
        if not self.rows:
            return 0.0, 0.0

        top_visible, bottom_visible = self.view.visible_bounds()
        first_row = self.rows[0]
        last_row = self.rows[-1]

        top_limit = top_visible - first_row.top_y
        bottom_limit = bottom_visible - last_row.bottom_y
        return min(top_limit, bottom_limit), max(top_limit, bottom_limit)

    def _clamp_scroll_offset(self, offset: float) -> float:
        lower, upper = self._content_scroll_limits()
        return max(lower, min(upper, offset))

    def _scroll_to_offset(self, offset: float, run_time: float | None = None):
        duration = run_time or self.theme.animation_defaults["scroll_run_time"]
        clamped_offset = self._clamp_scroll_offset(offset)
        self.scene.play(self.view.animate_scroll_to(clamped_offset, duration))
        self.scroll_offset = clamped_offset
        self.current_view_center_y = -clamped_offset

    def _set_scroll_offset(self, offset: float) -> None:
        clamped_offset = self._clamp_scroll_offset(offset)
        self.view.set_scroll_offset(clamped_offset)
        self.scroll_offset = clamped_offset
        self.current_view_center_y = -clamped_offset

    def _scroll_row_into_focus(self, row: TapeRow, run_time: float | None = None):
        self._scroll_to_offset(self._target_scroll_for_row(row), run_time=run_time)

    def _create_highlight(
        self,
        row: TapeRow,
        *,
        style: str,
        label: str | None,
        animate: bool,
        run_time: float | None = None,
    ):
        highlight = self.playback.make_highlight(row, style=style)
        self.view.highlight_layer.add(highlight)
        if animate:
            self.scene.play(
                self.playback.highlight_animation(
                    highlight,
                    style=style,
                    run_time=run_time or 0.6,
                )
            )

        caption = None
        if label:
            caption = Text(label, font_size=22, color=self.theme.text_color)
            caption.next_to(highlight, DOWN, buff=0.18)
            self.view.overlay_layer.add(caption)
            if animate:
                self.scene.play(FadeIn(caption, shift=UP * 0.1))

        self.highlighted_targets[row.id] = {
            "style": style,
            "label": label,
            "highlight": highlight,
            "caption": caption,
        }
        return highlight

    def _clear_highlights(self, *, animate: bool, record_event: bool) -> None:
        fade_targets = list(self.view.highlight_layer.submobjects) + list(self.view.overlay_layer.submobjects)
        if animate and fade_targets:
            self.scene.play(*[FadeOut(target) for target in fade_targets])
        self.view.clear_highlights()
        self.view.overlay_layer.submobjects.clear()
        self.highlighted_targets.clear()
        if record_event:
            self._record_event(
                "clear_highlights",
                target=None,
                animation="fade_out",
                metadata={"cleared": True},
            )

    def _register_row(
        self,
        row_type: str,
        row_group,
        *,
        anchor: str | None,
        metadata: dict[str, object] | None = None,
    ) -> TapeRow:
        top_y, center_y, bottom_y = self._position_row_group(row_group)
        row = TapeRow(
            id=self._next_id(row_type),
            mobject=row_group,
            row_type=row_type,
            y_position=center_y,
            height=row_group.height,
            top_y=top_y,
            center_y=center_y,
            bottom_y=bottom_y,
            anchor_name=anchor,
            visible=False,
            metadata=dict(metadata or {}),
        )
        self.view.add_row(row_group)
        self.model.register_row(row)
        if anchor:
            self.model.add_anchor(anchor, row.id)
        self.current_row_index = len(self.rows) - 1
        return row

    def _record_add_event(self, row: TapeRow, event_type: str, run_time: float | None, metadata: dict[str, object] | None = None):
        event_metadata = dict(metadata or {})
        event_metadata.update(
            {
                "row_type": row.row_type,
                "scroll_offset_after": self.scroll_offset,
            }
        )
        self._record_event(
            event_type,
            target=row.id,
            animation="row_entry",
            run_time=run_time,
            metadata=event_metadata,
        )

    def _add_row(
        self,
        row_type: str,
        row_group,
        *,
        anchor: str | None = None,
        animate: bool | None = None,
        transform_from=None,
        metadata: dict[str, object] | None = None,
    ) -> TapeRow:
        row = self._register_row(row_type, row_group, anchor=anchor, metadata=metadata)
        should_animate = self._resolve_animate(animate)
        run_time = self.theme.animation_defaults["row_run_time"]

        if should_animate:
            if transform_from is None:
                self._apply_visibility(row, False)
            else:
                self._apply_visibility(row, True)
            self._scroll_row_into_focus(row)
            self.scene.play(
                self.playback.row_entry_animation(
                    row,
                    transform_from=transform_from,
                    run_time=run_time,
                )
            )
            self._apply_visibility(row, True)
        else:
            self._apply_visibility(row, True)
            if row.bottom_y + self.scroll_offset < -self.viewport_height / 2 + self.bottom_safe_margin:
                self.view.set_scroll_offset(self._clamp_scroll_offset(self._target_scroll_for_row(row)))
                self.scroll_offset = self.view.scroll_offset
                self.current_view_center_y = -self.scroll_offset

        self._record_add_event(row, f"add_{row_type}", run_time, metadata)
        return row

    def add_problem(
        self,
        text: str,
        subtitle: str | None = None,
        tag: str | None = None,
        difficulty_label: bool = True,
        anchor: str = "problem",
        animate: bool | None = None,
    ) -> TapeRow:
        return self._add_row(
            "problem",
            self._make_problem_group(text, subtitle, tag, difficulty_label),
            anchor=anchor,
            animate=animate,
            metadata={"text": text, "subtitle": subtitle, "tag": tag},
        )

    def add_observation(self, text: str, anchor: str | None = None, animate: bool | None = None) -> TapeRow:
        icon = Text("Notice", font_size=22, color=self.theme.accent_color)
        body = self._make_text_block(text, font_size=24)
        return self._add_row(
            "observation",
            self._stack(icon, body),
            anchor=anchor,
            animate=animate,
            metadata={"text": text},
        )

    def add_text(
        self,
        text: str,
        label: str | None = None,
        anchor: str | None = None,
        animate: bool | None = None,
    ) -> TapeRow:
        label_block = self._make_label(label) if label else None
        body = self._make_text_block(text, font_size=24)
        return self._add_row(
            "text",
            self._stack(label_block, body),
            anchor=anchor,
            animate=animate,
            metadata={"text": text, "label": label},
        )

    def add_math(
        self,
        latex: str,
        label: str | None = None,
        reason: str | None = None,
        anchor: str | None = None,
        animate: bool | None = None,
        transform_from=None,
    ) -> TapeRow:
        label_block = self._make_label(label) if label else None
        math = self._make_math_block(latex)
        reason_block = self._make_text_block(reason, font_size=20).set_opacity(0.9) if reason else None
        return self._add_row(
            "math",
            self._stack(label_block, math, reason_block),
            anchor=anchor,
            animate=animate,
            transform_from=transform_from,
            metadata={"latex": latex, "label": label, "reason": reason},
        )

    def add_step(
        self,
        title: str,
        content: str | None = None,
        math: str | None = None,
        anchor: str | None = None,
        animate: bool | None = None,
    ) -> TapeRow:
        title_block = Text(title, font_size=26, color=self.theme.accent_color)
        content_block = self._make_text_block(content, font_size=22) if content else None
        math_block = self._make_math_block(math, font_size=38) if math else None
        return self._add_row(
            "step",
            self._stack(title_block, content_block, math_block),
            anchor=anchor,
            animate=animate,
            metadata={"title": title, "content": content, "math": math},
        )

    def add_note(
        self,
        text: str,
        tone: str = "neutral",
        anchor: str | None = None,
        animate: bool | None = None,
    ) -> TapeRow:
        return self._add_row(
            "note",
            self._make_note_group(text, tone),
            anchor=anchor,
            animate=animate,
            metadata={"text": text, "tone": tone},
        )

    def add_concept(
        self,
        title: str,
        explanation: str,
        formula: str | None = None,
        anchor: str | None = None,
        animate: bool | None = None,
    ) -> TapeRow:
        return self._add_row(
            "concept",
            self._make_concept_group(title, explanation, formula),
            anchor=anchor,
            animate=animate,
            metadata={"title": title, "explanation": explanation, "formula": formula},
        )

    def add_check(
        self,
        text: str | None = None,
        math: str | None = None,
        anchor: str | None = None,
        animate: bool | None = None,
    ) -> TapeRow:
        title = Text("Check", font_size=24, color=self.theme.accent_color)
        text_block = self._make_text_block(text, font_size=22) if text else None
        math_block = self._make_math_block(math, font_size=36) if math else None
        return self._add_row(
            "check",
            self._stack(title, text_block, math_block),
            anchor=anchor,
            animate=animate,
            metadata={"text": text, "math": math},
        )

    def add_conclusion(
        self,
        text: str,
        math: str | None = None,
        emphasize: bool = True,
        anchor: str = "answer",
        animate: bool | None = None,
    ) -> TapeRow:
        return self._add_row(
            "conclusion",
            self._make_conclusion_group(text, math, emphasize),
            anchor=anchor,
            animate=animate,
            metadata={"text": text, "math": math, "emphasize": emphasize},
        )

    def add_mobject(
        self,
        mobject,
        row_type: str = "custom",
        anchor: str | None = None,
        animate: bool | None = None,
    ) -> TapeRow:
        return self._add_row(
            row_type,
            self._fit_row(mobject),
            anchor=anchor,
            animate=animate,
        )

    def add_anchor(self, name: str, target: str | TapeRow | None = "latest") -> None:
        row = self.model.resolve_row(target)
        self.model.add_anchor(name, row.id)
        row.anchor_name = name

    def get_anchor(self, name: str) -> TapeRow:
        return self.model.resolve_row(name)

    def scroll_to(self, target: str | TapeRow, align: str = "center", run_time: float | None = None) -> None:
        row = self.model.resolve_row(target)
        self._scroll_row_into_focus(row, run_time=run_time)
        self._record_event(
            "scroll_to",
            target=row.id,
            animation=f"scroll_{align}",
            run_time=run_time,
            metadata={"offset": self.scroll_offset, "align": align},
        )

    def scroll_by(self, amount: float, run_time: float | None = None) -> None:
        self._scroll_to_offset(self.scroll_offset + amount, run_time=run_time)
        self._record_event(
            "scroll_by",
            target=None,
            animation="scroll_delta",
            run_time=run_time,
            metadata={"amount": amount, "offset": self.scroll_offset},
        )

    def scroll_to_current(self, run_time: float | None = None) -> None:
        if self.current_row_index >= 0:
            self._scroll_row_into_focus(self.rows[self.current_row_index], run_time=run_time)

    def return_to_current(self, run_time: float | None = None) -> None:
        self.scroll_to_current(run_time=run_time)

    def highlight(self, target: str | TapeRow, label: str | None = None, style: str = "soft"):
        row = self.model.resolve_row(target)
        highlight = self._create_highlight(
            row,
            style=style,
            label=label,
            animate=True,
        )
        self._record_event(
            "highlight",
            target=row.id,
            animation=style,
            metadata={"style": style, "label": label},
        )
        return highlight

    def flash(self, target: str | TapeRow):
        row = self.model.resolve_row(target)
        self.scene.play(self.playback.flash_animation(row))
        self._record_event(
            "flash",
            target=row.id,
            animation="flash",
            metadata={},
        )

    def box(self, target: str | TapeRow):
        return self.highlight(target, style="box")

    def underline(self, target: str | TapeRow):
        return self.highlight(target, style="underline")

    def dim_except(self, target: str | TapeRow):
        return self.highlight(target, style="dim_except")

    def clear_highlights(self):
        self._clear_highlights(animate=True, record_event=True)

    def callback_to(
        self,
        target: str | TapeRow,
        message: str | None = None,
        return_after: bool = True,
        highlight_style: str = "glow",
        run_time: float | None = None,
    ) -> None:
        prior_offset = self.scroll_offset
        row = self.model.resolve_row(target)
        self._record_event(
            "callback_to",
            target=row.id,
            animation=highlight_style,
            run_time=run_time,
            metadata={
                "message": message,
                "return_after": return_after,
                "prior_offset": prior_offset,
            },
        )
        self.scroll_to(row, run_time=run_time)
        self.highlight(row, label=message, style=highlight_style)
        if return_after:
            self._scroll_to_offset(prior_offset, run_time=run_time)
            self._record_event(
                "return_to",
                target=row.id,
                animation="scroll_return",
                run_time=run_time,
                metadata={"offset": self.scroll_offset},
            )

    def focus_card(self, target: str | TapeRow, caption: str | None = None) -> None:
        row = self.model.resolve_row(target)
        dim = BackgroundRectangle(
            self.view.background_layer[0].copy().stretch_to_fit_width(self.width).stretch_to_fit_height(self.viewport_height),
            fill_color="#000000",
            fill_opacity=0.55,
            stroke_opacity=0,
        )
        card = row.mobject.copy().scale(1.15).move_to(ORIGIN)
        group = VGroup(dim, card)
        if caption:
            caption_obj = Text(caption, font_size=24, color=self.theme.text_color).next_to(card, DOWN, buff=0.3)
            group.add(caption_obj)
        self.view.overlay_layer.add(group)
        enter, exit_anim = self.playback.focus_card_animations(group)
        self.scene.play(enter)
        self.scene.wait(0.3)
        self.scene.play(exit_anim)
        self.view.overlay_layer.remove(group)
        self._record_event(
            "focus_card",
            target=row.id,
            animation="focus_card",
            metadata={"caption": caption},
        )

    def capture_state(self, name: str):
        visible_rows = [row.id for row in self.rows if row.visible]
        hidden_rows = [row.id for row in self.rows if not row.visible]
        highlighted = list(self.highlighted_targets.keys())
        return self.model.capture_state(
            name,
            visible_rows=visible_rows,
            hidden_rows=hidden_rows,
            highlighted_targets=highlighted,
            scroll_offset=self.scroll_offset,
            active_row_index=self.current_row_index,
            scale=1.0,
            viewport_center_y=self.current_view_center_y,
            row_opacities={row.id: float(row.metadata.get("opacity", 1.0 if row.visible else 0.0)) for row in self.rows},
            highlight_specs=self._highlight_specs(),
            event_index=len(self.events),
        )

    def _apply_state_snapshot(self, state) -> None:
        self._clear_highlights(animate=False, record_event=False)
        for row in self.rows:
            self._set_row_opacity(row, state.row_opacities.get(row.id, 0.0))
        self._set_scroll_offset(state.scroll_offset)
        self.current_row_index = state.active_row_index

        for highlight_spec in state.highlight_specs:
            row = self.model.resolve_row(str(highlight_spec["row_id"]))
            self._create_highlight(
                row,
                style=str(highlight_spec.get("style", "soft")),
                label=highlight_spec.get("label"),
                animate=False,
            )

    def restore_state(self, name: str) -> None:
        state = self.model.copy_state(name)
        self._apply_state_snapshot(state)

    def _reset_for_replay(self) -> None:
        self._clear_highlights(animate=False, record_event=False)
        self._set_scroll_offset(0.0)
        for row in self.rows:
            self._set_row_opacity(row, 0.0)
        self.current_row_index = -1

    def _replay_events(self, events: Iterable[TapeEvent]) -> None:
        self._suspend_event_recording = True
        try:
            for event in events:
                self._replay_event(event)
        finally:
            self._suspend_event_recording = False

    def _replay_event(self, event: TapeEvent) -> None:
        if event.type.startswith("add_") and isinstance(event.target, str):
            row = self.model.resolve_row(event.target)
            self.current_row_index = self.rows.index(row)
            self._scroll_to_offset(
                float(event.metadata.get("scroll_offset_after", self._target_scroll_for_row(row))),
                run_time=event.run_time,
            )
            self._set_row_opacity(row, 0.0)
            self.scene.play(
                self.playback.row_entry_animation(
                    row,
                    run_time=event.run_time or self.theme.animation_defaults["row_run_time"],
                )
            )
            self._set_row_opacity(row, 1.0)
            return

        if event.type == "scroll_to":
            self._scroll_to_offset(
                float(event.metadata.get("offset", self.scroll_offset)),
                run_time=event.run_time,
            )
            return

        if event.type == "scroll_by":
            self._scroll_to_offset(
                float(event.metadata.get("offset", self.scroll_offset)),
                run_time=event.run_time,
            )
            return

        if event.type == "highlight" and isinstance(event.target, str):
            row = self.model.resolve_row(event.target)
            self._create_highlight(
                row,
                style=str(event.metadata.get("style", event.animation)),
                label=event.metadata.get("label"),
                animate=True,
                run_time=event.run_time,
            )
            return

        if event.type == "flash" and isinstance(event.target, str):
            row = self.model.resolve_row(event.target)
            self.scene.play(self.playback.flash_animation(row, run_time=event.run_time or 0.6))
            return

        if event.type == "clear_highlights":
            self._clear_highlights(animate=False, record_event=False)
            return

        if event.type == "return_to":
            self._scroll_to_offset(
                float(event.metadata.get("offset", self.scroll_offset)),
                run_time=event.run_time,
            )
            return

        if event.type == "focus_card" and isinstance(event.target, str):
            row = self.model.resolve_row(event.target)
            self.focus_card(row, caption=event.metadata.get("caption"))

    def list_states(self) -> list[str]:
        return list(self.states.keys())

    def freeze_current_view(self):
        return self.view.viewport_snapshot()

    def freeze_full_tape(self):
        tape = self.view.full_tape_group()
        if self.rows:
            top = self.rows[0].top_y
            bottom = self.rows[-1].bottom_y
        else:
            top = self.viewport_height / 2 - self.top_safe_margin
            bottom = -self.viewport_height / 2 + self.bottom_safe_margin
        tape_height = max(
            self.viewport_height,
            top - bottom + self.top_safe_margin + self.bottom_safe_margin,
        )
        background = tape[0][0] if isinstance(tape[0], VGroup) and len(tape[0]) else None
        if background is not None:
            background.stretch_to_fit_height(tape_height)
        return tape

    def freeze_rows(self, targets: Iterable[str | TapeRow]):
        rows = [self.model.resolve_row(target) for target in targets]
        return VGroup(*[row.mobject.copy() for row in rows])

    def freeze_state(self, state_name: str):
        state = self.model.copy_state(state_name)
        frozen_rows = []
        for row in self.rows:
            row_copy = row.mobject.copy()
            row_copy.set_opacity(state.row_opacities.get(row.id, 0.0))
            frozen_rows.append(row_copy)
        return VGroup(*frozen_rows)

    def replay(self) -> None:
        self._reset_for_replay()
        self._replay_events(self.events)

    def replay_from(self, state_name: str) -> None:
        state = self.model.copy_state(state_name)
        self._apply_state_snapshot(state)
        self._replay_events(self.events[state.event_index :])

    def replay_range(self, start_event: int, end_event: int) -> None:
        self._reset_for_replay()
        self._replay_events(self.events[start_event:end_event])

    def reanimate_row(self, row_or_anchor: str | TapeRow) -> None:
        row = self.model.resolve_row(row_or_anchor)
        self.scene.play(self.playback.row_entry_animation(row, run_time=self.theme.animation_defaults["row_run_time"]))

    def reanimate_highlight(self, target: str | TapeRow) -> None:
        row = self.model.resolve_row(target)
        if row.id in self.highlighted_targets:
            primary = self.highlighted_targets[row.id]["highlight"]
            self.scene.play(self.playback.highlight_animation(primary))

    def reveal_full_tape(
        self,
        emphasize_anchors: list[str] | None = None,
        fade_helper_notes: bool = True,
        run_time: float | None = None,
    ) -> None:
        self.clear_highlights()
        full = self.freeze_full_tape().scale_to_fit_height(self.viewport_height - 0.6).move_to(ORIGIN)
        animations = []
        if fade_helper_notes:
            for row in self.rows:
                if row.row_type == "note":
                    animations.append(row.mobject.animate.set_opacity(0.45))
        animations.append(FadeIn(full, run_time=run_time or 1.0))
        self.scene.play(*animations)
        if emphasize_anchors:
            for anchor in emphasize_anchors:
                if anchor in self.anchors:
                    row = self.get_anchor(anchor)
                    self.scene.play(self.playback.flash_animation(row, run_time=0.45))
        self._record_event(
            "reveal_full_tape",
            target=None,
            animation="full_reveal",
            run_time=run_time,
            metadata={
                "emphasize_anchors": list(emphasize_anchors or []),
                "fade_helper_notes": fade_helper_notes,
            },
        )
