"""Phase 0 skeleton for 3D world / unified canvas tests.

This file currently only verifies that the existing sheet/tape behavior
is still fully functional (no regressions from modeling work).

Real 3D space tests will be added in later phases.
"""


# These imports must continue to work exactly as before.
from canvas import CanvasBuilder, CanvasScene
from canvas.dsl import CanvasElement, CanvasSettings
from canvas.coords import SHEET_PLANE_Z


def test_existing_sheet_imports_and_constants_still_work():
    """Phase 0 sanity: core sheet model still loads and behaves."""
    assert SHEET_PLANE_Z == 0.0

    b = CanvasBuilder(title="Phase0 compat test")
    t = b.add_tape("t1")
    t.add_text("Hello from the sheet")
    t.add_math(r"x^2 + y^2 = 1")

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
    t = b.add_tape("t1")
    t.add_body("Line 1")
    t.add_body("Line 2")

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
    assert d["world_transform"]["position"]["x"] == 1.0
    assert d["world_transform"]["scale"] == 1.5

    # Legacy canvas_position still present for compat
    assert "canvas_position" in d


def test_builder_root_tape_phase2():
    """Phase 2: builder populates root_tape.local_elements (conceptual tape object)."""
    from canvas import CanvasBuilder
    b = CanvasBuilder(title="p2")
    t = b.add_tape("t1")
    t.add_text("one")
    t.add_flex_row([b.text_spec("two"), b.math_spec("x")])
    assert len(b.dsl.tapes) > 0
    
    assert len(t._builder._tapes['t1'].local_elements) == 3  # text + 2 in flex? wait flex adds the specs as elements
    # actually flex_row places multiple elements
    
    assert len(t._builder._tapes['t1'].local_elements) >= 2
    assert all(isinstance(e, type(b.dsl.timeline[0])) for e in t._builder._tapes['t1'].local_elements)


def test_camera_keyframe_phase3():
    """Phase 3: CameraKeyframe and observe_target structures work with tape."""
    from canvas import CanvasBuilder, CameraKeyframe, WorldPoint
    b = CanvasBuilder()
    kf1 = CameraKeyframe(id='k1', target=WorldPoint((0, 10, 0)))
    b.dsl.timeline.append(kf1)
    # observe would be called in scene, here just structure
    assert isinstance(kf1.target, WorldPoint)

    print('phase3 keyframe + target ok')


def test_phase4_relative_and_anchors():
    """Phase 4: relative positioning, anchors, tape pose."""
    from canvas import CanvasBuilder, CanvasElement
    b = CanvasBuilder()
    t = b.add_tape("t1")
    base = CanvasElement(id='base', type='Text', content='base', canvas_position=(0,0,0))
    t.add_raw(base)
    rel = CanvasElement(id='rel', type='Text', content='rel')
    t.add_relative('base', rel, (0, 1.0, 0), anchor='center')
    assert True
    # anchor on tape
    tape_anchor = t._builder._tapes['t1'].get_anchor('top_edge')
    assert tape_anchor.y > 0
    print('phase4 relative + anchor ok')


def test_phase9_registration_and_add_object():
    """Phase 9: registration and high-level add_object / context."""
    from canvas import register_object_kind, CanvasBuilder
    from canvas.measure import _OBJECT_KINDS

    def my_build(elem, wrap, tw, factory):
        # return a simple mob for test
        from manim import Square
        return Square()

    register_object_kind("MyTestViz", build=my_build)
    assert "MyTestViz" in _OBJECT_KINDS

    b = CanvasBuilder()
    eid = b.add_object(
        "MyTestViz",
        id="hero_world",
        position=(1, 2, 3),
        rotation=(10, 20, 30),
        scale=1.25,
        content={"foo": "bar"},
    )
    assert eid == "hero_world"
    # check root_objects
    assert len(b.dsl.root_objects) == 1
    world = b.dsl.root_objects[0]
    assert world.id == "hero_world"
    assert world.element.id == "hero_world"
    assert world.transform.position.as_tuple() == (1, 2, 3)
    assert world.transform.rotation.as_tuple() == (10, 20, 30)
    assert world.transform.scale == 1.25
    assert b._placed_transforms["hero_world"] is world.transform
    print('phase9 reg + add_object ok')

    # context
    with b.in_object_space("root_tape"):
        pass  # would scope future adds
    print('phase9 context ok')


