from __future__ import annotations

from manim import DOWN, LEFT, RIGHT, UP, Animation, DashedLine, Line, Rectangle, RoundedRectangle, Scene, VGroup

from .tape_theme import TapeTheme


class TapeView:
    def __init__(
        self,
        scene: Scene,
        *,
        width: float,
        viewport_height: float,
        left_safe_margin: float,
        right_safe_margin: float,
        top_safe_margin: float,
        bottom_safe_margin: float,
        show_grid: bool,
        show_frame: bool,
        theme: TapeTheme,
    ) -> None:
        self.scene = scene
        self.width = width
        self.viewport_height = viewport_height
        self.left_safe_margin = left_safe_margin
        self.right_safe_margin = right_safe_margin
        self.top_safe_margin = top_safe_margin
        self.bottom_safe_margin = bottom_safe_margin
        self.show_grid = show_grid
        self.show_frame = show_frame
        self.theme = theme

        self.background_layer = VGroup()
        self.frame_layer = VGroup()
        self.content_layer = VGroup()
        self.highlight_layer = VGroup()
        self.mask_layer = VGroup()
        self.overlay_layer = VGroup()
        self.scroll_container = VGroup(self.content_layer, self.highlight_layer)
        self.root = VGroup(
            self.background_layer,
            self.scroll_container,
            self.mask_layer,
            self.frame_layer,
            self.overlay_layer,
        )

        self.scroll_offset = 0.0
        self._build()

    def _build(self) -> None:
        self._build_background()
        self._build_masks()
        self._build_frame()

    def _build_background(self) -> None:
        background = RoundedRectangle(
            width=self.width,
            height=self.viewport_height,
            corner_radius=0.18,
            stroke_width=0,
            fill_color=self.theme.background_color,
            fill_opacity=1.0,
        )
        self.background_layer.add(background)

        if self.show_grid:
            grid = VGroup()
            for x in range(-3, 4):
                line = DashedLine(
                    start=UP * (self.viewport_height / 2) + RIGHT * x * (self.width / 6),
                    end=DOWN * (self.viewport_height / 2) + RIGHT * x * (self.width / 6),
                    dash_length=0.08,
                    dashed_ratio=0.5,
                    stroke_color=self.theme.grid_color,
                    stroke_width=self.theme.stroke_widths.get("grid", 1.0),
                )
                grid.add(line)
            for y in range(-6, 7):
                line = DashedLine(
                    start=LEFT * (self.width / 2) + UP * y * (self.viewport_height / 12),
                    end=RIGHT * (self.width / 2) + UP * y * (self.viewport_height / 12),
                    dash_length=0.08,
                    dashed_ratio=0.5,
                    stroke_color=self.theme.grid_color,
                    stroke_width=self.theme.stroke_widths.get("grid", 1.0),
                )
                grid.add(line)
            grid.set_opacity(0.25)
            self.background_layer.add(grid)

    def _build_masks(self) -> None:
        matte_color = self.scene.camera.background_color
        matte_size = max(self.scene.camera.frame_width, self.scene.camera.frame_height) * 2
        top_mask_height = max(self.top_safe_margin, 0.01)
        bottom_mask_height = max(self.bottom_safe_margin, 0.01)

        top_mask = Rectangle(
            width=matte_size,
            height=top_mask_height,
            stroke_width=0,
            fill_color=matte_color,
            fill_opacity=1.0,
        )
        top_mask.move_to(
            UP * (self.viewport_height / 2 - top_mask_height / 2)
        )

        bottom_mask = Rectangle(
            width=matte_size,
            height=bottom_mask_height,
            stroke_width=0,
            fill_color=matte_color,
            fill_opacity=1.0,
        )
        bottom_mask.move_to(
            DOWN * (self.viewport_height / 2 - bottom_mask_height / 2)
        )

        self.mask_layer.add(top_mask, bottom_mask)

    def _build_frame(self) -> None:
        if self.show_frame:
            frame = RoundedRectangle(
                width=self.width,
                height=self.viewport_height,
                corner_radius=0.18,
                stroke_color=self.theme.frame_color,
                stroke_width=self.theme.stroke_widths.get("frame", 2.0),
                fill_opacity=0,
            )
            corner = Line(
                start=UP * (self.viewport_height / 2 - 0.35) + LEFT * (self.width / 2 - 0.25),
                end=UP * (self.viewport_height / 2 - 0.35) + LEFT * (self.width / 2 - 0.9),
                stroke_color=self.theme.accent_color,
                stroke_width=4,
            )
            self.frame_layer.add(frame, corner)

    def attach_to_scene(self) -> None:
        self.scene.add(self.root)

    def add_row(self, row_group) -> None:
        self.content_layer.add(row_group)

    def set_scroll_offset(self, offset: float) -> None:
        self.scroll_offset = offset
        self.scroll_container.set_y(offset)

    def animate_scroll_to(self, offset: float, run_time: float) -> Animation:
        self.scroll_offset = offset
        return self.scroll_container.animate(run_time=run_time).set_y(offset)

    def clear_highlights(self) -> None:
        self.highlight_layer.submobjects.clear()

    def full_tape_group(self) -> VGroup:
        return VGroup(
            self.background_layer.copy(),
            self.content_layer.copy(),
            self.highlight_layer.copy(),
            self.frame_layer.copy(),
        )

    def viewport_snapshot(self) -> VGroup:
        return self.root.copy()

    def content_bounds(self) -> tuple[float, float]:
        if not self.content_layer.submobjects:
            top = self.viewport_height / 2 - self.top_safe_margin
            bottom = -self.viewport_height / 2 + self.bottom_safe_margin
            return top, bottom
        return self.content_layer.get_top()[1], self.content_layer.get_bottom()[1]

    def visible_bounds(self) -> tuple[float, float]:
        top = self.viewport_height / 2 - self.top_safe_margin
        bottom = -self.viewport_height / 2 + self.bottom_safe_margin
        return top, bottom
