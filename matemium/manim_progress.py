"""Hook Manim partial-movie rendering for granular progress events."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol

import numpy as np
from manim import config as manim_config
from manim.camera.three_d_camera import ThreeDCamera
from manim.renderer.cairo_renderer import CairoRenderer
from manim.scene.scene_file_writer import SceneFileWriter

if TYPE_CHECKING:
    from manim.scene.scene import Scene


class ProgressCallback(Protocol):
    def __call__(
        self,
        *,
        pct: float,
        message: str = "",
        section: str | None = None,
        frame: int | None = None,
        total_frames: int | None = None,
        partial_index: int | None = None,
        partial_total: int | None = None,
        partial_cached: bool | None = None,
    ) -> None: ...


def _expected_frame_count(duration: float) -> int:
    """Match Manim's ``np.arange(0, run_time, 1 / frame_rate)`` iteration count."""
    if duration <= 0:
        return 1
    step = 1 / float(manim_config["frame_rate"])
    return max(1, len(np.arange(0, duration, step)))


def _segment_is_cached(file_writer: SceneFileWriter, renderer: CairoRenderer) -> bool:
    """True when Manim skipped encoding because the partial movie already exists."""
    idx = renderer.num_plays
    files = file_writer.partial_movie_files
    if idx >= len(files):
        return False
    entry = files[idx]
    if not entry:
        return False
    return Path(entry).is_file()


@dataclass
class ManimProgressReporter:
    """Translate Manim renderer activity into coarse-grained IPC progress."""

    callback: ProgressCallback
    animation_estimate: int
    min_interval_s: float = 0.12

    def __post_init__(self) -> None:
        self._completed_segments = 0
        self._segment_frames = 0
        self._segment_total_frames = 0
        self._active_partial_index = 0
        self._active_scene: Scene | None = None
        self._last_emit = 0.0
        self._in_combine = False
        self._observed_total = 0

    def bind_scene(self, scene: Scene) -> None:
        self._active_scene = scene

    def unbind_scene(self) -> None:
        self._active_scene = None

    def on_animation_begin(self, renderer: CairoRenderer, *, cached: bool = False) -> None:
        self._segment_frames = 0
        self._segment_total_frames = 0
        scene = self._active_scene
        if scene is not None:
            self._segment_total_frames = _expected_frame_count(scene.duration)
        index = renderer.num_plays + 1
        self._active_partial_index = index
        if cached:
            self._segment_total_frames = 1
            self._segment_frames = 1
            self._emit(
                renderer,
                force=True,
                partial_index=index,
                partial_cached=True,
                message=f"Using cached segment {index}",
                section="animate",
            )
            return
        if renderer.skip_animations:
            return
        self._emit(
            renderer,
            force=True,
            partial_index=index,
            partial_cached=False,
            message=f"Rendering segment {index}",
            section="animate",
        )

    def on_frame(self, renderer: CairoRenderer, num_frames: int) -> None:
        if renderer.skip_animations or self._in_combine:
            return
        if self._segment_total_frames <= 0 and self._active_scene is not None:
            self._segment_total_frames = _expected_frame_count(self._active_scene.duration)
        self._segment_frames += num_frames
        self._emit(renderer, section="animate")

    def on_animation_done(
        self,
        renderer: CairoRenderer,
        *,
        cached: bool = False,
    ) -> None:
        if not renderer.skip_animations or cached:
            self._completed_segments += 1
        self._observed_total = max(self._observed_total, renderer.num_plays)
        index = renderer.num_plays + 1
        self._active_partial_index = index
        if cached:
            self._segment_total_frames = 1
            self._segment_frames = 1
        else:
            total = self._segment_total_frames
            self._segment_frames = total if total > 0 else 1
            if self._segment_total_frames <= 0:
                self._segment_total_frames = self._segment_frames
        self._emit(
            renderer,
            force=True,
            partial_index=index,
            partial_cached=cached if cached else False,
            message=(
                f"Cached segment {index}"
                if cached
                else f"Finished segment {index}"
            ),
            section="animate",
        )
        self._segment_frames = 0
        self._segment_total_frames = 0

    def on_render_finished(self, renderer: CairoRenderer) -> None:
        total = max(self._observed_total, renderer.num_plays, self._completed_segments)
        self.callback(
            pct=0.96,
            message=f"Rendered {total} segments",
            section="animate",
            partial_index=total,
            partial_total=total,
        )

    def on_combine_start(self) -> None:
        self._in_combine = True
        self.callback(
            pct=0.97,
            message="Combining partial movies",
            section="combine",
        )

    def on_combine_done(self) -> None:
        self._in_combine = False
        self.callback(
            pct=0.99,
            message="Finalizing video",
            section="combine",
        )

    def _emit(
        self,
        renderer: CairoRenderer,
        *,
        force: bool = False,
        partial_index: int | None = None,
        message: str | None = None,
        section: str | None = None,
        partial_cached: bool | None = None,
    ) -> None:
        now = time.monotonic()
        if not force and now - self._last_emit < self.min_interval_s:
            return
        self._last_emit = now

        estimate = max(1, self.animation_estimate)
        segment_fraction = (
            self._segment_frames / self._segment_total_frames
            if self._segment_total_frames > 0
            else 0.0
        )
        pct = min(0.96, (self._completed_segments + segment_fraction) / estimate)

        if partial_index is None:
            partial_index = self._active_partial_index or max(1, renderer.num_plays + 1)

        observed = max(
            self._observed_total,
            partial_index,
            self._completed_segments,
        )
        partial_total = max(estimate, observed)

        payload: dict[str, Any] = {
            "pct": round(pct, 4),
            "message": message or f"Rendering segment {partial_index}",
            "section": section or "animate",
            "partial_index": partial_index,
            "partial_total": partial_total,
        }
        if self._segment_total_frames > 0:
            payload["frame"] = self._segment_frames
            payload["total_frames"] = max(
                self._segment_total_frames,
                self._segment_frames,
            )
        if partial_cached is not None:
            payload["partial_cached"] = partial_cached

        self.callback(**payload)


