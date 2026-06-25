"""Solid rotation keyframe path tests."""

from __future__ import annotations

from canvas.rotation_path import (
    RotateKeyframe,
    compile_rotation_segments,
    preset_rotation_keyframes,
    resolve_rotation_keyframes,
)


def test_preset_tumble_has_multiple_steps():
    kfs = preset_rotation_keyframes("tumble")
    assert len(kfs) >= 3


def test_resolve_rotation_from_preset():
    kfs = resolve_rotation_keyframes(preset="show_back")
    assert len(kfs) == 1
    assert kfs[0].angle == 180.0


def test_resolve_rotation_single_axis_angle():
    kfs = resolve_rotation_keyframes(axis="x", angle=45.0, hold=0.5)
    assert len(kfs) == 1
    assert kfs[0].axis == "x"
    assert kfs[0].angle == 45.0
    assert kfs[0].hold == 0.5


def test_compile_rotation_segments_one_per_keyframe():
    kfs = [
        RotateKeyframe(axis="y", angle=90.0),
        RotateKeyframe(axis="x", angle=30.0),
    ]
    segments = compile_rotation_segments(kfs)
    assert len(segments) == 2