"""Unit tests for SheetDSL.validate().

All tests are pure-Python — no Manim render required.
"""

from __future__ import annotations

import pytest

from canvas.dsl import (
    CanvasElement,
    CameraFocus,
    CameraInspect,
    CameraMove,
    DSLValidationError,
    PlotTrace,
    SheetDSL,
    SolidLift,
    SolidRotate,
    TapeObject,
    TransformElement,
    ValidationIssue,
    ValidationSeverity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dsl(*timeline_items) -> SheetDSL:
    """Build a minimal SheetDSL with the given timeline items."""
    dsl = SheetDSL()
    dsl.timeline = list(timeline_items)
    return dsl


def _elem(id: str, type: str = "Text", **kwargs) -> CanvasElement:
    return CanvasElement(id=id, type=type, content="x", **kwargs)


def _codes(issues) -> list:
    return [i.code for i in issues]


def _errors(issues) -> list:
    return [i for i in issues if i.severity == ValidationSeverity.ERROR]


def _warnings(issues) -> list:
    return [i for i in issues if i.severity == ValidationSeverity.WARNING]


# ---------------------------------------------------------------------------
# 1. Known element type
# ---------------------------------------------------------------------------

class TestKnownElementType:
    def test_known_core_type_no_issue(self):
        dsl = _make_dsl(_elem("e1", "Text"), _elem("e2", "MathTex"))
        issues = dsl.validate()
        type_issues = [i for i in issues if i.code == "unknown_element_type"]
        assert not type_issues

    def test_known_registered_type_no_issue(self):
        """Types registered via register_object_kind() are also accepted."""
        from canvas.measure import register_object_kind
        register_object_kind("MyCustomViz", build=lambda *a, **k: None)
        dsl = _make_dsl(_elem("e1", "MyCustomViz"))
        issues = dsl.validate()
        type_issues = [i for i in issues if i.code == "unknown_element_type"]
        assert not type_issues

    def test_unknown_type_produces_warning(self):
        dsl = _make_dsl(_elem("e1", "CompletelyMadeUpType"))
        issues = dsl.validate()
        type_issues = [i for i in issues if i.code == "unknown_element_type"]
        assert len(type_issues) == 1
        assert type_issues[0].severity == ValidationSeverity.WARNING
        assert type_issues[0].element_id == "e1"
        assert type_issues[0].field == "type"

    def test_unknown_type_is_warning_not_error(self):
        """Unknown types are warnings (not errors) because custom builders may handle them."""
        dsl = _make_dsl(_elem("e1", "FutureType"))
        issues = dsl.validate()
        assert not _errors(issues)
        assert any(i.code == "unknown_element_type" for i in _warnings(issues))

    def test_all_core_primitives_accepted(self):
        core_types = [
            "MathTex", "Text", "ThreeDGraph", "Surface", "Solid3D",
            "Axes", "NumberPlane", "ParametricFunction", "VGroup",
            "Dot", "Arrow", "Image", "SVG",
            "GridBoard", "GridMark", "QuadraticPlot", "QuadraticPlotPair",
        ]
        for t in core_types:
            dsl = _make_dsl(_elem("e1", t))
            issues = dsl.validate()
            type_issues = [i for i in issues if i.code == "unknown_element_type"]
            assert not type_issues, f"Core type {t!r} should not produce unknown_element_type"


# ---------------------------------------------------------------------------
# 2. Duplicate element ids
# ---------------------------------------------------------------------------

class TestDuplicateElementIds:
    def test_unique_ids_no_issue(self):
        dsl = _make_dsl(_elem("e1"), _elem("e2"), _elem("e3"))
        issues = dsl.validate()
        assert not any(i.code == "duplicate_element_id" for i in issues)

    def test_duplicate_id_in_timeline(self):
        dsl = _make_dsl(_elem("e1"), _elem("e1"))
        issues = dsl.validate()
        dup = [i for i in issues if i.code == "duplicate_element_id"]
        assert len(dup) == 1
        assert dup[0].severity == ValidationSeverity.ERROR
        assert dup[0].element_id == "e1"

    def test_multiple_duplicates_reported(self):
        dsl = _make_dsl(_elem("a"), _elem("a"), _elem("b"), _elem("b"))
        issues = dsl.validate()
        dup = [i for i in issues if i.code == "duplicate_element_id"]
        assert len(dup) == 2

    def test_camera_move_id_not_duplicated_with_element(self):
        """CameraMove ids live in a different namespace — no false positive."""
        dsl = _make_dsl(
            _elem("e1"),
            CameraMove(id="cm1", target_position=(0, 5, 0)),
        )
        issues = dsl.validate()
        assert not any(i.code == "duplicate_element_id" for i in issues)


# ---------------------------------------------------------------------------
# 3. parent_object_id references existing tape/world object
# ---------------------------------------------------------------------------

class TestParentObjectId:
    def test_no_parent_no_issue(self):
        dsl = _make_dsl(_elem("e1"))
        issues = dsl.validate()
        assert not any(i.code == "unknown_parent_object_id" for i in issues)

    def test_valid_parent_tape_id(self):
        tape = TapeObject(id="tape1")
        dsl = _make_dsl(_elem("e1", parent_object_id="tape1"))
        dsl.tapes = [tape]
        issues = dsl.validate()
        assert not any(i.code == "unknown_parent_object_id" for i in issues)

    def test_invalid_parent_id_produces_error(self):
        dsl = _make_dsl(_elem("e1", parent_object_id="nonexistent_tape"))
        issues = dsl.validate()
        parent_issues = [i for i in issues if i.code == "unknown_parent_object_id"]
        assert len(parent_issues) == 1
        assert parent_issues[0].severity == ValidationSeverity.ERROR
        assert parent_issues[0].element_id == "e1"
        assert parent_issues[0].field == "parent_object_id"


# ---------------------------------------------------------------------------
# 4. Target element id references
# ---------------------------------------------------------------------------

class TestTargetElementIds:
    def test_transform_valid_source_id(self):
        dsl = _make_dsl(
            _elem("e1"),
            TransformElement(id="t1", source_id="e1"),
        )
        issues = dsl.validate()
        assert not any(i.code == "unknown_target_element_id" for i in issues)

    def test_transform_invalid_source_id(self):
        dsl = _make_dsl(
            TransformElement(id="t1", source_id="ghost"),
        )
        issues = dsl.validate()
        target_issues = [i for i in issues if i.code == "unknown_target_element_id"]
        assert len(target_issues) == 1
        assert target_issues[0].severity == ValidationSeverity.ERROR
        assert target_issues[0].element_id == "t1"
        assert target_issues[0].field == "source_id"

    def test_solid_lift_valid_element_id(self):
        dsl = _make_dsl(
            _elem("cube", "Solid3D"),
            SolidLift(id="sl1", element_id="cube"),
        )
        issues = dsl.validate()
        assert not any(i.code == "unknown_target_element_id" for i in issues)

    def test_solid_lift_invalid_element_id(self):
        dsl = _make_dsl(SolidLift(id="sl1", element_id="missing"))
        issues = dsl.validate()
        target_issues = [i for i in issues if i.code == "unknown_target_element_id"]
        assert len(target_issues) == 1
        assert target_issues[0].field == "element_id"

    def test_solid_rotate_invalid_element_id(self):
        dsl = _make_dsl(SolidRotate(id="sr1", element_id="missing"))
        issues = dsl.validate()
        assert any(i.code == "unknown_target_element_id" for i in issues)

    def test_camera_inspect_invalid_element_id(self):
        dsl = _make_dsl(CameraInspect(id="ci1", element_id="missing"))
        issues = dsl.validate()
        assert any(i.code == "unknown_target_element_id" for i in issues)

    def test_camera_focus_valid_element_id(self):
        dsl = _make_dsl(
            _elem("e1"),
            CameraFocus(id="cf1", element_id="e1"),
        )
        issues = dsl.validate()
        assert not any(i.code == "unknown_target_element_id" for i in issues)

    def test_camera_focus_invalid_element_id(self):
        dsl = _make_dsl(CameraFocus(id="cf1", element_id="ghost"))
        issues = dsl.validate()
        assert any(i.code == "unknown_target_element_id" for i in issues)

    def test_plot_trace_valid_element_id(self):
        dsl = _make_dsl(
            _elem("plot1", "QuadraticPlot"),
            PlotTrace(id="pt1", element_id="plot1"),
        )
        issues = dsl.validate()
        assert not any(i.code == "unknown_target_element_id" for i in issues)

    def test_plot_trace_invalid_element_id(self):
        dsl = _make_dsl(PlotTrace(id="pt1", element_id="ghost"))
        issues = dsl.validate()
        assert any(i.code == "unknown_target_element_id" for i in issues)

    def test_target_after_source_in_timeline_is_valid(self):
        """Validation is order-independent: target can appear before source."""
        dsl = _make_dsl(
            SolidLift(id="sl1", element_id="cube"),
            _elem("cube", "Solid3D"),
        )
        issues = dsl.validate()
        assert not any(i.code == "unknown_target_element_id" for i in issues)

    def test_empty_element_id_not_flagged(self):
        """An empty string element_id is treated as 'no target' — not an error."""
        dsl = _make_dsl(SolidLift(id="sl1", element_id=""))
        issues = dsl.validate()
        assert not any(i.code == "unknown_target_element_id" for i in issues)


# ---------------------------------------------------------------------------
# 5. flex_group consistency
# ---------------------------------------------------------------------------

class TestFlexGroupConsistency:
    def test_valid_consecutive_flex_group(self):
        dsl = _make_dsl(
            _elem("a", flex_group="g1"),
            _elem("b", flex_group="g1"),
            _elem("c", flex_group="g1"),
        )
        issues = dsl.validate()
        flex_issues = [i for i in issues if "flex_group" in i.code]
        assert not flex_issues

    def test_single_member_flex_group_is_warning(self):
        dsl = _make_dsl(_elem("a", flex_group="g1"))
        issues = dsl.validate()
        single = [i for i in issues if i.code == "flex_group_single_member"]
        assert len(single) == 1
        assert single[0].severity == ValidationSeverity.WARNING

    def test_non_consecutive_flex_group_is_error(self):
        dsl = _make_dsl(
            _elem("a", flex_group="g1"),
            _elem("x"),  # interrupts the group
            _elem("b", flex_group="g1"),
        )
        issues = dsl.validate()
        nc = [i for i in issues if i.code == "flex_group_non_consecutive"]
        assert len(nc) == 1
        assert nc[0].severity == ValidationSeverity.ERROR

    def test_two_separate_valid_flex_groups(self):
        dsl = _make_dsl(
            _elem("a", flex_group="g1"),
            _elem("b", flex_group="g1"),
            _elem("c"),
            _elem("d", flex_group="g2"),
            _elem("e", flex_group="g2"),
        )
        issues = dsl.validate()
        flex_issues = [i for i in issues if "flex_group" in i.code]
        assert not flex_issues

    def test_no_flex_group_no_issue(self):
        dsl = _make_dsl(_elem("a"), _elem("b"), _elem("c"))
        issues = dsl.validate()
        flex_issues = [i for i in issues if "flex_group" in i.code]
        assert not flex_issues


# ---------------------------------------------------------------------------
# raise_on_error behaviour
# ---------------------------------------------------------------------------

class TestRaiseOnError:
    def test_no_errors_does_not_raise(self):
        dsl = _make_dsl(_elem("e1"), _elem("e2"))
        # Should not raise
        issues = dsl.validate(raise_on_error=True)
        assert isinstance(issues, list)

    def test_errors_raise_dsl_validation_error(self):
        dsl = _make_dsl(
            TransformElement(id="t1", source_id="nonexistent"),
        )
        with pytest.raises(DSLValidationError) as exc_info:
            dsl.validate(raise_on_error=True)
        err = exc_info.value
        assert len(err.errors) >= 1
        assert "unknown_target_element_id" in str(err)

    def test_warnings_alone_do_not_raise(self):
        dsl = _make_dsl(_elem("e1", "UnknownType"))
        # Only a warning — should not raise
        issues = dsl.validate(raise_on_error=True)
        assert any(i.code == "unknown_element_type" for i in issues)

    def test_dsl_validation_error_has_issues_attribute(self):
        dsl = _make_dsl(
            _elem("dup"),
            _elem("dup"),
        )
        with pytest.raises(DSLValidationError) as exc_info:
            dsl.validate(raise_on_error=True)
        assert hasattr(exc_info.value, "issues")
        assert hasattr(exc_info.value, "errors")


# ---------------------------------------------------------------------------
# ValidationIssue helpers
# ---------------------------------------------------------------------------

class TestValidationIssue:
    def test_to_dict_keys(self):
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            code="duplicate_element_id",
            message="Duplicate id 'x'",
            element_id="x",
            field="id",
        )
        d = issue.to_dict()
        assert d["severity"] == "error"
        assert d["code"] == "duplicate_element_id"
        assert d["element_id"] == "x"
        assert d["field"] == "id"

    def test_str_includes_severity_and_code(self):
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            code="unknown_element_type",
            message="Type 'Foo' is unknown",
            element_id="e1",
        )
        s = str(issue)
        assert "WARNING" in s
        assert "unknown_element_type" in s
        assert "e1" in s

    def test_str_no_element_id(self):
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            code="flex_group_non_consecutive",
            message="Gap in flex group",
        )
        s = str(issue)
        assert "id=" not in s