class ProgressSceneFileWriter(SceneFileWriter):
    reporter: ManimProgressReporter | None = None

    def begin_animation(
        self,
        allow_write: bool = False,
        file_path: Any = None,
    ) -> None:
        if self.reporter is not None:
            cached = not allow_write and _segment_is_cached(self, self.renderer)
            if allow_write or cached:
                self.reporter.on_animation_begin(self.renderer, cached=cached)
        super().begin_animation(allow_write=allow_write, file_path=file_path)

    def end_animation(self, allow_write: bool = False) -> None:
        super().end_animation(allow_write=allow_write)
        if self.reporter is not None and not allow_write:
            if _segment_is_cached(self, self.renderer):
                self.reporter.on_animation_done(self.renderer, cached=True)

    def close_partial_movie_stream(self) -> None:
        super().close_partial_movie_stream()
        if self.reporter is not None:
            self.reporter.on_animation_done(self.renderer, cached=False)

    def combine_to_movie(self) -> None:
        if self.reporter is not None:
            self.reporter.on_combine_start()
        super().combine_to_movie()
        if self.reporter is not None:
            self.reporter.on_combine_done()


class ProgressCairoRenderer(CairoRenderer):
    def __init__(self, *, reporter: ManimProgressReporter, **kwargs: Any) -> None:
        self._reporter = reporter
        super().__init__(file_writer_class=ProgressSceneFileWriter, **kwargs)

    def init_scene(self, scene: Scene) -> None:
        super().init_scene(scene)
        self._reporter.bind_scene(scene)
        self.file_writer.reporter = self._reporter

    def play(self, scene: Scene, *args: Any, **kwargs: Any) -> None:
        self._reporter.bind_scene(scene)
        try:
            super().play(scene, *args, **kwargs)
        finally:
            self._reporter.bind_scene(scene)

    def add_frame(self, frame: Any, num_frames: int = 1) -> None:
        super().add_frame(frame, num_frames=num_frames)
        self._reporter.on_frame(self, num_frames)


def make_progress_renderer(reporter: ManimProgressReporter) -> ProgressCairoRenderer:
    # CanvasScene is a ThreeDScene — must match its camera or construct() fails.
    return ProgressCairoRenderer(reporter=reporter, camera_class=ThreeDCamera)