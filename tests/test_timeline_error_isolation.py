"""Unit tests for per-item timeline error isolation in CanvasScene.

These tests exercise the TimelineExecutionError wrapper and the _item_meta
helper without requiring a full Manim render.  A stub handler that raises is
injected to simulate a mid-timeline failure.
"""

from __future__ import annotations

import pytest

from canvas.scene import TimelineExecutionError, _item_meta
from canvas.dsl import (
    CanvasElement,
    CameraMove,
    CameraKeyframe,
    TransformElement,
    PlotTrace,
    SolidLift,
    SolidRotate,
    CameraInspect,
    CameraFocus,
    WorldPoint,
)


# ---------------------------------------------------------------------------
# _item_meta helper
# ---------------------------------------------------------------------------

class TestItemMeta:
    """_item_meta extracts (kind, type, id) from any timeline payload."""

    def test_canvas_element(self):
        elem = CanvasElement(id="el1", type="MathTex", content=r"x^2")
        kind, typ, eid = _item_meta(elem)
        assert kind == "element"
        assert typ == "MathTex"
        assert eid == "el1"

    def test_camera_move(self):
        cm = CameraMove(id="cm1", target_position=(0, 5, 0))
        kind, typ, eid = _item_meta(cm)
        assert kind == "camera_move"
        assert typ == "CameraMove"
        assert eid == "cm1"

    def test_camera_keyframe(self):
        kf = CameraKeyframe(id="kf1", target=WorldPoint((0, 0, 0)))
        kind, typ, eid = _item_meta(kf)
        assert kind == "camera_keyframe"
        assert eid == "kf1"

    def test_transform_element(self):
        te = TransformElement(id="te1", source_id="el1")
        kind, typ, eid = _item_meta(te)
        assert kind == "transform"
        assert eid == "te1"

    def test_plot_trace(self):
        pt = PlotTrace(id="pt1", element_id="el1")
        kind, typ, eid = _item_meta(pt)
        assert kind == "plot_trace"
        assert eid == "pt1"

    def test_solid_lift(self):
        sl = SolidLift(id="sl1", element_id="el1")
        kind, typ, eid = _item_meta(sl)
        assert kind == "solid_lift"
        assert eid == "sl1"

    def test_solid_rotate(self):
        sr = SolidRotate(id="sr1", element_id="el1")
        kind, typ, eid = _item_meta(sr)
        assert kind == "solid_rotate"
        assert eid == "sr1"

    def test_camera_inspect(self):
        ci = CameraInspect(id="ci1", element_id="el1")
        kind, typ, eid = _item_meta(ci)
        assert kind == "camera_inspect"
        assert eid == "ci1"

    def test_camera_focus(self):
        cf = CameraFocus(id="cf1", element_id="el1")
        kind, typ, eid = _item_meta(cf)
        assert kind == "camera_focus"
        assert eid == "cf1"

    def test_flex_group_list(self):
        elems = [
            CanvasElement(id="a", type="Text", content="A", flex_group="g1"),
            CanvasElement(id="b", type="MathTex", content=r"x", flex_group="g1"),
        ]
        kind, typ, eid = _item_meta(elems)
        assert kind == "flex_group"
        # element_id for a flex group is the group id or first element id
        assert eid in ("g1", "a")

    def test_flex_group_empty_list(self):
        kind, typ, eid = _item_meta([])
        assert kind == "flex_group"
        assert typ == "unknown"
        assert eid is None

    def test_unknown_payload(self):
        """Arbitrary objects fall back to 'unknown' kind."""
        class Weird:
            pass
        kind, typ, eid = _item_meta(Weird())
        assert kind == "unknown"


# ---------------------------------------------------------------------------
# TimelineExecutionError
# ---------------------------------------------------------------------------

class TestTimelineExecutionError:
    """TimelineExecutionError carries structured fields and a clear message."""

    def _make_error(self, **overrides):
        defaults = dict(
            timeline_index=3,
            item_kind="element",
            item_type="MathTex",
            element_id="el_bad",
            cause="LaTeX compilation failed",
            original=ValueError("LaTeX compilation failed"),
        )
        defaults.update(overrides)
        return TimelineExecutionError(**defaults)

    def test_message_contains_index(self):
        err = self._make_error(timeline_index=7)
        assert "timeline:7" in str(err)

    def test_message_contains_kind(self):
        err = self._make_error(item_kind="solid_lift")
        assert "solid_lift" in str(err)

    def test_message_contains_type(self):
        err = self._make_error(item_type="Solid3D")
        assert "Solid3D" in str(err)

    def test_message_contains_element_id(self):
        err = self._make_error(element_id="cube_1")
        assert "cube_1" in str(err)

    def test_message_contains_cause(self):
        err = self._make_error(cause="division by zero")
        assert "division by zero" in str(err)

    def test_message_no_id_when_none(self):
        err = self._make_error(element_id=None)
        assert "id=" not in str(err)

    def test_to_dict_keys(self):
        err = self._make_error()
        d = err.to_dict()
        assert d["error"] == "TimelineExecutionError"
        assert d["timeline_index"] == 3
        assert d["item_kind"] == "element"
        assert d["item_type"] == "MathTex"
        assert d["element_id"] == "el_bad"
        assert "cause" in d

    def test_is_exception(self):
        err = self._make_error()
        assert isinstance(err, Exception)

    def test_original_chained(self):
        original = RuntimeError("boom")
        err = self._make_error(original=original)
        assert err.original is original

    def test_attributes(self):
        err = self._make_error(
            timeline_index=2,
            item_kind="camera_move",
            item_type="CameraMove",
            element_id="cm1",
            cause="bad rate_func",
        )
        assert err.timeline_index == 2
        assert err.item_kind == "camera_move"
        assert err.item_type == "CameraMove"
        assert err.element_id == "cm1"
        assert err.cause == "bad rate_func"