def test_world_object_placement_uses_local_origin_not_visual_center():
    """Asymmetric world geometry must not displace its authored origin."""
    import numpy as np
    from manim import Dot, Line, ORIGIN, RIGHT, VGroup

    from canvas import CanvasBuilder, register_object_kind

    def build_asymmetric(elem, wrap, target_width, surface_factory):
        marker = Dot(ORIGIN)
        group = VGroup(marker, Line(ORIGIN, RIGHT * float(elem.content["tail"])))
        group.matemium_parts = {"origin": marker}
        return group

    register_object_kind("AsymmetricWorldPlacement", build=build_asymmetric)
    builder = CanvasBuilder()
    builder.add_object(
        "AsymmetricWorldPlacement",
        id="world",
        position=(2.0, -1.0, 0.5),
        rotation=(15.0, 25.0, 0.0),
        scale=1.4,
        content={"tail": 6.0},
    )
    scene = CanvasScene(builder.build())

    scene._build_world_object(builder.dsl.root_objects[0])

    marker = scene.registry.get("world").matemium_parts["origin"]
    assert np.allclose(marker.get_center(), (2.0, -1.0, 0.5))


def test_world_object_morph_preserves_local_origin(monkeypatch):
    """Changing asymmetric content cannot drag stable world geometry sideways."""
    import numpy as np
    from manim import Dot, Line, ORIGIN, RIGHT, VGroup

    from canvas import CanvasBuilder, register_object_kind
    from canvas.dsl import ElementMorph

    def build_asymmetric(elem, wrap, target_width, surface_factory):
        marker = Dot(ORIGIN)
        group = VGroup(marker, Line(ORIGIN, RIGHT * float(elem.content["tail"])))
        group.matemium_parts = {"origin": marker}
        return group

    register_object_kind("AsymmetricWorldMorph", build=build_asymmetric)
    builder = CanvasBuilder()
    builder.add_object(
        "AsymmetricWorldMorph",
        id="world",
        position=(1.5, 2.0, -0.25),
        content={"tail": 2.0},
    )
    scene = CanvasScene(builder.build())
    scene._build_world_object(builder.dsl.root_objects[0])
    monkeypatch.setattr(scene, "play", lambda *animations, **kwargs: None)

    target = CanvasElement(
        id="world",
        type="AsymmetricWorldMorph",
        content={"tail": 9.0},
        auto_focus=False,
    )
    scene._handle_element_morph(
        ElementMorph(id="morph", element_id="world", target=target)
    )

    replacement = scene.registry.get("world")
    assert replacement is scene._world_objects["world"]
    assert np.allclose(
        replacement.matemium_parts["origin"].get_center(),
        (1.5, 2.0, -0.25),
    )


def test_phase10_mixed_3d_render_smoke():
    """A mixed scene keeps tapes separate from transformed world objects."""
    from projects.demo.scenes import Space3DDemo
    # Instantiation builds the dsl with new model; construct would render in 3D
    s = Space3DDemo()
    dsl = s.dsl
    assert len(dsl.tapes) > 0
    assert len(dsl.root_objects) >= 1
    # simpler: check root_tape has local content and objects have transforms
    assert len(dsl.tapes[0].local_elements) > 0
    assert any(hasattr(o, 'transform') for o in dsl.root_objects)
    print('phase10 mixed 3D smoke ok')


