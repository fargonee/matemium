"""Generic, data-backed visual kinds shared by unrelated subject domains.

The schemas in this module contain no lesson semantics. Projects supply sampled
paths, plot series, or diagram nodes/edges and keep domain calculations local.
"""

from __future__ import annotations

from math import isfinite
from typing import Any, Iterable, Optional

import numpy as np
from manim import (
    Arrow,
    Axes,
    Circle,
    Dot,
    Line,
    Rectangle,
    RoundedRectangle,
    Text,
    VGroup,
    VMobject,
    WHITE,
)

from .dsl import CanvasElement

DEFAULT_BLUE = "#5eb3ff"


def _mapping(content: Any) -> dict[str, Any]:
    return dict(content) if isinstance(content, dict) else {}


def _finite_point(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) in (2, 3)
        and all(isinstance(item, (int, float)) and isfinite(float(item)) for item in value)
    )


def _points(value: Any) -> list[list[float]]:
    if not isinstance(value, list):
        return []
    return [
        [float(p[0]), float(p[1]), float(p[2]) if len(p) == 3 else 0.0]
        for p in value
        if _finite_point(p)
    ]


def validate_data_path(content: Any) -> list[str]:
    data = _mapping(content)
    points = data.get("points")
    issues: list[str] = []
    if not isinstance(points, list) or len(points) < 2:
        issues.append("'points' must contain at least two coordinates")
    elif any(not _finite_point(point) for point in points):
        issues.append("every path point must contain two or three finite numbers")
    return issues


def validate_data_plot(content: Any) -> list[str]:
    data = _mapping(content)
    issues: list[str] = []
    series = data.get("series")
    if not isinstance(series, list) or not series:
        return ["'series' must be a non-empty list"]
    seen: set[str] = set()
    for index, item in enumerate(series):
        if not isinstance(item, dict):
            issues.append(f"series[{index}] must be an object")
            continue
        sid = item.get("id")
        if not isinstance(sid, str) or not sid:
            issues.append(f"series[{index}].id must be a non-empty string")
        elif sid in seen:
            issues.append(f"duplicate series id {sid!r}")
        else:
            seen.add(sid)
        points = item.get("points")
        if not isinstance(points, list) or len(points) < 2:
            issues.append(f"series[{index}].points must contain at least two coordinates")
        elif any(not _finite_point(point) for point in points):
            issues.append(f"series[{index}] contains a malformed/non-finite point")
    for key in ("x_range", "y_range"):
        value = data.get(key)
        if value is not None and (
            not isinstance(value, (list, tuple))
            or len(value) < 2
            or not all(isinstance(x, (int, float)) and isfinite(float(x)) for x in value[:2])
            or float(value[0]) >= float(value[1])
        ):
            issues.append(f"{key!r} must start with two increasing finite numbers")
    marker_ids: set[str] = set()
    markers = data.get("markers", [])
    if not isinstance(markers, list):
        issues.append("'markers' must be a list")
    else:
        for index, marker in enumerate(markers):
            if not isinstance(marker, dict):
                issues.append(f"markers[{index}] must be an object")
                continue
            marker_id = marker.get("id")
            if not isinstance(marker_id, str) or not marker_id:
                issues.append(f"markers[{index}].id must be a non-empty string")
            elif marker_id in marker_ids:
                issues.append(f"duplicate marker id {marker_id!r}")
            else:
                marker_ids.add(marker_id)
            if not _finite_point(marker.get("point")):
                issues.append(f"markers[{index}].point must contain two or three finite numbers")
    return issues


def validate_diagram(content: Any) -> list[str]:
    data = _mapping(content)
    nodes = data.get("nodes")
    edges = data.get("edges", [])
    issues: list[str] = []
    if not isinstance(nodes, list) or not nodes:
        return ["'nodes' must be a non-empty list"]
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            issues.append(f"nodes[{index}] must be an object")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            issues.append(f"nodes[{index}].id must be a non-empty string")
        elif node_id in node_ids:
            issues.append(f"duplicate node id {node_id!r}")
        else:
            node_ids.add(node_id)
        if not _finite_point(node.get("position", [0.0, 0.0])):
            issues.append(f"nodes[{index}].position must contain two or three finite numbers")
    if not isinstance(edges, list):
        return issues + ["'edges' must be a list"]
    edge_ids: set[str] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            issues.append(f"edges[{index}] must be an object")
            continue
        edge_id = edge.get("id")
        if not isinstance(edge_id, str) or not edge_id:
            issues.append(f"edges[{index}].id must be a non-empty string")
        elif edge_id in edge_ids:
            issues.append(f"duplicate edge id {edge_id!r}")
        else:
            edge_ids.add(edge_id)
        for endpoint in ("from", "to"):
            if edge.get(endpoint) not in node_ids:
                issues.append(f"edges[{index}].{endpoint} references an unknown node")
    return issues


