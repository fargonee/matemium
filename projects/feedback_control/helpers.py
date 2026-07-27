"""Deterministic cruise-control model and visuals for the engineering flagship.

This is a teaching model, not a production vehicle controller.  Vehicle speed
is coupled to a first-order actuator.  A PI controller rejects a constant hill
load; actuator lag makes aggressive tuning visibly underdamped.
"""

from __future__ import annotations

BG = "#07131d"
WHITE = "#f4f8fc"
MUTED = "#63778b"
TARGET = "#ffd166"
MEASURED = "#4da3ff"
ERROR = "#ff7b72"
COMMAND = "#5ce1a8"
SETTLED = "#79e36b"
DISTURBANCE = "#ff9f5a"
PANEL = "#152535"

TARGET_SPEED = 25.0
HILL_START = 3.0
HILL_LOAD = 3.0
DT = 0.04
DURATION = 20.0
ACTUATOR_TAU = 2.2
PLANT_GAIN = 0.55
SPEED_DAMPING = 0.22

TUNINGS = {
    "slow": {"kp": 0.8, "ki": 0.08, "color": "#7f9db8"},
    "balanced": {"kp": 2.5, "ki": 0.55, "color": COMMAND},
    "aggressive": {"kp": 8.0, "ki": 2.0, "color": ERROR},
}


def simulate(
    kp: float,
    ki: float,
    *,
    feedback: bool = True,
) -> list[dict[str, float]]:
    """Euler-integrate the disclosed actuator + longitudinal teaching model."""

    speed = TARGET_SPEED
    actuator = 5.0
    integral = 0.0
    samples: list[dict[str, float]] = []
    steps = int(DURATION / DT)
    for index in range(steps + 1):
        time = index * DT
        hill = HILL_LOAD if time >= HILL_START else 0.0
        error = TARGET_SPEED - speed if feedback else 0.0
        integral += error * DT
        command = 5.0 + kp * error + ki * integral if feedback else 5.0
        actuator += DT * (command - actuator) / ACTUATOR_TAU
        speed += DT * (
            PLANT_GAIN * (actuator - 5.0 - hill)
            - SPEED_DAMPING * (speed - TARGET_SPEED)
        )
        samples.append(
            {
                "time": time,
                "speed": speed,
                "error": TARGET_SPEED - speed,
                "command": command,
                "actuator": actuator,
                "hill": hill,
            }
        )
    return samples


def sampled_points(samples: list[dict[str, float]], key: str, every: int = 4) -> list[list[float]]:
    return [
        [sample["time"], sample[key]]
        for index, sample in enumerate(samples)
        if index % every == 0 or index == len(samples) - 1
    ]


def response_series(active: str | None = None) -> list[dict[str, object]]:
    series: list[dict[str, object]] = [
        {
            "id": "target",
            "points": [[0.0, TARGET_SPEED], [DURATION, TARGET_SPEED]],
            "color": TARGET,
            "stroke_width": 4,
        },
        {
            "id": "hill",
            "points": [[HILL_START, 17.0], [HILL_START, 27.0]],
            "color": DISTURBANCE,
            "stroke_width": 3,
        },
    ]
    for name, tuning in TUNINGS.items():
        color = str(tuning["color"]) if active in (None, name) else MUTED
        series.append(
            {
                "id": name,
                "points": sampled_points(
                    simulate(float(tuning["kp"]), float(tuning["ki"])),
                    "speed",
                ),
                "color": color,
                "stroke_width": 7 if active == name else 4,
                "smooth": True,
            }
        )
    series.append(
        {
            "id": "open",
            "points": sampled_points(simulate(0.0, 0.0, feedback=False), "speed"),
            "color": "#9a6cff" if active in (None, "open") else MUTED,
            "stroke_width": 7 if active == "open" else 4,
            "smooth": True,
        }
    )
    return series


def one_response_series(name: str) -> list[dict[str, object]]:
    return [
        item for item in response_series(active=name)
        if item["id"] in {"target", "hill", name}
    ]


def sample_near(samples: list[dict[str, float]], time: float) -> dict[str, float]:
    return min(samples, key=lambda sample: abs(sample["time"] - time))