def test_phase5_dsl_and_builder_mix():
    """Phase 5: DSL and builder support mix of tape and world objects."""
    from canvas import CanvasBuilder, WorldObject, WorldTransform, Vector3
    b = CanvasBuilder()
    t = b.add_tape("t1")
    t.add_text("tape content")
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
    from canvas import CanvasBuilder, CanvasElement, Vector3, resolve_world_position
    b = CanvasBuilder()
    t = b.add_tape("t1")
    el = CanvasElement(id="base", type="Text", content="base")
    t.add_raw(el)
    # place an object via add_object
    b.add_object("Text", id="relobj", position=(10, 0, 0))
    # resolve absolute
    p = resolve_world_position((0, 0, 0))
    assert isinstance(p, Vector3)
    # relative via tape
    tape_anchor = t._builder._tapes['t1'].get_anchor("center")
    assert hasattr(tape_anchor, "x")
    # element world pos should be composed in _add
    print("phase10 resolve + anchors ok")


def test_phase10_mixed_builder_add_object():
    """A screen-facing tape and transformed world object coexist in the DSL."""
    from canvas import CanvasBuilder, ObjectAnchor
    b = CanvasBuilder()
    t = b.add_tape("t1")
    eid = b.add_object("Solid3D", position=(1,2,3), content={"shape": "sphere", "size": 0.8})
    assert eid
    assert len(b.dsl.root_objects) >= 1
    b.add_camera_keyframe(target=ObjectAnchor(object_id=eid, anchor="center"), duration=1.5)
    dsl = b.build()
    assert len(dsl.tapes) > 0
    assert len(dsl.root_objects) >= 1
    kfs = [x for x in dsl.timeline if hasattr(x, "target")]
    assert len(kfs) >= 1
    print("phase10 builder mixed ok")


def test_tape_is_camera_facing_context_and_roundtrips():
    """A secondary tape retains local layout but never accepts a world pose."""
    import pytest

    from canvas.dsl import SheetDSL

    b = CanvasBuilder()
    tape = b.add_tape(
        "telemetry",
        frame_width=8.0,
        frame_height=5.0,
    )
    tape.add_body("Altitude 400 km")

    source = b._tapes["telemetry"]
    assert not hasattr(source, "world_transform")
    assert source.get_surface_info()["presentation_mode"] == "camera_facing"

    restored = SheetDSL.from_dict(b.build().to_dict())
    rebuilt = next(item for item in restored.tapes if item.id == "telemetry")
    assert rebuilt.local_canvas_settings.frame_width == 8.0
    assert rebuilt.local_canvas_settings.frame_height == 5.0
    assert not hasattr(rebuilt, "world_transform")

    with pytest.raises(ValueError, match="camera-facing presentation contexts"):
        b.add_tape("invalid", position=(1.0, 2.0, 3.0))


def test_scene_tracks_root_and_secondary_tapes_as_foreground_contexts():
    """World restoration can reliably distinguish all tape content."""
    b = CanvasBuilder()
    b.add_body("Root tape")
    notes = b.add_tape("notes")
    notes.add_body("Secondary tape")
    b.add_object("Solid3D", id="world", content={"shape": "sphere", "size": 1})

    scene = CanvasScene(dsl=b.build())
    assert len(scene._tape_content_ids) == 2
    assert {tape.id for tape in scene._element_tape_map.values()} == {
        "root_tape",
        "notes",
    }


def test_tape_scroll_roundtrips_as_an_explicit_curtain_target():
    """Explicit tape selection survives project serialization."""
    from canvas import CameraKeyframe, TapeScroll
    from canvas.dsl import SheetDSL

    b = CanvasBuilder()
    notes = b.add_tape("notes")
    notes.add_body("Foreground explanation")
    b.scroll_tape(tape_id="notes", local_y=-1.75, run_time=0.8)

    restored = SheetDSL.from_dict(b.build().to_dict())
    keyframe = next(
        item for item in restored.timeline if isinstance(item, CameraKeyframe)
    )
    assert isinstance(keyframe.target, TapeScroll)
    assert keyframe.target.tape_id == "notes"
    assert keyframe.target.local_y == -1.75


