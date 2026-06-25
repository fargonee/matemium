"""Count Manim play()/wait() segments without encoding video."""

from __future__ import annotations

import logging

from manim import tempconfig

from canvas import CanvasScene, SheetDSL

logger = logging.getLogger(__name__)


def _fallback_animation_count(dsl: SheetDSL) -> int:
    """Heuristic when dry-run counting fails."""
    return max(2, len(dsl.timeline) + 2)


def count_scene_plays(dsl: SheetDSL) -> int:
    """Run ``CanvasScene.construct()`` once and count ``play`` / ``wait`` calls."""
    plays = 0

    class _PlayCountScene(CanvasScene):
        def play(self, *args, **kwargs) -> None:
            nonlocal plays
            plays += 1

        def wait(self, *args, **kwargs) -> None:
            nonlocal plays
            plays += 1

    settings = dsl.canvas_settings
    config = settings.get_manim_config_dict()
    config["write_to_movie"] = False
    config["save_last_frame"] = False

    with tempconfig(config):
        _PlayCountScene(dsl=dsl).render()

    return max(plays, 1)


def resolve_animation_count(dsl: SheetDSL) -> int:
    """Exact segment count when possible; heuristic fallback on failure."""
    try:
        return count_scene_plays(dsl)
    except Exception:
        logger.exception("play count dry-run failed; using timeline heuristic")
        return _fallback_animation_count(dsl)