# ---------------------------------------------------------------------------
# Backward compatibility: existing projects must pass validation
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """Validation must pass (no errors) on DSLs produced by CanvasBuilder
    for the existing projects in projects/.  We test the builder output
    directly without importing project scenes (which require Manim).
    """

    def test_simple_builder_output_passes_validation(self):
        from canvas.builder import CanvasBuilder
        b = CanvasBuilder(title="Compat test")
        t = b.add_tape("main")
        t.add_heading("Hello")
        t.add_math(r"x^2 + y^2 = 1")
        t.add_body("Some body text here.")
        dsl = b.build()
        issues = dsl.validate()
        errors = _errors(issues)
        assert not errors, f"Builder output should have no errors: {errors}"

    def test_builder_with_camera_move_passes(self):
        from canvas.builder import CanvasBuilder
        b = CanvasBuilder(title="Camera compat")
        t = b.add_tape("main")
        t.add_text("Line 1")
        t.add_camera_move(dy=4.0, run_time=1.5)
        t.add_text("Line 2")
        dsl = b.build()
        issues = dsl.validate()
        assert not _errors(issues)

    def test_builder_with_solid_and_inspect_passes(self):
        from canvas.builder import CanvasBuilder
        b = CanvasBuilder(title="Solid compat")
        t = b.add_tape("main")
        b.add_solid(shape="cube", size=2.0, id="cube_1")
        b.add_solid_lift("cube_1", lift=1.5)
        b.add_camera_inspect("cube_1", preset="orbit")
        b.add_solid_rotation("cube_1", preset="show_right")
        dsl = b.build()
        issues = dsl.validate()
        assert not _errors(issues)

    def test_builder_flex_row_passes(self):
        from canvas.builder import CanvasBuilder
        b = CanvasBuilder(title="Flex compat")
        t = b.add_tape("main")
        t.add_flex_row([b.text_spec("left"), b.math_spec(r"x^2")])
        dsl = b.build()
        issues = dsl.validate()
        assert not _errors(issues)

    def test_empty_dsl_passes(self):
        dsl = SheetDSL()
        issues = dsl.validate()
        assert not _errors(issues)
