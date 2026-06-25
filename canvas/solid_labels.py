"""Billboard labels for 3D solids — always face the camera during inspect."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from manim import Mobject, Text, VGroup, WHITE

_BILLBOARD_ATTR = "_matemium_billboard_labels"
_DEFAULT_FONT_SIZE = 22


def parse_label_specs(content: Any) -> List[Dict[str, Any]]:
    """Extract label definitions from solid element content."""
    if not isinstance(content, dict):
        return []
    raw = content.get("labels")
    if not raw:
        return []
    if isinstance(raw, dict):
        return [raw]
    return [item for item in raw if isinstance(item, dict)]


def make_label_mobject(spec: Dict[str, Any]) -> Mobject:
    """Build one Text label positioned at a local 3D offset."""
    text = str(spec.get("text", spec.get("label", "")))
    at = spec.get("at", spec.get("position", (0.0, 0.0, 0.0)))
    if isinstance(at, (list, tuple)) and len(at) >= 3:
        pos = (float(at[0]), float(at[1]), float(at[2]))
    else:
        pos = (0.0, 0.0, 0.0)

    font_size = int(spec.get("font_size", _DEFAULT_FONT_SIZE))
    color = str(spec.get("color", "#ffdd66"))
    opacity = float(spec.get("opacity", 1.0))

    mob = Text(text, font_size=font_size, color=color).set_opacity(opacity)
    scale = float(spec.get("scale", 1.0))
    if scale != 1.0:
        mob.scale(scale)
    mob.move_to(pos)
    return mob


def make_solid_labels(specs: Sequence[Dict[str, Any]]) -> List[Mobject]:
    return [make_label_mobject(spec) for spec in specs]


def attach_labels_to_solid(body: Mobject, content: Any) -> Mobject:
    """Wrap a solid body with billboard-ready labels (local coords, center = origin)."""
    specs = parse_label_specs(content)
    if not specs:
        return body

    labels = make_solid_labels(specs)
    group = VGroup(body, *labels)
    setattr(group, _BILLBOARD_ATTR, labels)
    return group


def billboard_labels_for(mob: Mobject) -> List[Mobject]:
    """Return label mobjects that should use fixed camera orientation."""
    found = getattr(mob, _BILLBOARD_ATTR, None)
    if found:
        return list(found)
    return []


def apply_billboard_labels(scene, mob: Mobject) -> None:
    """Register labels so they always face the camera (ThreeDScene API)."""
    labels = billboard_labels_for(mob)
    if not labels:
        return
    if hasattr(scene, "add_fixed_orientation_mobjects"):
        scene.add_fixed_orientation_mobjects(*labels)