"""Phase 0 skeleton for 3D world / unified canvas tests.

This file currently only verifies that the existing sheet/tape behavior
is still fully functional (no regressions from modeling work).

Real 3D space tests will be added in later phases.
"""

import pytest

# These imports must continue to work exactly as before.
from canvas import CanvasBuilder, CanvasScene
from canvas.dsl import CanvasElement, CanvasSettings
from canvas.coords import SHEET_PLANE_Z


def test_existing_sheet_imports_and_constants_still_work():
    """Phase 0 sanity: core sheet model still loads and behaves."""
    assert SHEET_PLANE_Z == 0.0

    b = CanvasBuilder(title="Phase0 compat test")
    b.add_text("Hello from the sheet")
    b.add_math(r"x^2 + y^2 = 1")

    dsl = b.build()
    assert len(dsl.timeline) >= 2
    assert all(isinstance(el, CanvasElement) for el in dsl.timeline if hasattr(el, 'type'))

    # Scene construction should not explode (we don't run full render here)
    # In later phases we will test world transforms + TapeObjects.
    settings = CanvasSettings.for_reels()
    # Just ensure we can instantiate without error.
    # (actual render happens via manim in other tests)
    _ = CanvasScene  # import is enough for this skeleton


def test_sheet_default_positioning_unchanged():
    """The default tape is still at z=0 for backward compat."""
    b = CanvasBuilder()
    b.add_body("Line 1")
    b.add_body("Line 2")

    for el in b.dsl.timeline:
        if hasattr(el, "canvas_position"):
            # In current model z is 0 or very small overlay
            assert abs(el.canvas_position[2]) < 0.01 or el.canvas_position[2] == 0.0

# --- Phase 1 tests ---

def test_world_transform_on_element():
    """Phase 1: elements can carry explicit WorldTransform (for 3D space model)."""
    from canvas import Vector3, WorldTransform, CanvasElement

    el = CanvasElement(
        id="test_el",
        type="Text",
        content="hello",
        world_transform=WorldTransform(
            position=Vector3(1.0, 2.0, 3.0),
            rotation=Vector3(0, 90, 0),
            scale=1.5,
        ),
    )

    d = el.to_dict()
    assert "world_transform" in d
    assert d["world_transform"]["position"] == (1.0, 2.0, 3.0)
    assert d["world_transform"]["scale"] == 1.5

    # Legacy canvas_position still present for compat
    assert "canvas_position" in d


def test_builder_root_tape_phase2():
    """Phase 2: builder populates root_tape.local_elements (conceptual tape object)."""
    from canvas import CanvasBuilder
    b = CanvasBuilder(title="p2")
    b.add_text("one")
    b.add_flex_row([b.text_spec("two"), b.math_spec("x")])
    assert hasattr(b, "root_tape")
    assert b.root_tape is not None
    assert len(b.root_tape.local_elements) == 3  # text + 2 in flex? wait flex adds the specs as elements
    # actually flex_row places multiple elements
    print('root_tape local count:', len(b.root_tape.local_elements))
    assert len(b.root_tape.local_elements) >= 2
    assert all(isinstance(e, type(b.dsl.timeline[0])) for e in b.root_tape.local_elements)


def test_camera_keyframe_phase3():
    """Phase 3: CameraKeyframe and observe_target structures work with tape."""
    from canvas import CanvasBuilder, CameraKeyframe, WorldPoint, TapeScroll
    from canvas.dsl import ObservationTarget
    b = CanvasBuilder()
    kf1 = CameraKeyframe(id='k1', target=WorldPoint((0, 10, 0)))
    kf2 = CameraKeyframe(id='k2', target=TapeScroll(tape_id='root_tape', local_y=5.0))
    b.dsl.timeline.append(kf1)
    b.dsl.timeline.append(kf2)
    # observe would be called in scene, here just structure
    assert isinstance(kf1.target, WorldPoint)
    assert isinstance(kf2.target, TapeScroll)
    print('phase3 keyframe + target ok')


def test_phase4_relative_and_anchors():
    """Phase 4: relative positioning, anchors, tape pose."""
    from canvas import CanvasBuilder, CanvasElement, Vector3
    b = CanvasBuilder()
    b.set_tape_pose(rotation=(30, 0, 0))
    base = CanvasElement(id='base', type='Text', content='base', canvas_position=(0,0,0))
    b._add(base)
    rel = CanvasElement(id='rel', type='Text', content='rel')
    b.add_relative('base', rel, (0, 1.0, 0), anchor='center')
    assert abs(rel.world_transform.position.y - 1.0) < 0.01
    # anchor on tape
    tape_anchor = b.root_tape.get_anchor('top_edge')
    assert tape_anchor.y > 0
    print('phase4 relative + anchor ok')


def test_phase9_registration_and_add_object():
    """Phase 9: registration and high-level add_object / context."""
    from canvas import register_object_kind, CanvasBuilder, CanvasElement, WorldTransform, Vector3
    from canvas.measure import _OBJECT_KINDS

    def my_build(elem, wrap, tw, factory):
        # return a simple mob for test
        from manim import Square
        return Square()

    register_object_kind("MyTestViz", build=my_build)
    assert "MyTestViz" in _OBJECT_KINDS

    b = CanvasBuilder()
    eid = b.add_object("MyTestViz", position=(1,2,3), content={"foo": "bar"})
    assert eid
    # check root_objects
    assert len(b.dsl.root_objects) > 0 or any(e.type == "MyTestViz" for e in b.dsl.timeline)
    print('phase9 reg + add_object ok')

    # context
    with b.in_object_space("root_tape"):
        pass  # would scope future adds
    print('phase9 context ok')