def data_path_parts(content: Any) -> set[str]:
    return {"path"}


def data_plot_parts(content: Any) -> set[str]:
    data = _mapping(content)
    parts = {f"series:{item['id']}" for item in data.get("series", []) if isinstance(item, dict) and item.get("id")}
    parts |= {f"marker:{item['id']}" for item in data.get("markers", []) if isinstance(item, dict) and item.get("id")}
    parts.add("axes")
    return parts


def diagram_parts(content: Any) -> set[str]:
    data = _mapping(content)
    parts = {f"node:{item['id']}" for item in data.get("nodes", []) if isinstance(item, dict) and item.get("id")}
    parts |= {f"edge:{item['id']}" for item in data.get("edges", []) if isinstance(item, dict) and item.get("id")}
    parts |= {
        f"edge-label:{item['id']}"
        for item in data.get("edges", [])
        if isinstance(item, dict) and item.get("id") and item.get("label")
    }
    return parts


def _attach_parts(group: VGroup, parts: dict[str, VMobject]) -> VGroup:
    group.matemium_parts = parts
    return group


def resolve_semantic_part(root: VMobject, part_id: str) -> Optional[VMobject]:
    parts = getattr(root, "matemium_parts", {})
    return parts.get(part_id) if isinstance(parts, dict) else None


def build_data_path(
    elem: CanvasElement,
    wrap: bool,
    target_width: Optional[float],
    surface_factory,
) -> VGroup:
    data = _mapping(elem.content)
    coords = [np.array(point) for point in _points(data.get("points"))]
    path = VMobject(
        color=str(data.get("color", DEFAULT_BLUE)),
        stroke_width=float(data.get("stroke_width", 4.0)),
    )
    if data.get("smooth", False):
        path.set_points_smoothly(coords)
    else:
        path.set_points_as_corners(coords)
    if data.get("closed", False) and coords:
        path.add_line_to(coords[0])
    group = VGroup(path)
    if data.get("arrow", False) and len(coords) >= 2:
        tip = Arrow(
            coords[-2],
            coords[-1],
            buff=0,
            color=str(data.get("color", DEFAULT_BLUE)),
            stroke_width=float(data.get("stroke_width", 4.0)),
            max_tip_length_to_length_ratio=0.22,
        )
        group.add(tip)
    _attach_parts(group, {"path": path})
    if target_width and group.width > 0:
        group.set_width(float(target_width))
    return group


def _range(values: Iterable[float], padding: float = 0.08) -> list[float]:
    values = list(values)
    low, high = min(values), max(values)
    if low == high:
        low, high = low - 1.0, high + 1.0
    pad = (high - low) * padding
    return [low - pad, high + pad, (high - low) / 4.0]


def build_data_plot(
    elem: CanvasElement,
    wrap: bool,
    target_width: Optional[float],
    surface_factory,
) -> VGroup:
    data = _mapping(elem.content)
    series = list(data.get("series") or [])
    all_points = [point for item in series for point in _points(item.get("points"))]
    x_range = list(data.get("x_range") or _range(point[0] for point in all_points))
    y_range = list(data.get("y_range") or _range(point[1] for point in all_points))
    axes = Axes(
        x_range=x_range,
        y_range=y_range,
        x_length=float(data.get("width", 8.0)),
        y_length=float(data.get("height", 4.5)),
        tips=bool(data.get("tips", False)),
    )
    parts: dict[str, VMobject] = {"axes": axes}
    visuals: list[VMobject] = [axes]
    for item in series:
        coords = [axes.c2p(point[0], point[1]) for point in _points(item.get("points"))]
        curve = VMobject(
            color=str(item.get("color", DEFAULT_BLUE)),
            stroke_width=float(item.get("stroke_width", 4.0)),
        )
        if item.get("smooth", data.get("smooth", True)):
            curve.set_points_smoothly(coords)
        else:
            curve.set_points_as_corners(coords)
        parts[f"series:{item['id']}"] = curve
        visuals.append(curve)
    for item in data.get("markers", []):
        point = item.get("point", [0.0, 0.0])
        marker = Dot(
            axes.c2p(float(point[0]), float(point[1])),
            radius=float(item.get("radius", 0.08)),
            color=str(item.get("color", "#ffdd66")),
        )
        parts[f"marker:{item['id']}"] = marker
        visuals.append(marker)
    group = _attach_parts(VGroup(*visuals), parts)
    if target_width and group.width > 0:
        group.set_width(float(target_width))
    return group


