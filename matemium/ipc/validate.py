"""Sheet DSL validation for AI-generated payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Deferred to support lazy control-plane (imported inside validate functions)
from .protocol import ELEMENT_TYPES, KNOWN_TIMELINE_TYPES, LEGACY_TYPES


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    dsl: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


def _issue(path: str, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(path=path, code=code, message=message)


def validate_dsl_payload(
    dsl_data: Any,
    *,
    strict: bool = True,
) -> ValidationResult:
    """Validate raw JSON-compatible DSL before any render spend."""
    from canvas.dsl import SheetDSL

    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    if not isinstance(dsl_data, dict):
        return ValidationResult(
            valid=False,
            errors=[_issue("dsl", "INVALID_TYPE", "DSL root must be a JSON object")],
            warnings=[],
        )

    timeline = dsl_data.get("timeline")
    if timeline is None:
        errors.append(_issue("timeline", "MISSING_FIELD", "timeline is required"))
        timeline = []
    elif not isinstance(timeline, list):
        errors.append(_issue("timeline", "INVALID_TYPE", "timeline must be an array"))
        timeline = []
    elif len(timeline) == 0:
        warnings.append(_issue("timeline", "EMPTY_TIMELINE", "timeline has no items"))

    seen_ids: set[str] = set()
    for index, item in enumerate(timeline):
        path = f"timeline[{index}]"
        if not isinstance(item, dict):
            errors.append(_issue(path, "INVALID_TYPE", "timeline item must be an object"))
            continue

        item_type = item.get("type")
        if not item_type:
            errors.append(_issue(f"{path}.type", "MISSING_FIELD", "type is required"))
            continue
        if not isinstance(item_type, str):
            errors.append(_issue(f"{path}.type", "INVALID_TYPE", "type must be a string"))
            continue

        if item_type not in KNOWN_TIMELINE_TYPES:
            errors.append(
                _issue(f"{path}.type", "UNKNOWN_TYPE", f"Unknown timeline type: {item_type}")
            )
            continue

        if strict and item_type in LEGACY_TYPES:
            warnings.append(
                _issue(
                    f"{path}.type",
                    "LEGACY_TYPE",
                    f"{item_type} is a dev-only type; prefer core element types in production",
                )
            )

        item_id = item.get("id")
        if not item_id:
            errors.append(_issue(f"{path}.id", "MISSING_FIELD", "id is required"))
        elif not isinstance(item_id, str):
            errors.append(_issue(f"{path}.id", "INVALID_TYPE", "id must be a string"))
        elif item_id in seen_ids:
            errors.append(_issue(f"{path}.id", "DUPLICATE_ID", f"Duplicate id: {item_id}"))
        else:
            seen_ids.add(item_id)

        if item_type in ELEMENT_TYPES and item.get("content") is None:
            # Text/Math may use empty string; None is suspicious for AI output.
            if item_type in ("Text", "MathTex"):
                warnings.append(
                    _issue(f"{path}.content", "EMPTY_CONTENT", f"{item_type} has no content")
                )
            else:
                warnings.append(
                    _issue(f"{path}.content", "MISSING_CONTENT", f"{item_type} should include content")
                )

        pos = item.get("canvas_position")
        if item_type in ELEMENT_TYPES and pos is not None:
            if not isinstance(pos, (list, tuple)) or len(pos) != 3:
                errors.append(
                    _issue(
                        f"{path}.canvas_position",
                        "INVALID_POSITION",
                        "canvas_position must be [x, y, z]",
                    )
                )

    settings = dsl_data.get("canvas_settings")
    if settings is not None and not isinstance(settings, dict):
        errors.append(_issue("canvas_settings", "INVALID_TYPE", "canvas_settings must be an object"))

    if errors:
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    try:
        dsl = SheetDSL.from_dict(dsl_data)
    except Exception as exc:
        errors.append(_issue("dsl", "PARSE_ERROR", str(exc)))
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    return ValidationResult(valid=True, errors=[], warnings=warnings, dsl=dsl)