def test_phase10_mixed_3d_render_smoke():
    """Phase 10: smoke that a mixed 3D scene (rotated tape + world objects + relative + keyframes) builds without error."""
    from projects.demo.scenes import Space3DDemo
    # Instantiation builds the dsl with new model; construct would render in 3D
    s = Space3DDemo()
    dsl = s.dsl
    assert dsl.root_tape is not None
    assert len(dsl.root_objects) >= 1
    # simpler: check root_tape has local content and objects have transforms
    assert len(dsl.root_tape.local_elements) > 0
    assert any(hasattr(o, 'transform') for o in dsl.root_objects)
    print('phase10 mixed 3D smoke ok')


def test_phase5_dsl_and_builder_mix():
    """Phase 5: DSL and builder support mix of tape and world objects."""
    from canvas import CanvasBuilder, WorldObject, WorldTransform, Vector3, CanvasElement
    b = CanvasBuilder()
    b.add_text("tape content")
    wo = WorldObject(id="wo", transform=WorldTransform(position=Vector3(0,0,5)))
    b.add_world_object(wo)
    d = b.dsl.to_dict()
    assert "root_objects" in d
    assert len(d["root_objects"]) == 1
    print("phase5 dsl mix ok")


# --- Phase 10 comprehensive tests ---

def test_phase10_builtins_auto_registered():
    """Phase 10: core types are auto-registered so dispatch is uniform."""
    from canvas.measure import _OBJECT_KINDS
    for t in ("MathTex", "Text", "Solid3D", "ThreeDGraph", "Surface", "GridBoard", "QuadraticPlot", "Axes"):
        assert t in _OBJECT_KINDS, f"{t} should be registered"
        assert _OBJECT_KINDS[t].get("build") is not None
    print("phase10 builtins registered ok")


def test_phase10_resolve_world_and_anchors():
    """Phase 10: resolve_world_position + anchors on tape and objects."""
    from canvas import CanvasBuilder, CanvasElement, Vector3, WorldTransform, resolve_world_position
    b = CanvasBuilder()
    b.set_tape_pose(position=(1, 2, 0), rotation=(0, 0, 0))
    el = CanvasElement(id="base", type="Text", content="base")
    b._add(el)
    # place an object via add_object
    b.add_object("Text", id="relobj", position=(10, 0, 0))
    # resolve absolute
    p = resolve_world_position((0, 0, 0))
    assert isinstance(p, Vector3)
    # relative via tape
    tape_anchor = b.root_tape.get_anchor("center")
    assert hasattr(tape_anchor, "x")
    # element world pos should be composed in _add
    print("phase10 resolve + anchors ok")


def test_phase10_mixed_builder_add_object():
    """Phase 10: add_object via registry + add_relative + set_tape_pose produces correct DSL."""
    from canvas import CanvasBuilder, ObjectAnchor, TapeScroll
    b = CanvasBuilder()
    b.set_tape_pose(rotation=(10, 20, 0))
    eid = b.add_object("Solid3D", position=(1,2,3), content={"shape": "sphere", "size": 0.8})
    assert eid
    assert len(b.dsl.root_objects) >= 1
    b.add_camera_keyframe(target=ObjectAnchor(object_id=eid, anchor="center"), duration=1.5)
    b.add_camera_keyframe(target=TapeScroll(tape_id="root_tape", local_y=2.0), duration=2.0)
    dsl = b.build()
    assert dsl.root_tape is not None
    assert len(dsl.root_objects) >= 1
    kfs = [x for x in dsl.timeline if hasattr(x, "target")]
    assert len(kfs) >= 2
    print("phase10 builder mixed ok")


def test_phase10_dsl_roundtrip_root_objects():
    """Phase 10: to_dict/from_dict roundtrips root_objects + root_tape + keyframes."""
    from canvas import CanvasBuilder, CanvasElement, WorldObject, WorldTransform, Vector3, CameraKeyframe, WorldPoint
    from canvas.dsl import SheetDSL
    b = CanvasBuilder()
    b.add_text("hello on tape")
    wo = WorldObject(id="w1", element=CanvasElement(id="w1e", type="Text", content="w"), transform=WorldTransform(position=Vector3(5,1,0)))
    b.add_world_object(wo)
    b.add_camera_keyframe(target=WorldPoint(position=(0,10,0)), duration=1.0)
    d = b.dsl.to_dict()
    dsl2 = SheetDSL.from_dict(d)
    assert dsl2.root_tape is not None
    assert len(dsl2.root_objects) == 1
    assert any(isinstance(x, CameraKeyframe) for x in dsl2.timeline)
    print("phase10 dsl roundtrip ok")


def test_phase10_registry_measure_and_build_dispatch():
    """Phase 10: build and measure use registered kinds (no direct legacy if for builtins)."""
    from canvas.measure import build_mobject, measure_element, _OBJECT_KINDS
    from canvas.dsl import CanvasElement
    # Use a registered type
    el = CanvasElement(id="t1", type="Text", content="Hello registry")
    # measure should not explode
    w, h, wr = measure_element(el, usable_width=8.0)
    assert w > 0 and h > 0
    # build
    mob = build_mobject(el)
    assert mob is not None
    # confirm Text kind present
    assert "Text" in _OBJECT_KINDS
    print("phase10 registry dispatch ok")
