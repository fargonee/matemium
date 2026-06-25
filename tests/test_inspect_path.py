"""Inspect keyframe path compilation tests."""

from __future__ import annotations

from canvas.inspect_path import (
    InspectKeyframe,
    compile_inspect_segments,
    densify_path,
    preset_keyframes,
    resolve_inspect_keyframes,
)


def test_preset_orbit_produces_keyframes():
    kfs = preset_keyframes("orbit", steps=8)
    assert len(kfs) == 8
    assert kfs[-1].theta > kfs[0].theta


def test_resolve_inspect_from_preset():
    kfs = resolve_inspect_keyframes(preset="cardinals")
    assert len(kfs) >= 4


def test_resolve_inspect_from_dict_path():
    kfs = resolve_inspect_keyframes(
        path=[{"phi": 70.0, "theta": -30.0, "run_time": 1.0, "hold": 0.5}]
    )
    assert len(kfs) == 1
    assert kfs[0].phi == 70.0


def test_compile_inspect_segments_densifies_sparse_path():
    kfs = [
        InspectKeyframe(phi=60.0, theta=0.0, run_time=1.0),
        InspectKeyframe(phi=60.0, theta=90.0, run_time=1.0),
    ]
    segments = compile_inspect_segments(kfs, (0.0, 0.0, 0.0), curve="smooth")
    assert len(segments) > len(kfs)


def test_densify_skipped_for_linear_curve():
    kfs = [
        InspectKeyframe(phi=60.0, theta=0.0, run_time=1.0),
        InspectKeyframe(phi=60.0, theta=90.0, run_time=1.0),
    ]
    dense = densify_path(kfs, (0.0, 0.0, 0.0), curve="linear")
    assert len(dense) == 2