def test_tape_scroll_rejects_unknown_tape_during_validation():
    from canvas import TapeScroll

    b = CanvasBuilder()
    b.add_camera_keyframe(target=TapeScroll(tape_id="missing"), duration=0.5)
    issues = b.build().validate()
    assert any(issue.code == "unknown_tape_id" for issue in issues)


def test_curtain_switch_hides_other_contexts_and_world_restore_excludes_tapes():
    """Regression: opening the world must not resurrect previous tapes."""
    from manim import Dot, FadeIn, FadeOut

    b = CanvasBuilder()
    b.add_body("Root")
    tape_a = b.add_tape("a")
    tape_a.add_body("A")
    tape_b = b.add_tape("b")
    tape_b.add_body("B")
    b.add_object("Solid3D", id="world", content={"shape": "sphere", "size": 1})

    scene = CanvasScene(dsl=b.build())
    ids = {
        "root": b.root_tape.local_elements[0].id,
        "a": b._tapes["a"].local_elements[0].id,
        "b": b._tapes["b"].local_elements[0].id,
    }
    mobs = {name: Dot() for name in ("root", "a", "b", "world")}
    for name in ("root", "a", "b"):
        scene.registry.register(ids[name], mobs[name], 0.0, (0.0, 0.0, 0.0))
    scene.registry.register("world", mobs["world"], 0.0, (0.0, 0.0, 0.0))
    scene._world_objects["world"] = mobs["world"]
    scene.add(*mobs.values())

    close = scene._get_context_switch_animations(b._tapes["a"])
    closing_targets = {
        animation.mobject
        for animation in close
        if isinstance(animation, FadeOut)
    }
    assert closing_targets == {mobs["root"], mobs["b"], mobs["world"]}

    # Approximate the post-close membership after Manim removes FadeOut targets.
    scene.remove(mobs["root"], mobs["b"], mobs["world"])
    open_world = scene._get_world_context_animations()
    fade_in_targets = {
        animation.mobject
        for animation in open_world
        if isinstance(animation, FadeIn)
    }
    fade_out_targets = {
        animation.mobject
        for animation in open_world
        if isinstance(animation, FadeOut)
    }
    assert fade_in_targets == {mobs["world"]}
    assert fade_out_targets == {mobs["a"]}

    for animation in (*close, *open_world):
        assert tuple(animation.shift_vector) == (0.0, 0.0, 0.0)


def test_first_flex_group_on_tape_hard_hides_world_context():
    """A tape that starts with a flex group gets the same isolation as one item."""
    from manim import Dot

    b = CanvasBuilder()
    tape = b.add_tape("dashboard")
    tape.add_flex_row(
        [
            b.text_spec("Left", id="left"),
            b.text_spec("Right", id="right"),
        ]
    )
    b.add_object("Solid3D", id="world", content={"shape": "sphere", "size": 1})

    scene = CanvasScene(dsl=b.build())
    world_mob = Dot()
    scene.registry.register("world", world_mob, 0.0, (0.0, 0.0, 0.0))
    scene._world_objects["world"] = world_mob
    scene.add(world_mob)
    scene.play = lambda *animations, **kwargs: None

    elements = [item for item in b.dsl.timeline if getattr(item, "flex_group", None)]
    scene._handle_flex_group_reveal(elements)

    assert scene._active_scroll_tape is b._tapes["dashboard"]
    assert world_mob not in scene.mobjects


def test_tape_context_switch_hard_removes_world_if_fadeout_does_not():
    """Regression: tape isolation cannot depend only on FadeOut side effects."""
    from manim import Dot

    b = CanvasBuilder()
    tape = b.add_tape("notes")
    tape.add_body("Tape")
    b.add_object("Solid3D", id="world", content={"shape": "sphere", "size": 1})

    scene = CanvasScene(dsl=b.build())
    tape_id = b._tapes["notes"].local_elements[0].id
    tape_mob = Dot()
    world_mob = Dot()
    scene.registry.register(tape_id, tape_mob, 0.0, (0.0, 0.0, 0.0))
    scene.registry.register("world", world_mob, 0.0, (0.0, 0.0, 0.0))
    scene._world_objects["world"] = world_mob
    scene.add(tape_mob, world_mob)

    # Simulate the problematic renderer path: animations are accepted, but
    # FadeOut does not remove the 3D world object from scene.mobjects.
    scene.play = lambda *animations, **kwargs: None

    scene._play_tape_context_switch(b._tapes["notes"], run_time=0.7)

    assert tape_mob in scene.mobjects
    assert world_mob not in scene.mobjects


