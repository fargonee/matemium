"""Deterministic two-body data for the orbital-mechanics flagship.

The visual model uses Earth radii and a normalized gravitational parameter so
all paths share one stable coordinate system. Public labels are calculated from
SI constants at 400 km altitude.
"""

from __future__ import annotations

from math import cos, pi, sin, sqrt

import numpy as np
from manim import (
    BLUE_E,
    PI,
    RIGHT,
    UP,
    Arrow,
    Circle,
    Cube,
    Dot3D,
    Rectangle,
    Sphere,
    VGroup,
    VMobject,
)

from canvas import register_object_kind

EARTH_RADIUS_M = 6_371_000.0
EARTH_MU = 3.986_004_418e14
STANDARD_GRAVITY_M_S2 = 9.80665

ALTITUDE_KM = 400.0
DISPLAY_EARTH_RADIUS = 1.0
DISPLAY_ORBIT_RADIUS = 1.52  # altitude exaggerated and disclosed in the scene

EARTH_BLUE = "#2878c8"
EARTH_GLOW = "#5eb3ff"
REENTRY_CORAL = "#ff755f"
ORBIT_CYAN = "#4de3d1"
ESCAPE_GOLD = "#ffd166"
ELLIPSE_VIOLET = "#c59cff"
VELOCITY_GOLD = "#ffd166"
ACCELERATION_CORAL = "#ff755f"
MUTED = "#66758a"

WORLD_EARTH_RADIUS = 1.35
WORLD_ORBIT_RADIUS = WORLD_EARTH_RADIUS * DISPLAY_ORBIT_RADIUS


def circular_speed(altitude_km: float = ALTITUDE_KM) -> float:
    """Circular speed in km/s for a spherical-Earth two-body model."""

    radius_m = EARTH_RADIUS_M + altitude_km * 1000.0
    return sqrt(EARTH_MU / radius_m) / 1000.0


def gravity_at_altitude(altitude_km: float = ALTITUDE_KM) -> float:
    """Gravitational acceleration in m/s² at the requested altitude."""

    radius_m = EARTH_RADIUS_M + altitude_km * 1000.0
    return EARTH_MU / radius_m**2


def gravity_fraction(altitude_km: float = ALTITUDE_KM) -> float:
    """Fraction of standard surface gravity at altitude."""

    return gravity_at_altitude(altitude_km) / STANDARD_GRAVITY_M_S2


def launch_trials(altitude_km: float = ALTITUDE_KM) -> list[dict[str, str | float]]:
    """Three regimes sharing one initial position and varying only speed."""

    orbit = circular_speed(altitude_km)
    return [
        {
            "id": "reentry",
            "label": "too slow",
            "factor": 0.78,
            "speed_km_s": 0.78 * orbit,
            "outcome": "path intersects Earth",
            "color": REENTRY_CORAL,
        },
        {
            "id": "circular",
            "label": "circular speed",
            "factor": 1.0,
            "speed_km_s": orbit,
            "outcome": "closed circular orbit",
            "color": ORBIT_CYAN,
        },
        {
            "id": "escape",
            "label": "above escape speed",
            "factor": 1.46,
            "speed_km_s": 1.46 * orbit,
            "outcome": "positive-energy escape",
            "color": ESCAPE_GOLD,
        },
    ]


def visual_trials() -> list[dict[str, str | float]]:
    """Cinematic speed ladder used by the persistent orbital world."""

    trials = {
        str(trial["id"]): dict(trial)
        for trial in launch_trials()
    }
    return [
        {
            "id": "drop",
            "label": "no sideways speed",
            "factor": 0.0,
            "color": REENTRY_CORAL,
        },
        {
            "id": "short_arc",
            "label": "a little sideways speed",
            "factor": 0.38,
            "color": REENTRY_CORAL,
        },
        {
            "id": "long_arc",
            "label": "more sideways speed",
            "factor": 0.62,
            "color": REENTRY_CORAL,
        },
        trials["reentry"],
        trials["circular"],
        {
            "id": "ellipse",
            "label": "faster, still bound",
            "factor": 1.08,
            "color": ELLIPSE_VIOLET,
        },
        trials["escape"],
    ]


def _visual_trial(regime: str) -> dict[str, str | float]:
    return next(item for item in visual_trials() if item["id"] == regime)


