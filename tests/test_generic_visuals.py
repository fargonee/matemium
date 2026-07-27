"""Cross-domain contracts for generic data visuals and state actions."""

from __future__ import annotations

import pytest

from canvas import (
    CanvasBuilder,
    CanvasElement,
    CanvasScene,
    ElementMorph,
    SheetDSL,
    StatePatch,
    StateTransition,
    build_mobject,
)
from canvas.generic_visuals import resolve_semantic_part
from canvas.measure import _OBJECT_KINDS


def issue_codes(dsl: SheetDSL) -> set[str]:
    return {issue.code for issue in dsl.validate()}


def test_generic_visual_kinds_are_registered_with_schemas_and_parts():
    for kind in ("DataPath", "DataPlot", "Diagram"):
        assert _OBJECT_KINDS[kind]["build"] is not None
        assert _OBJECT_KINDS[kind]["measure"] is not None
        assert _OBJECT_KINDS[kind]["validate"] is not None
        assert _OBJECT_KINDS[kind]["parts"] is not None


def test_data_path_builds_addressable_path():
    element = CanvasElement(
        id="trajectory",
        type="DataPath",
        content={"points": [[0, 0], [1, 1], [2, 0]], "smooth": True},
    )
    mobject = build_mobject(element)
    assert mobject is not None
    assert resolve_semantic_part(mobject, "path") is not None


def test_data_plot_builds_named_series_and_marker():
    element = CanvasElement(
        id="response",
        type="DataPlot",
        content={
            "series": [{"id": "speed", "points": [[0, 0], [1, 2], [2, 1]]}],
            "markers": [{"id": "cursor", "point": [1, 2]}],
        },
    )
    mobject = build_mobject(element)
    assert mobject is not None
    assert resolve_semantic_part(mobject, "axes") is not None
    assert resolve_semantic_part(mobject, "series:speed") is not None
    assert resolve_semantic_part(mobject, "marker:cursor") is not None


def test_diagram_builds_named_nodes_and_edges():
    element = CanvasElement(
        id="system",
        type="Diagram",
        content={
            "nodes": [
                {"id": "sensor", "label": "Sensor", "position": [-2, 0]},
                {"id": "controller", "label": "Controller", "position": [2, 0]},
            ],
            "edges": [{"id": "measurement", "from": "sensor", "to": "controller"}],
        },
    )
    mobject = build_mobject(element)
    assert mobject is not None
    assert resolve_semantic_part(mobject, "node:sensor") is not None
    assert resolve_semantic_part(mobject, "edge:measurement") is not None


def test_builder_creates_generic_visuals_and_synchronized_actions():
    builder = CanvasBuilder(title="Generic")
    diagram_id = builder.add_diagram(
        [{"id": "a", "position": [0, 0]}, {"id": "b", "position": [2, 0]}],
        [{"id": "ab", "from": "a", "to": "b"}],
        id="graph",
    )
    builder.add_state_transition(
        [
            {"target_id": f"{diagram_id}::node:a", "changes": {"color": "#ff0000"}},
            {"target_id": f"{diagram_id}::edge:ab", "changes": {"stroke_width": 7}},
        ]
    )
    builder.add_element_morph(
        diagram_id,
        CanvasElement(
            id="graph_next",
            type="Diagram",
            content={"nodes": [{"id": "done", "position": [0, 0]}], "edges": []},
        ),
    )
    dsl = builder.build()
    assert not dsl.validate()
    assert any(isinstance(item, StateTransition) for item in dsl.timeline)
    assert any(isinstance(item, ElementMorph) for item in dsl.timeline)


def test_generic_visual_content_validation_rejects_malformed_data():
    bad_path = SheetDSL(
        timeline=[CanvasElement(id="p", type="DataPath", content={"points": [[0, 0]]})]
    )
    bad_plot = SheetDSL(
        timeline=[
            CanvasElement(
                id="plot",
                type="DataPlot",
                content={"series": [{"id": "s", "points": [[0, 0], [float("inf"), 1]]}]},
            )
        ]
    )
    bad_diagram = SheetDSL(
        timeline=[
            CanvasElement(
                id="diagram",
                type="Diagram",
                content={
                    "nodes": [{"id": "a", "position": [0, 0]}],
                    "edges": [{"id": "bad", "from": "a", "to": "missing"}],
                },
            )
        ]
    )
    assert "invalid_element_content" in issue_codes(bad_path)
    assert "invalid_element_content" in issue_codes(bad_plot)
    assert "invalid_element_content" in issue_codes(bad_diagram)


def test_state_transition_validation_rejects_unknown_target_part_and_property():
    diagram = CanvasElement(
        id="graph",
        type="Diagram",
        content={"nodes": [{"id": "a", "position": [0, 0]}], "edges": []},
    )
    transition = StateTransition(
        id="state",
        patches=[
            StatePatch(target_id="graph::node:missing", changes={"color": "#fff"}),
            StatePatch(target_id="graph::node:a", changes={"domain_magic": True}),
        ],
    )
    codes = issue_codes(SheetDSL(timeline=[diagram, transition]))
    assert "unknown_semantic_part_id" in codes
    assert "unknown_state_property" in codes