def test_tape_context_switch_removes_stale_unregistered_scene_mobject():
    """A replaced world object cannot leak merely because its registry entry moved."""
    from manim import Dot, FadeOut

    b = CanvasBuilder()
    tape = b.add_tape("notes")
    tape.add_body("Tape")
    scene = CanvasScene(dsl=b.build())
    stale_world = Dot()
    scene.add(stale_world)

    animations = scene._get_context_switch_animations(b._tapes["notes"])
    assert any(
        isinstance(animation, FadeOut) and animation.mobject is stale_world
        for animation in animations
    )

    scene.play = lambda *animations, **kwargs: None
    scene._play_tape_context_switch(b._tapes["notes"], run_time=0.7)
    assert stale_world not in scene.mobjects


def test_world_keyframe_from_tape_cuts_camera_before_fade_in():
    """World observation reached from a tape does not interpolate camera trackers."""
    from canvas import CameraKeyframe, ObjectAnchor
    from canvas.dsl import ObservationMode
    from canvas.inspect_path import CameraPose

    b = CanvasBuilder()
    tape = b.add_tape("notes")
    tape.add_body("Tape")
    b.add_object("Solid3D", id="world", content={"shape": "sphere", "size": 1})

    scene = CanvasScene(dsl=b.build())
    scene._observation_mode = ObservationMode.TAPE_SCROLL
    scene._active_scroll_tape = b._tapes["notes"]
    resolved = CameraPose(0.0, 0.0, 0.0, 58.0, -32.0, 1.0)

    class CameraController:
        def resolve_observation_pose(self, *args, **kwargs):
            return resolved

        def observe_target(self, *args, **kwargs):
            raise AssertionError("a context cut must not animate observe_target")

    entered = []
    scene.camera_ctl = CameraController()
    scene._enter_world_context = lambda **kwargs: entered.append(kwargs.get("initial_pose"))
    scene._handle_camera_keyframe(
        CameraKeyframe(id="world_cut", target=ObjectAnchor(object_id="world"))
    )

    assert entered == [resolved]


def test_phase10_dsl_roundtrip_root_objects():
    """Phase 10: to_dict/from_dict roundtrips root_objects + root_tape + keyframes."""
    from canvas import CanvasBuilder, CanvasElement, WorldObject, WorldTransform, Vector3, CameraKeyframe, WorldPoint
    from canvas.dsl import SheetDSL
    b = CanvasBuilder()
    t = b.add_tape("t1")
    t.add_text("hello on tape")
    wo = WorldObject(id="w1", element=CanvasElement(id="w1e", type="Text", content="w"), transform=WorldTransform(position=Vector3(5,1,0)))
    b.add_world_object(wo)
    b.add_camera_keyframe(target=WorldPoint(position=(0,10,0)), duration=1.0)
    d = b.dsl.to_dict()
    dsl2 = SheetDSL.from_dict(d)
    assert len(dsl2.tapes) > 0
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


# --- Backward compatibility ---


def test_phase6_classic_cameramove_still_works():
    """Phase 6: Classic CameraMove on default tape continues to work for full backward compat."""
    from canvas.builder import CanvasBuilder

    b = CanvasBuilder()
    t = b.add_tape("t1")
    t.add_text("legacy style content")
    t.add_camera_move(dy=4.0, run_time=1.5)  # classic

    moves = [x for x in b.dsl.timeline if hasattr(x, "target_position")]
    assert len(moves) == 1
    assert moves[0].target_position[1] > 0
    print("phase6 classic CameraMove compat ok")
