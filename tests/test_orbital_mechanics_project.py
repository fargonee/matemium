from math import hypot, sqrt

import pytest

from projects.orbital_mechanics.helpers import (
    DISPLAY_ORBIT_RADIUS,
    orbital_world_state,
    simulate_trajectory,
    visual_trials,
)


def test_visual_speed_ladder_is_monotonic_and_includes_bound_ellipse() -> None:
    trials = visual_trials()

    assert [trial["id"] for trial in trials] == [
        "drop",
        "short_arc",
        "long_arc",
        "reentry",
        "circular",
        "ellipse",
        "escape",
    ]
    assert [float(trial["factor"]) for trial in trials] == sorted(
        float(trial["factor"]) for trial in trials
    )
    ellipse = next(trial for trial in trials if trial["id"] == "ellipse")
    assert 1.0 < float(ellipse["factor"]) < sqrt(2.0)


def test_drop_hits_earth_while_circular_path_holds_radius() -> None:
    drop = simulate_trajectory(0.0)
    circular = simulate_trajectory(1.0)

    assert hypot(*drop[-1]) <= 1.0
    assert max(abs(hypot(*point) - DISPLAY_ORBIT_RADIUS) for point in circular) < 1e-6


def test_orbital_world_accepts_cinematic_states() -> None:
    state = orbital_world_state("short_arc", vectors=True, animate_satellite=True)

    assert state == {
        "regime": "short_arc",
        "vectors": True,
        "animate_satellite": True,
    }
    with pytest.raises(ValueError, match="Unknown orbital regime"):
        orbital_world_state("warp")