def _node_shape(node: dict[str, Any]) -> VMobject:
    width = float(node.get("width", 2.2))
    height = float(node.get("height", 1.0))
    color = str(node.get("color", DEFAULT_BLUE))
    shape = str(node.get("shape", "rounded")).lower()
    if shape == "circle":
        body = Circle(radius=max(width, height) / 2.0, color=color)
    elif shape == "rectangle":
        body = Rectangle(width=width, height=height, color=color)
    else:
        body = RoundedRectangle(width=width, height=height, corner_radius=0.15, color=color)
    body.set_fill(str(node.get("fill_color", color)), opacity=float(node.get("fill_opacity", 0.14)))
    label = Text(str(node.get("label", node.get("id", ""))), font_size=int(node.get("font_size", 24)), color=WHITE)
    if label.width > width * 0.82 and label.width > 0:
        label.set_width(width * 0.82)
    label.move_to(body.get_center())
    return VGroup(body, label)


def build_diagram(
    elem: CanvasElement,
    wrap: bool,
    target_width: Optional[float],
    surface_factory,
) -> VGroup:
    data = _mapping(elem.content)
    nodes: dict[str, VMobject] = {}
    parts: dict[str, VMobject] = {}
    for item in data.get("nodes", []):
        node = _node_shape(item)
        position = _points([item.get("position", [0.0, 0.0])])[0]
        node.move_to(np.array(position))
        nodes[item["id"]] = node
        parts[f"node:{item['id']}"] = node

    edges: list[VMobject] = []
    labels: list[VMobject] = []
    for item in data.get("edges", []):
        source, target = nodes[item["from"]], nodes[item["to"]]
        edge_cls = Arrow if item.get("directed", True) else Line
        edge = edge_cls(
            source.get_center(),
            target.get_center(),
            buff=float(item.get("buff", 0.5)),
            color=str(item.get("color", "#9aa4b2")),
            stroke_width=float(item.get("stroke_width", 3.0)),
        )
        edges.append(edge)
        if item.get("label"):
            label = Text(str(item["label"]), font_size=int(item.get("font_size", 18)), color=WHITE)
            label.move_to(edge.get_center() + np.array([0.0, 0.18, 0.0]))
            labels.append(label)
            parts[f"edge-label:{item['id']}"] = label
        parts[f"edge:{item['id']}"] = edge
    group = _attach_parts(VGroup(*edges, *nodes.values(), *labels), parts)
    if target_width and group.width > 0:
        group.set_width(float(target_width))
    return group


def measure_data_path(
    elem: CanvasElement,
    *,
    usable_width: float,
    style_width: Optional[float],
    style_height: Optional[float],
    wrap: Optional[bool],
) -> tuple[float, float, bool]:
    points = _points(_mapping(elem.content).get("points"))
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    natural_width = max(max(xs) - min(xs), 0.5)
    natural_height = max(max(ys) - min(ys), 0.5)
    width = min(float(style_width or natural_width), usable_width)
    height = float(style_height or natural_height * width / natural_width)
    return width, height, False


def measure_boxed(
    elem: CanvasElement,
    *,
    usable_width: float,
    style_width: Optional[float],
    style_height: Optional[float],
    wrap: Optional[bool],
) -> tuple[float, float, bool]:
    data = _mapping(elem.content)
    width = min(float(style_width or data.get("width", 8.0)), usable_width)
    height = float(style_height or data.get("height", 4.5))
    return width, height, False
