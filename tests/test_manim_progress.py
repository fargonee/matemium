"""Unit tests for Manim render progress estimation and reporting."""

from __future__ import annotations

from unittest.mock import MagicMock

from canvas.dsl import CameraMove

from matemium.ipc.duration import estimate_animation_count
from matemium.manim_progress import ManimProgressReporter, _segment_is_cached


class _FakeCamera:
    frame_rate = 30


class _FakeRenderer:
    def __init__(self, *, num_plays: int = 0, skip_animations: bool = False) -> None:
        self.num_plays = num_plays
        self.skip_animations = skip_animations
        self.camera = _FakeCamera()


class _FakeScene:
    duration = 2.0


def test_estimate_animation_count_counts_timeline_items():
    dsl = MagicMock()
    dsl.timeline = [
        CameraMove(id="a"),
        CameraMove(id="b"),
        CameraMove(id="c"),
    ]
    assert estimate_animation_count(dsl) == 5  # 2 base + 3 items


def test_progress_reporter_emits_partial_movie_fields():
    events: list[dict] = []

    def callback(**kwargs):
        events.append(kwargs)

    reporter = ManimProgressReporter(callback, animation_estimate=10, min_interval_s=0.0)
    reporter.bind_scene(_FakeScene())
    renderer = _FakeRenderer(num_plays=0)

    reporter.on_animation_begin(renderer)
    reporter.on_frame(renderer, 15)
    reporter.on_animation_done(renderer)

    assert len(events) >= 2
    frame_event = next(e for e in events if e.get("frame") == 15)
    assert frame_event["partial_index"] == 1
    assert frame_event["partial_total"] == 10
    assert frame_event["total_frames"] >= 15
    assert frame_event["section"] == "animate"
    assert 0.0 < frame_event["pct"] < 1.0
    begin_event = next(
        e for e in events if str(e.get("message", "")).startswith("Rendering segment")
    )
    assert begin_event["partial_cached"] is False


def test_progress_reporter_emits_cached_segment_fields():
    events: list[dict] = []

    def callback(**kwargs):
        events.append(kwargs)

    reporter = ManimProgressReporter(callback, animation_estimate=4, min_interval_s=0.0)
    reporter.bind_scene(_FakeScene())
    renderer = _FakeRenderer(num_plays=2)

    reporter.on_animation_begin(renderer, cached=True)
    reporter.on_animation_done(renderer, cached=True)

    assert events[0]["partial_index"] == 3
    assert events[0]["partial_cached"] is True
    assert "cached" in events[0]["message"].lower()
    assert events[-1]["partial_cached"] is True


def test_frame_events_keep_active_partial_index_during_encode():
    events: list[dict] = []

    def callback(**kwargs):
        events.append(kwargs)

    reporter = ManimProgressReporter(callback, animation_estimate=6, min_interval_s=0.0)
    reporter.bind_scene(_FakeScene())
    renderer = _FakeRenderer(num_plays=1)

    reporter.on_animation_begin(renderer)
    reporter.on_frame(renderer, 8)

    begin = next(
        e for e in events if str(e.get("message", "")).startswith("Rendering segment")
    )
    frame = next(e for e in events if e.get("frame") == 8)
    assert begin["partial_index"] == 2
    assert frame["partial_index"] == 2


def test_animation_done_reports_one_based_segment_index():
    events: list[dict] = []

    def callback(**kwargs):
        events.append(kwargs)

    reporter = ManimProgressReporter(callback, animation_estimate=3, min_interval_s=0.0)
    reporter.bind_scene(_FakeScene())
    renderer = _FakeRenderer(num_plays=0)

    reporter.on_animation_done(renderer)

    assert events[-1]["partial_index"] == 1
    assert "Finished segment 1" in events[-1]["message"]


def test_segment_is_cached_uses_partial_movie_files_index(tmp_path):
    renderer = _FakeRenderer(num_plays=1)
    writer = MagicMock()
    writer.partial_movie_files = [None, str(tmp_path / "missing.mp4")]

    assert _segment_is_cached(writer, renderer) is False

    path = tmp_path / "existing_segment.mp4"
    path.write_bytes(b"probe")
    writer.partial_movie_files[1] = str(path)
    assert _segment_is_cached(writer, renderer) is True