def earth_circle(samples: int = 181) -> list[list[float]]:
    """Sample the normalized Earth circumference."""

    return [
        [
            DISPLAY_EARTH_RADIUS * cos(2.0 * pi * index / (samples - 1)),
            DISPLAY_EARTH_RADIUS * sin(2.0 * pi * index / (samples - 1)),
        ]
        for index in range(samples)
    ]


def _derivative(state: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x, y, vx, vy = state
    radius = sqrt(x * x + y * y)
    inverse_r3 = 1.0 / radius**3
    return vx, vy, -x * inverse_r3, -y * inverse_r3


def _rk4_step(
    state: tuple[float, float, float, float],
    dt: float,
) -> tuple[float, float, float, float]:
    k1 = _derivative(state)
    k2 = _derivative(tuple(value + 0.5 * dt * slope for value, slope in zip(state, k1)))
    k3 = _derivative(tuple(value + 0.5 * dt * slope for value, slope in zip(state, k2)))
    k4 = _derivative(tuple(value + dt * slope for value, slope in zip(state, k3)))
    return tuple(
        value + dt * (a + 2.0 * b + 2.0 * c + d) / 6.0
        for value, a, b, c, d in zip(state, k1, k2, k3, k4)
    )


def simulate_trajectory(
    speed_factor: float,
    *,
    dt: float = 0.012,
    max_time: float = 11.0,
    sample_every: int = 5,
) -> list[list[float]]:
    """Integrate a normalized two-body path from a common top launch point.

    Normalized units use ``mu = 1``. The initial velocity is tangent to the
    circular teaching radius. Re-entry stops at Earth's surface; open paths stop
    when they leave the display envelope.
    """

    radius = DISPLAY_ORBIT_RADIUS
    circular_velocity = sqrt(1.0 / radius)
    state = (0.0, radius, speed_factor * circular_velocity, 0.0)
    points = [[state[0], state[1]]]
    steps = int(max_time / dt)
    for index in range(1, steps + 1):
        state = _rk4_step(state, dt)
        x, y, _, _ = state
        distance = sqrt(x * x + y * y)
        if index % sample_every == 0:
            points.append([x, y])
        if distance <= DISPLAY_EARTH_RADIUS:
            points.append([x, y])
            break
        if distance >= 3.05:
            points.append([x, y])
            break
    return points


def orbit_plot_series(active: str | None = None) -> list[dict[str, object]]:
    """Earth plus three paths, optionally muting inactive trials."""

    series: list[dict[str, object]] = [
        {
            "id": "earth",
            "points": earth_circle(),
            "color": EARTH_BLUE,
            "stroke_width": 9,
            "smooth": True,
        }
    ]
    for trial in launch_trials():
        trial_id = str(trial["id"])
        color = str(trial["color"]) if active in (None, trial_id) else MUTED
        width = 6 if active == trial_id else 4
        series.append(
            {
                "id": trial_id,
                "points": simulate_trajectory(float(trial["factor"])),
                "color": color,
                "stroke_width": width,
                "smooth": True,
            }
        )
    return series


def one_trial_plot_series(trial_id: str) -> list[dict[str, object]]:
    """Earth and one selected launch path for staged morphing."""

    trial = next(item for item in launch_trials() if item["id"] == trial_id)
    return [
        {
            "id": "earth",
            "points": earth_circle(),
            "color": EARTH_BLUE,
            "stroke_width": 9,
            "smooth": True,
        },
        {
            "id": "trial",
            "points": simulate_trajectory(float(trial["factor"])),
            "color": str(trial["color"]),
            "stroke_width": 6,
            "smooth": True,
        },
    ]


def launch_markers() -> list[dict[str, object]]:
    return [
        {
            "id": "launch",
            "point": [0.0, DISPLAY_ORBIT_RADIUS],
            "color": "#ffffff",
            "radius": 0.09,
        }
    ]


def local_vector_diagram() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Semantic freeze-frame diagram for tangent velocity and inward acceleration."""

    nodes: list[dict[str, object]] = [
        {
            "id": "earth",
            "label": "EARTH",
            "position": [-0.35, -0.85],
            "shape": "circle",
            "width": 2.5,
            "height": 2.5,
            "color": EARTH_BLUE,
            "fill_color": "#12365a",
            "fill_opacity": 0.52,
            "font_size": 24,
        },
        {
            "id": "satellite",
            "label": "●",
            "position": [-0.35, 0.95],
            "shape": "circle",
            "width": 0.42,
            "height": 0.42,
            "color": "#ffffff",
            "fill_color": "#ffffff",
            "fill_opacity": 0.95,
            "font_size": 18,
        },
        {
            "id": "velocity_tip",
            "label": "v",
            "position": [2.6, 0.95],
            "shape": "rounded",
            "width": 1.6,
            "height": 0.55,
            "color": VELOCITY_GOLD,
            "fill_color": "#3c3318",
            "fill_opacity": 0.75,
            "font_size": 20,
        },
    ]
    edges: list[dict[str, object]] = [
        {
            "id": "velocity",
            "from": "satellite",
            "to": "velocity_tip",
            "directed": True,
            "buff": 0.28,
            "color": VELOCITY_GOLD,
            "stroke_width": 6,
        },
        {
            "id": "acceleration",
            "from": "satellite",
            "to": "earth",
            "label": "a = gravity",
            "directed": True,
            "buff": 0.28,
            "color": ACCELERATION_CORAL,
            "stroke_width": 6,
            "font_size": 20,
        },
    ]
    return nodes, edges


# ---------------------------------------------------------------------------
# Project-local world object
# ---------------------------------------------------------------------------


def orbital_world_state(
    regime: str = "circular",
    *,
    vectors: bool = True,
    animate_satellite: bool | None = None,
) -> dict[str, object]:
    """Serializable state for the flagship's persistent spatial model."""

    valid = {str(item["id"]) for item in visual_trials()}
    if regime not in valid:
        raise ValueError(f"Unknown orbital regime: {regime}")
    if animate_satellite is None:
        animate_satellite = regime == "circular"
    return {
        "regime": regime,
        "vectors": bool(vectors),
        "animate_satellite": bool(animate_satellite),
    }


def _world_path(regime: str) -> VMobject:
    trial = _visual_trial(regime)
    points = np.array(
        [
            [WORLD_EARTH_RADIUS * x, WORLD_EARTH_RADIUS * y, 0.0]
            for x, y in simulate_trajectory(float(trial["factor"]))
        ],
        dtype=float,
    )
    path = VMobject(color=str(trial["color"]), stroke_width=6)
    path.set_points_smoothly(points)
    path.set_stroke(opacity=0.98)
    return path


def _satellite_model() -> VGroup:
    body = Cube(side_length=0.28, fill_opacity=1.0, stroke_width=0.9)
    body.set_fill("#e9f1fa")
    panel_left = Rectangle(
        width=0.54,
        height=0.18,
        color=ORBIT_CYAN,
        fill_color=BLUE_E,
        fill_opacity=0.9,
        stroke_width=1.2,
    ).shift(RIGHT * 0.41)
    panel_right = panel_left.copy().shift(RIGHT * -0.82)
    return VGroup(panel_left, body, panel_right)


def _build_orbital_world(elem, wrap, target_width, surface_factory):
    """Build a complete reusable world without adding orbital rules to core."""

    content = dict(elem.content or {})
    regime = str(content.get("regime", "circular"))
    trial = _visual_trial(regime)
    speed_factor = float(trial["factor"])
    show_vectors = bool(content.get("vectors", True))
    animate_satellite = bool(content.get("animate_satellite", regime == "circular"))

    glow = Sphere(
        radius=WORLD_EARTH_RADIUS * 1.055,
        resolution=(20, 12),
        fill_opacity=0.08,
        stroke_opacity=0.0,
    ).set_fill(EARTH_GLOW)
    earth = Sphere(
        radius=WORLD_EARTH_RADIUS,
        resolution=(32, 18),
        fill_opacity=0.88,
        stroke_width=0.35,
    ).set_fill(EARTH_BLUE)

    equator = Circle(
        radius=WORLD_EARTH_RADIUS * 1.006,
        color=EARTH_GLOW,
        stroke_width=1.25,
        stroke_opacity=0.42,
    )
    meridian_a = equator.copy().rotate(PI / 2, axis=RIGHT)
    meridian_b = equator.copy().rotate(PI / 2, axis=UP)
    globe_grid = VGroup(equator, meridian_a, meridian_b)

    active_path = _world_path(regime)
    guide_path = Circle(
        radius=WORLD_ORBIT_RADIUS,
        color=MUTED,
        stroke_width=1.4,
        stroke_opacity=0.45,
    )

    launch = np.array([0.0, WORLD_ORBIT_RADIUS, 0.08])
    satellite = _satellite_model().move_to(launch)
    satellite_halo = Dot3D(
        point=launch,
        radius=0.16,
        color="#ffffff",
        resolution=(10, 10),
    ).set_opacity(0.24)
    velocity_length = max(0.02, 1.08 * speed_factor)
    velocity = Arrow(
        start=launch,
        end=launch + np.array([velocity_length, 0.0, 0.0]),
        color=VELOCITY_GOLD,
        buff=0.0,
        stroke_width=7.0,
        max_tip_length_to_length_ratio=0.18,
    )
    gravity = Arrow(
        start=launch,
        end=launch + np.array([0.0, -1.02, 0.0]),
        color=ACCELERATION_CORAL,
        buff=0.0,
        stroke_width=7.0,
        max_tip_length_to_length_ratio=0.18,
    )
    vectors = VGroup(velocity, gravity)
    if speed_factor < 0.01:
        velocity.set_opacity(0.0)
    if not show_vectors:
        vectors.set_opacity(0.0)

    moving_body = VGroup(satellite_halo, satellite, velocity, gravity)
    if animate_satellite:
        path_points = np.array(
            [
                [WORLD_EARTH_RADIUS * x, WORLD_EARTH_RADIUS * y, 0.08]
                for x, y in simulate_trajectory(speed_factor)
            ],
            dtype=float,
        )
        elapsed = 0.0
        duration = 4.8 if regime in {"circular", "ellipse", "escape"} else 2.4

        def follow_trajectory(group, dt):
            nonlocal elapsed
            elapsed = min(elapsed + dt, duration)
            progress = elapsed / duration
            sample = progress * (len(path_points) - 1)
            index = min(int(sample), len(path_points) - 1)
            next_index = min(index + 1, len(path_points) - 1)
            position = (
                path_points[index] * (1.0 - (sample - index))
                + path_points[next_index] * (sample - index)
            )
            previous = path_points[max(index - 1, 0)]
            following = path_points[next_index]
            tangent = following - previous
            tangent[2] = 0.0
            tangent_norm = np.linalg.norm(tangent)
            if tangent_norm > 1e-8:
                tangent /= tangent_norm
            inward = -position.copy()
            inward[2] = 0.0
            inward_norm = np.linalg.norm(inward)
            if inward_norm > 1e-8:
                inward /= inward_norm

            satellite_halo.move_to(position)
            satellite.move_to(position)
            velocity.put_start_and_end_on(position, position + tangent * velocity_length)
            gravity.put_start_and_end_on(position, position + inward * 1.02)

        moving_body.add_updater(follow_trajectory)

    launch_marker = Dot3D(
        point=launch,
        radius=0.055,
        color="#ffffff",
        resolution=(8, 8),
    )
    world = VGroup(
        glow,
        earth,
        globe_grid,
        guide_path,
        active_path,
        launch_marker,
        moving_body,
    )
    world.matemium_parts = {
        "earth": earth,
        "glow": glow,
        "grid": globe_grid,
        "guide": guide_path,
        "path": active_path,
        "launch": launch_marker,
        "satellite": satellite,
        "satellite_halo": satellite_halo,
        "velocity": velocity,
        "gravity": gravity,
        "vectors": vectors,
    }
    return world


def _validate_orbital_world(content: object) -> list[str]:
    if not isinstance(content, dict):
        return ["content must be a mapping"]
    regime = str(content.get("regime", ""))
    valid = {str(item["id"]) for item in visual_trials()}
    if regime not in valid:
        return [f"regime must be one of {sorted(valid)}"]
    return []


def _orbital_world_parts(content: object) -> set[str]:
    return {
        "earth",
        "glow",
        "grid",
        "guide",
        "path",
        "launch",
        "satellite",
        "satellite_halo",
        "velocity",
        "gravity",
        "vectors",
    }


register_object_kind(
    "OrbitalWorld",
    build=_build_orbital_world,
    validate=_validate_orbital_world,
    parts=_orbital_world_parts,
)