def test_state_transition_validation_rejects_non_finite_geometry():
    element = CanvasElement(id="label", type="Text", content="hello")
    transition = StateTransition(
        id="state",
        patches=[StatePatch(target_id="label", changes={"position": [0, float("nan")]})],
    )
    assert "invalid_state_property" in issue_codes(SheetDSL(timeline=[element, transition]))


def test_element_morph_validates_target_kind_and_content():
    original = CanvasElement(id="label", type="Text", content="hello")
    unknown = ElementMorph(
        id="unknown",
        element_id="label",
        target=CanvasElement(id="target", type="UnregisteredDomainThing"),
    )
    malformed = ElementMorph(
        id="malformed",
        element_id="label",
        target=CanvasElement(id="target", type="DataPath", content={"points": [[0, 0]]}),
    )
    assert "unknown_morph_target_type" in issue_codes(SheetDSL(timeline=[original, unknown]))
    assert "invalid_morph_target_content" in issue_codes(SheetDSL(timeline=[original, malformed]))


def test_new_actions_round_trip_through_json_dict():
    element = CanvasElement(
        id="path",
        type="DataPath",
        content={"points": [[0, 0], [1, 1]]},
    )
    transition = StateTransition(
        id="state",
        patches=[StatePatch(target_id="path::path", changes={"stroke_width": 8})],
    )
    morph = ElementMorph(
        id="morph",
        element_id="path",
        target=CanvasElement(
            id="next",
            type="DataPath",
            content={"points": [[0, 0], [2, 0]]},
        ),
    )
    restored = SheetDSL.from_dict(SheetDSL(timeline=[element, transition, morph]).to_dict())
    assert isinstance(restored.timeline[1], StateTransition)
    assert restored.timeline[1].patches[0].target_id == "path::path"
    assert isinstance(restored.timeline[2], ElementMorph)
    assert restored.timeline[2].target.type == "DataPath"
    assert not restored.validate()


def test_scene_dispatch_resolves_and_animates_semantic_parts(monkeypatch):
    diagram = CanvasElement(
        id="graph",
        type="Diagram",
        content={"nodes": [{"id": "a", "position": [0, 0]}], "edges": []},
    )
    transition = StateTransition(
        id="state",
        patches=[StatePatch(target_id="graph::node:a", changes={"color": "#ff0000"})],
    )
    scene = CanvasScene(SheetDSL(timeline=[diagram, transition]))
    mobject = build_mobject(diagram)
    scene.registry.register("graph", mobject, 0.0, (0.0, 0.0, 0.0))
    played = []
    monkeypatch.setattr(scene, "play", lambda *animations, **kwargs: played.append((animations, kwargs)))
    scene._handle_state_transition(transition)
    assert len(played) == 1


def test_root_timeline_visual_uses_layout_position_not_default_world_origin(monkeypatch):
    builder = CanvasBuilder(title="Placement")
    builder.add_text("first")
    plot_id = builder.add_data_plot(
        [{"id": "series", "points": [[0, 0], [1, 1]]}],
        id="plot",
        style={"width": 6.0, "height": 3.0},
    )
    plot = next(item for item in builder.dsl.timeline if getattr(item, "id", None) == plot_id)
    assert plot.canvas_position[1] != 0.0
    scene = CanvasScene(builder.build())
    monkeypatch.setattr(scene, "play", lambda *animations, **kwargs: None)
    monkeypatch.setattr(scene, "add", lambda *mobjects: None)
    scene._handle_element_reveal(plot, play_animation=False)
    rendered = scene.registry.get(plot_id)
    assert rendered is not None
    assert rendered.get_center()[1] == pytest.approx(plot.canvas_position[1])


def test_scene_morph_replaces_registry_object_and_semantic_parts(monkeypatch):
    original = CanvasElement(
        id="path",
        type="DataPath",
        content={"points": [[0, 0], [1, 1]]},
    )
    target = CanvasElement(
        id="next",
        type="DataPath",
        content={"points": [[0, 0], [2, 0]], "color": "#ff0000"},
    )
    morph = ElementMorph(id="morph", element_id="path", target=target)
    scene = CanvasScene(SheetDSL(timeline=[original, morph]))
    source_mobject = build_mobject(original)
    scene.registry.register("path", source_mobject, 0.0, (0.0, 0.0, 0.0))
    scene._element_specs["path"] = original
    monkeypatch.setattr(scene, "play", lambda *animations, **kwargs: None)
    monkeypatch.setattr(scene, "remove", lambda *mobjects: None)
    monkeypatch.setattr(scene, "add", lambda *mobjects: None)
    scene._handle_element_morph(morph)
    replacement = scene.registry.get("path")
    assert replacement is not source_mobject
    assert resolve_semantic_part(replacement, "path") is not None
    assert scene._element_specs["path"] is target