# ---------------------------------------------------------------------------
# Error isolation wrapper — simulated construct() loop
# ---------------------------------------------------------------------------

def _simulate_construct_loop(timeline_items, handler_fn):
    """Simulate the construct() dispatch loop with error isolation.

    Mirrors the pattern in CanvasScene.construct() so we can test the
    wrapping logic without instantiating a full Manim scene.
    """
    for tl_index, item in enumerate(timeline_items):
        try:
            handler_fn(item)
        except TimelineExecutionError:
            raise
        except Exception as exc:
            item_kind, item_type, element_id = _item_meta(item)
            raise TimelineExecutionError(
                timeline_index=tl_index,
                item_kind=item_kind,
                item_type=item_type,
                element_id=element_id,
                cause=str(exc),
                original=exc,
            ) from exc


class TestErrorIsolationWrapper:
    """The construct() loop wraps handler failures into TimelineExecutionError."""

    def test_clean_timeline_does_not_raise(self):
        items = [
            CanvasElement(id="e1", type="Text", content="hello"),
            CameraMove(id="cm1", target_position=(0, 5, 0)),
        ]
        results = []
        _simulate_construct_loop(items, lambda item: results.append(item))
        assert len(results) == 2

    def test_failing_handler_raises_timeline_error(self):
        items = [
            CanvasElement(id="e1", type="Text", content="ok"),
            CanvasElement(id="e2", type="MathTex", content=r"\bad"),
        ]

        def handler(item):
            if getattr(item, "id", None) == "e2":
                raise ValueError("LaTeX error")

        with pytest.raises(TimelineExecutionError) as exc_info:
            _simulate_construct_loop(items, handler)

        err = exc_info.value
        assert err.timeline_index == 1
        assert err.item_kind == "element"
        assert err.item_type == "MathTex"
        assert err.element_id == "e2"
        assert "LaTeX error" in err.cause

    def test_error_index_is_correct_for_third_item(self):
        items = [
            CanvasElement(id="e1", type="Text", content="a"),
            CanvasElement(id="e2", type="Text", content="b"),
            CameraMove(id="cm1", target_position=(0, 3, 0)),
        ]

        def handler(item):
            if isinstance(item, CameraMove):
                raise RuntimeError("camera exploded")

        with pytest.raises(TimelineExecutionError) as exc_info:
            _simulate_construct_loop(items, handler)

        err = exc_info.value
        assert err.timeline_index == 2
        assert err.item_kind == "camera_move"
        assert err.element_id == "cm1"

    def test_already_wrapped_error_is_not_double_wrapped(self):
        """A TimelineExecutionError raised inside a handler must propagate as-is."""
        inner = TimelineExecutionError(
            timeline_index=0,
            item_kind="element",
            item_type="Text",
            element_id="inner_id",
            cause="inner cause",
            original=ValueError("inner"),
        )
        items = [CanvasElement(id="outer", type="Text", content="x")]

        def handler(item):
            raise inner

        with pytest.raises(TimelineExecutionError) as exc_info:
            _simulate_construct_loop(items, handler)

        # Must be the exact same object — not re-wrapped
        assert exc_info.value is inner
        assert exc_info.value.element_id == "inner_id"

    def test_flex_group_failure_carries_group_metadata(self):
        """A flex-group list payload produces kind='flex_group' in the error."""
        group = [
            CanvasElement(id="fa", type="Text", content="A", flex_group="g1"),
            CanvasElement(id="fb", type="MathTex", content=r"x", flex_group="g1"),
        ]
        # Wrap in a tuple to simulate the (kind, payload) from _iter_timeline_batches
        # but here we pass the list directly as the "item" to the loop.
        items = [group]

        def handler(item):
            raise RuntimeError("flex render failed")

        with pytest.raises(TimelineExecutionError) as exc_info:
            _simulate_construct_loop(items, handler)

        err = exc_info.value
        assert err.item_kind == "flex_group"
        assert err.timeline_index == 0

    def test_to_dict_is_json_serialisable(self):
        import json
        items = [CanvasElement(id="bad", type="Text", content="x")]

        def handler(item):
            raise ValueError("oops")

        with pytest.raises(TimelineExecutionError) as exc_info:
            _simulate_construct_loop(items, handler)

        d = exc_info.value.to_dict()
        # Must be JSON-serialisable (for IPC / AI self-correction loop)
        serialised = json.dumps(d)
        assert "TimelineExecutionError" in serialised
        assert "oops" in serialised