def _node(
    node_id: str,
    label: str,
    position: tuple[float, float],
    color: str,
    *,
    width: float = 1.8,
    height: float = 0.9,
    font_size: int = 19,
    shape: str = "rounded",
) -> dict[str, object]:
    return {
        "id": node_id,
        "label": label,
        "position": list(position),
        "shape": shape,
        "width": width,
        "height": height,
        "color": color,
        "fill_color": color,
        "fill_opacity": 0.24,
        "font_size": font_size,
    }


def control_loop_diagram() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    nodes = [
        _node("setpoint", "TARGET\n25 m/s", (-5.2, 0.9), TARGET),
        _node("compare", "COMPARE\nr − y", (-3.1, 0.9), ERROR, width=1.55),
        _node("controller", "PI CONTROL\nP + I action", (-0.8, 0.9), COMMAND, width=2.35),
        _node("actuator", "THROTTLE\nACTUATOR", (1.8, 0.9), COMMAND, width=2.0),
        _node("car", "CAR\nspeed y", (4.2, 0.9), MEASURED, width=1.8),
        _node("sensor", "SENSOR\nmeasured y", (2.6, -1.35), MEASURED, width=2.1),
        _node("hill", "HILL LOAD", (4.2, 2.55), DISTURBANCE, width=1.9),
    ]
    edges = [
        {"id": "reference", "from": "setpoint", "to": "compare", "directed": True, "buff": 0.35, "color": TARGET, "stroke_width": 5, "label": "r"},
        {"id": "error", "from": "compare", "to": "controller", "directed": True, "buff": 0.35, "color": ERROR, "stroke_width": 5, "label": "e"},
        {"id": "command", "from": "controller", "to": "actuator", "directed": True, "buff": 0.35, "color": COMMAND, "stroke_width": 5, "label": "u"},
        {"id": "drive", "from": "actuator", "to": "car", "directed": True, "buff": 0.35, "color": COMMAND, "stroke_width": 5},
        {"id": "output", "from": "car", "to": "sensor", "directed": True, "buff": 0.35, "color": MEASURED, "stroke_width": 5, "label": "y"},
        {"id": "feedback", "from": "sensor", "to": "compare", "directed": True, "buff": 0.35, "color": MEASURED, "stroke_width": 5, "label": "feedback"},
        {"id": "disturbance", "from": "hill", "to": "car", "directed": True, "buff": 0.35, "color": DISTURBANCE, "stroke_width": 6, "label": "load"},
    ]
    return nodes, edges


def physical_hill_diagram() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    nodes = [
        _node("target", "TARGET\n25 m/s", (-4.5, 1.5), TARGET, width=2.0),
        _node("car", "CAR\nspeed ↓", (0.0, 0.0), MEASURED, width=2.4, height=1.2),
        _node("hill", "UPHILL\nextra load", (4.4, 1.5), DISTURBANCE, width=2.2),
        _node("throttle", "FIXED\nCOMMAND", (-3.2, -1.6), MUTED, width=2.3),
    ]
    edges = [
        {"id": "target", "from": "target", "to": "car", "directed": True, "buff": 0.45, "color": TARGET, "stroke_width": 5},
        {"id": "load", "from": "hill", "to": "car", "directed": True, "buff": 0.45, "color": DISTURBANCE, "stroke_width": 6},
        {"id": "command", "from": "throttle", "to": "car", "directed": True, "buff": 0.45, "color": MUTED, "stroke_width": 4},
    ]
    return nodes, edges


def correction_cards(
    sample: dict[str, float],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Four fixed-width values for one inspectable correction instant."""

    nodes = [
        _node("target", "TARGET\n25.00 m/s", (-4.5, 0.0), TARGET, width=2.35),
        _node(
            "measured",
            f"MEASURED\n{sample['speed']:.2f} m/s",
            (-1.5, 0.0),
            MEASURED,
            width=2.35,
        ),
        _node(
            "error",
            f"ERROR\n{sample['error']:.2f} m/s",
            (1.5, 0.0),
            ERROR,
            width=2.35,
        ),
        _node(
            "command",
            f"COMMAND\n{sample['command']:.2f}",
            (4.5, 0.0),
            COMMAND,
            width=2.35,
        ),
    ]
    return nodes, []
