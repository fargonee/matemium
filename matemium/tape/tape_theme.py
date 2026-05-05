from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from manim import BLUE_B, BLUE_E, GOLD, GRAY_B, GRAY_C, GREEN_B, ORANGE, PURPLE_B, RED_B, TEAL_B, WHITE, YELLOW


@dataclass(slots=True)
class TapeTheme:
    background_color: str
    grid_color: str
    frame_color: str
    text_color: str
    math_color: str
    accent_color: str
    muted_color: str
    note_colors: dict[str, str]
    stroke_widths: dict[str, float] = field(default_factory=dict)
    animation_defaults: dict[str, Any] = field(default_factory=dict)


_THEMES: dict[str, TapeTheme] = {
    "matemium_dark": TapeTheme(
        background_color="#0C1220",
        grid_color="#22314E",
        frame_color="#5E81F4",
        text_color=WHITE,
        math_color=WHITE,
        accent_color=TEAL_B,
        muted_color=GRAY_B,
        note_colors={
            "neutral": BLUE_B,
            "hint": TEAL_B,
            "warning": ORANGE,
            "insight": GOLD,
            "shortcut": PURPLE_B,
            "memory": GREEN_B,
        },
        stroke_widths={"frame": 2.0, "grid": 1.0, "highlight": 3.0},
        animation_defaults={"row_run_time": 0.8, "scroll_run_time": 0.9},
    ),
    "matemium_light": TapeTheme(
        background_color="#F8FAFF",
        grid_color="#D5DEEE",
        frame_color=BLUE_E,
        text_color="#0D1B2A",
        math_color="#0D1B2A",
        accent_color=BLUE_B,
        muted_color=GRAY_C,
        note_colors={
            "neutral": BLUE_B,
            "hint": TEAL_B,
            "warning": ORANGE,
            "insight": GOLD,
            "shortcut": PURPLE_B,
            "memory": GREEN_B,
        },
        stroke_widths={"frame": 2.0, "grid": 1.0, "highlight": 3.0},
        animation_defaults={"row_run_time": 0.8, "scroll_run_time": 0.9},
    ),
    "paper_light": TapeTheme(
        background_color="#FFFDF5",
        grid_color="#E4DEC8",
        frame_color="#84734F",
        text_color="#31291E",
        math_color="#31291E",
        accent_color="#6B8E23",
        muted_color="#A79A80",
        note_colors={
            "neutral": "#7586B8",
            "hint": "#4F8A8B",
            "warning": "#D97706",
            "insight": "#B8860B",
            "shortcut": "#7C3AED",
            "memory": "#2F855A",
        },
        stroke_widths={"frame": 2.0, "grid": 1.0, "highlight": 3.0},
        animation_defaults={"row_run_time": 0.8, "scroll_run_time": 0.9},
    ),
    "technical_dark": TapeTheme(
        background_color="#0A0D12",
        grid_color="#1F2937",
        frame_color="#94A3B8",
        text_color=WHITE,
        math_color=WHITE,
        accent_color=YELLOW,
        muted_color=GRAY_C,
        note_colors={
            "neutral": BLUE_B,
            "hint": TEAL_B,
            "warning": RED_B,
            "insight": GOLD,
            "shortcut": PURPLE_B,
            "memory": GREEN_B,
        },
        stroke_widths={"frame": 2.0, "grid": 1.0, "highlight": 3.0},
        animation_defaults={"row_run_time": 0.8, "scroll_run_time": 0.9},
    ),
}

_DIFFICULTY_ACCENTS = {
    "easy": "#5EEAD4",
    "medium": "#F59E0B",
    "hard": "#F97316",
}


def get_tape_theme(theme_name: str, difficulty: str) -> TapeTheme:
    base_theme = _THEMES.get(theme_name, _THEMES["matemium_dark"])
    accent = _DIFFICULTY_ACCENTS.get(difficulty, base_theme.accent_color)
    return TapeTheme(
        background_color=base_theme.background_color,
        grid_color=base_theme.grid_color,
        frame_color=base_theme.frame_color,
        text_color=base_theme.text_color,
        math_color=base_theme.math_color,
        accent_color=accent,
        muted_color=base_theme.muted_color,
        note_colors=dict(base_theme.note_colors),
        stroke_widths=dict(base_theme.stroke_widths),
        animation_defaults=dict(base_theme.animation_defaults),
    )

