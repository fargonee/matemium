"""Inspect keyframe path compilation tests."""

from __future__ import annotations

from canvas.inspect_path import (
    InspectKeyframe,
    compile_inspect_segments,
    densify_path,
    preset_keyframes,
    resolve_inspect_keyframes,
)
from canvas.dsl import CameraInspect, ObservationMode
from canvas.inspect_engine import InspectEngine


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


def test_densified_camera_path_uses_continuous_linear_subsegments():
    kfs = [
        InspectKeyframe(phi=60.0, theta=0.0, run_time=1.0),
        InspectKeyframe(phi=55.0, theta=35.0, run_time=1.8),
    ]

    segments = compile_inspect_segments(kfs, (0.0, 0.0, 0.0), curve="smooth")

    assert len(segments) > len(kfs)
    assert {segment.rate_func for segment in segments[1:]} == {"linear"}


def test_inspect_from_tape_cuts_to_first_pose_before_world_fade():
    class Registry:
        def pause_far_updaters(self, *args, **kwargs):
            pass

    class CameraController:
        current_y = 0.0

        def __init__(self):
            self.animated_poses = []

        def pose_anims(self, pose, run_time, rate_func):
            self.animated_poses.append(pose)
            return []

        def return_to_sheet(self, *args, **kwargs):
            pass

    class Scene:
        def __init__(self):
            self.registry = Registry()
            self._observation_mode = ObservationMode.TAPE_SCROLL
            self.entered_at = None
            self.play_calls = 0

        def _enter_world_context(self, *, initial_pose=None, run_time=0.7):
            self.entered_at = initial_pose
            self._observation_mode = ObservationMode.NORMAL_3D

        def play(self, *args, **kwargs):
            self.play_calls += 1

        def wait(self, duration):
            pass

    scene = Scene()
    camera = CameraController()
    inspect = CameraInspect(
        id="inspect",
        element_id="world",
        path=[
            {"phi": 62.0, "theta": -30.0, "zoom": 1.1, "run_time": 1.2},
            {"phi": 58.0, "theta": -5.0, "zoom": 1.16, "run_time": 1.8},
        ],
    )

    InspectEngine(scene, camera_ctl=camera).apply(
        inspect,
        mob=type("Mob", (), {"get_center": lambda self: (0.0, 0.0, 0.0)})(),
        spec=type("Spec", (), {"world_transform": None})(),
    )

    assert scene.entered_at is not None
    assert scene.entered_at.phi == 62.0
    assert all(pose != scene.entered_at for pose in camera.animated_poses)
