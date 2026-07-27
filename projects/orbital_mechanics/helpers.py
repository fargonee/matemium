"""Deterministic two-body data for the orbital-mechanics flagship.

The visual model uses Earth radii and a normalized gravitational parameter so
all paths share one stable coordinate system. Public labels are calculated from
SI constants at 400 km altitude.
"""

from __future__ import annotations

from math import cos, pi, sin, sqrt

EARTH_RADIUS_M = 6_371_000.0
EARTH_MU = 3.986_004_418e14
STANDARD_GRAVITY_M_S2 = 9.80665

ALTITUDE_KM = 400.0
DISPLAY_EARTH_RADIUS = 1.0
DISPLAY_ORBIT_RADIUS = 1.28  # altitude exaggerated and disclosed in the scene

EARTH_BLUE = "#2878c8"
EARTH_GLOW = "#5eb3ff"
REENTRY_CORAL = "#ff755f"
ORBIT_CYAN = "#4de3d1"
ESCAPE_GOLD = "#ffd166"
VELOCITY_GOLD = "#ffd166"
ACCELERATION_CORAL = "#ff755f"
MUTED = "#66758a"


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
