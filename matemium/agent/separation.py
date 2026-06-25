"""Guardrail 1 — radical decoupling of scenes narrative vs assets engine room."""

from __future__ import annotations

import re
from typing import Any

from .models import (
    AssetsConfig,
    DecoupledArtifacts,
    ScenesConfig,
    TimingBlueprint,
    WaitAnchor,
)
from .script_parser import extract_div_markers, parse_narrative_blocks

BUILDER_CALL_RE = re.compile(
    r"b\.(add_\w+)\s*\((.*?)\)",
    re.DOTALL,
)
LATEX_IN_CALL_RE = re.compile(r'r"([^"]+)"|r\'([^\']+)\'')


def _classify_builder_call(method: str, args_text: str) -> tuple[str, dict[str, Any]]:
    """Split a builder invocation into narrative vs asset-bearing content."""
    payload: dict[str, Any] = {"method": method, "args": args_text.strip()}
    if method == "add_math":
        match = LATEX_IN_CALL_RE.search(args_text)
        if match:
            payload["latex_ref"] = f"assets.latex_{method}"
    if method == "add_3d":
        payload["surface_ref"] = "assets.mesh_definitions"
    return method, payload


def build_decoupled_artifacts(script: str, blueprint: TimingBlueprint) -> DecoupledArtifacts:
    """Produce scenes_config and assets_config from script + timing blueprint."""
    blocks = parse_narrative_blocks(script)
    div_markers = extract_div_markers(script)
    segment_by_id = {s.block_id: s for s in blueprint.segments}

    builder_calls: list[dict[str, Any]] = []
    wait_anchors: list[WaitAnchor] = []
    latex_strings: list[str] = []
    coordinate_sets: list[dict[str, Any]] = []
    computations: list[dict[str, Any]] = []
    mesh_definitions: list[dict[str, Any]] = []
    part_functions: list[str] = []

    for block in blocks:
        fn_name = f"part_{block.title.lower().replace(' ', '_')}"
        part_functions.append(fn_name)

        for method, payload in (
            _classify_builder_call(m.group(1), m.group(2))
            for m in BUILDER_CALL_RE.finditer(block.body)
        ):
            if method in {"add_math", "add_3d"}:
                narrative_call = {**payload, "content_ref": f"assets.{method}"}
                builder_calls.append(narrative_call)
            else:
                builder_calls.append(payload)

        segment = segment_by_id.get(block.block_id)
        if segment:
            wait_anchors.append(
                WaitAnchor(
                    block_id=block.block_id,
                    duration=segment.wait_duration,
                    after_call=f"{fn_name}_tail",
                )
            )

        for idx, latex in enumerate(block.latex_fragments):
            latex_strings.append(latex)
            computations.append(
                {
                    "id": f"{block.block_id}_latex_{idx}",
                    "kind": "latex_eval",
                    "expression": latex,
                    "block_id": block.block_id,
                }
            )

        if block.has_3d:
            surface_match = re.search(r'add_3d\s*\(\s*["\']([^"\']+)["\']', block.body)
            surface = surface_match.group(1) if surface_match else "z = x^2 - y^2"
            mesh_definitions.append(
                {
                    "id": f"{block.block_id}_surface",
                    "equation": surface,
                    "resolution": (32, 32),
                    "block_id": block.block_id,
                }
            )
            coordinate_sets.append(
                {
                    "id": f"{block.block_id}_grid",
                    "x_range": (-3.0, 3.0),
                    "y_range": (-3.0, 3.0),
                    "samples": 64,
                }
            )

    scenes = ScenesConfig(
        div_markers=div_markers,
        part_functions=tuple(part_functions),
        builder_calls=tuple(builder_calls),
        wait_anchors=tuple(wait_anchors),
        orientation="portrait",
    )
    assets = AssetsConfig(
        latex_strings=tuple(latex_strings),
        coordinate_sets=tuple(coordinate_sets),
        computations=tuple(computations),
        mesh_definitions=tuple(mesh_definitions),
    )
    return DecoupledArtifacts(scenes=scenes, assets=assets)