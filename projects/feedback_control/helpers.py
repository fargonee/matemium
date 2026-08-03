"""Deterministic cruise-control model and visuals for the engineering flagship.

This is a teaching model, not a production vehicle controller.  Vehicle speed
is coupled to a first-order actuator.  A PI controller rejects a constant hill
load; actuator lag makes aggressive tuning visibly underdamped.
"""

from __future__ import annotations

import math

import numpy as np
from manim import (
    PI,
    RIGHT,
    Arrow3D,
    Circle,
    Cylinder,
    Line3D,
    Polygon,
    Prism,
    RoundedRectangle,
    Sphere,
    Text,
    VGroup,
    VMobject,
)

from canvas import register_object_kind

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
        # Edges are drawn behind nodes.  A strong panel fill keeps connector
        # strokes and arrowheads from showing through the node labels.
        "fill_opacity": 1.0,
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
        _node("hill", "HILL LOAD", (4.2, 2.15), DISTURBANCE, width=1.9),
    ]
    edges = [
        {"id": "reference", "from": "setpoint", "to": "compare", "directed": True, "buff": 0.35, "color": TARGET, "stroke_width": 5},
        {"id": "error", "from": "compare", "to": "controller", "directed": True, "buff": 0.35, "color": ERROR, "stroke_width": 5},
        {"id": "command", "from": "controller", "to": "actuator", "directed": True, "buff": 0.35, "color": COMMAND, "stroke_width": 5},
        {"id": "drive", "from": "actuator", "to": "car", "directed": True, "buff": 0.35, "color": COMMAND, "stroke_width": 5},
        {"id": "output", "from": "car", "to": "sensor", "directed": True, "buff": 0.35, "color": MEASURED, "stroke_width": 5},
        {"id": "feedback", "from": "sensor", "to": "compare", "directed": True, "buff": 0.35, "color": MEASURED, "stroke_width": 5},
        {"id": "disturbance", "from": "hill", "to": "car", "directed": True, "buff": 0.35, "color": DISTURBANCE, "stroke_width": 6},
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


# ---------------------------------------------------------------------------
# Project-local physical world
# ---------------------------------------------------------------------------


def vehicle_world_state(
    time: float,
    *,
    tuning: str = "balanced",
    feedback: bool = True,
    stage: str = "overview",
) -> dict[str, object]:
    """Serializable snapshot of the disclosed deterministic teaching model."""

    value = float(time)
    if not 0.0 <= value <= DURATION:
        raise ValueError(f"time must be between 0 and {DURATION}")
    if tuning not in TUNINGS:
        raise ValueError(f"unknown tuning: {tuning}")
    if stage not in {"overview", "disturbance", "measurement", "correction", "recovery"}:
        raise ValueError(f"unknown world stage: {stage}")
    return {
        "time": value,
        "tuning": tuning,
        "feedback": bool(feedback),
        "stage": stage,
    }


def world_sample(content: dict[str, object]) -> dict[str, float]:
    tuning = TUNINGS[str(content.get("tuning", "balanced"))]
    feedback = bool(content.get("feedback", True))
    samples = simulate(float(tuning["kp"]), float(tuning["ki"]), feedback=feedback)
    return sample_near(samples, float(content.get("time", 0.0)))


def _road_height(x: float) -> float:
    # The hill begins at the vehicle position corresponding to HILL_START and
    # eases into a plateau so the road remains cinematic rather than a ramp.
    start, end = -2.8, 1.25
    if x <= start:
        return -0.8
    if x >= end:
        return 0.75
    u = (x - start) / (end - start)
    smooth = u * u * (3.0 - 2.0 * u)
    return -0.8 + 1.55 * smooth


def _road_slope(x: float) -> float:
    epsilon = 0.015
    return math.atan2(_road_height(x + epsilon) - _road_height(x - epsilon), 2.0 * epsilon)


def _road_path(lateral: float, *, color: str = WHITE, width: float = 2.0) -> VMobject:
    points = np.array(
        [[x, lateral, _road_height(x) + 0.025] for x in np.linspace(-5.2, 5.2, 88)],
        dtype=float,
    )
    path = VMobject(color=color, stroke_width=width)
    path.set_points_smoothly(points).set_stroke(opacity=0.98)
    return path


def _road_surface() -> tuple[VGroup, VGroup, VGroup]:
    asphalt = VGroup()
    shoulders = VGroup()
    samples = np.linspace(-5.3, 5.3, 42)
    for x0, x1 in zip(samples[:-1], samples[1:]):
        z0, z1 = _road_height(float(x0)), _road_height(float(x1))
        asphalt.add(
            Polygon(
                [x0, -1.28, z0], [x1, -1.28, z1],
                [x1, 1.28, z1], [x0, 1.28, z0],
                color="#263848",
                fill_color="#1a2732",
                fill_opacity=1.0,
                stroke_width=0.25,
            )
        )
        for inner, outer in ((-1.28, -3.0), (1.28, 3.0)):
            shoulders.add(
                Polygon(
                    [x0, inner, z0 - 0.025], [x1, inner, z1 - 0.025],
                    [x1, outer, z1 - 0.12], [x0, outer, z0 - 0.12],
                    color="#17392f",
                    fill_color="#102b25",
                    fill_opacity=1.0,
                    stroke_width=0.15,
                )
            )

    markings = VGroup(
        _road_path(-1.13, color="#d9e2e8", width=2.2),
        _road_path(1.13, color="#d9e2e8", width=2.2),
    )
    for x in np.arange(-5.0, 5.0, 1.2):
        x1 = min(float(x + 0.58), 5.2)
        markings.add(
            Line3D(
                [x, 0.0, _road_height(float(x)) + 0.035],
                [x1, 0.0, _road_height(x1) + 0.035],
                thickness=0.018,
                color=TARGET,
                resolution=6,
            ).set_opacity(0.82)
        )
    # Cairo's 3D renderer uses painter-style ordering rather than a robust
    # per-pixel depth buffer.  Keep the physical ground layers explicitly
    # behind the vehicle and its camera-facing teaching details.
    shoulders.set_z_index(-30)
    asphalt.set_z_index(-20)
    markings.set_z_index(-10)
    return asphalt, shoulders, markings


def _car_model(position: np.ndarray, slope: float, color: str, *, wheel_phase: float) -> tuple[VGroup, VGroup]:
    lower = Prism(dimensions=[1.72, 0.88, 0.32])
    lower.set_fill(color, opacity=0.96).set_stroke(WHITE, width=0.45, opacity=0.42)
    lower.set_z_index(10)
    hood = Prism(dimensions=[0.64, 0.84, 0.20])
    hood.set_fill(color, opacity=0.98).set_stroke(WHITE, width=0.35, opacity=0.35)
    hood.shift(np.array([0.56, 0.0, 0.23]))
    hood.set_z_index(11)
    cabin = Prism(dimensions=[0.78, 0.76, 0.42])
    cabin.set_fill("#17394c", opacity=0.98).set_stroke("#8fc9e8", width=0.55, opacity=0.9)
    cabin.shift(np.array([-0.12, 0.0, 0.48]))
    cabin.set_z_index(12)
    near_body_skin = Polygon(
        [-0.86, -0.456, -0.15],
        [0.90, -0.456, -0.15],
        [0.90, -0.456, 0.18],
        [0.32, -0.456, 0.25],
        [-0.34, -0.456, 0.19],
        [-0.86, -0.456, 0.12],
        color=WHITE,
        fill_color=color,
        fill_opacity=1.0,
        stroke_width=0.55,
    )
    near_body_skin.set_z_index(20)
    side_windows = VGroup()
    for side in (-1.0, 1.0):
        # Window glass sits clearly outside the 0.38 cabin half-width instead
        # of sharing its plane.  Only the approved negative-y roadside face is
        # promoted above the shell; the far face remains true occluded detail.
        window_y = side * 0.412
        seam_y = side * 0.452
        front_window = Polygon(
            [-0.04, window_y, 0.37], [0.24, window_y, 0.37],
            [0.18, window_y, 0.64], [-0.01, window_y, 0.64],
            color="#c7edff", fill_color="#73b7dd", fill_opacity=1.0, stroke_width=0.55,
        )
        rear_window = Polygon(
            [-0.34, window_y, 0.37], [-0.08, window_y, 0.37],
            [-0.05, window_y, 0.64], [-0.25, window_y, 0.64],
            color="#c7edff", fill_color="#73b7dd", fill_opacity=1.0, stroke_width=0.55,
        )
        door_seam = Line3D(
            [-0.08, seam_y, -0.02], [-0.08, seam_y, 0.35],
            thickness=0.008, color="#d8f3ef", resolution=5,
        ).set_opacity(0.7)
        detail_layer = 24 if side < 0 else 13
        front_window.set_z_index(detail_layer)
        rear_window.set_z_index(detail_layer)
        door_seam.set_z_index(detail_layer)
        side_windows.add(front_window, rear_window, door_seam)
    wheels = VGroup()
    wheel_z = -0.34
    for x in (-0.56, 0.56):
        for y in (-0.56, 0.56):
            wheel = Cylinder(
                radius=0.28,
                height=0.18,
                direction=np.array([0.0, 1.0, 0.0]),
                resolution=(14, 8),
            )
            wheel.set_fill("#202a34", opacity=1.0).set_stroke("#f0f5f8", width=1.35)
            wheel.move_to(np.array([x, y, wheel_z]))
            wheel.set_z_index(6)
            hub = Cylinder(
                radius=0.095,
                height=0.155,
                direction=np.array([0.0, 1.0, 0.0]),
                resolution=(12, 6),
            ).set_fill("#dce5eb", opacity=1.0).set_stroke(MEASURED, width=0.45)
            hub.move_to(np.array([x, y, wheel_z]))
            hub.set_z_index(7)
            visible_faces = VGroup()
            if y < 0:
                face_y = y - 0.105
                sidewall = Circle(
                    radius=0.235,
                    color="#f0f5f8",
                    fill_color="#202a34",
                    fill_opacity=1.0,
                    stroke_width=1.6,
                )
                sidewall.rotate(PI / 2, axis=RIGHT).move_to([x, face_y, wheel_z])
                sidewall.set_z_index(30)
                hub_face = Circle(
                    radius=0.082,
                    color=MEASURED,
                    fill_color="#dce5eb",
                    fill_opacity=1.0,
                    stroke_width=1.0,
                )
                hub_face.rotate(PI / 2, axis=RIGHT).move_to([x, face_y - 0.004, wheel_z])
                hub_face.set_z_index(31)
                visible_faces.add(sidewall, hub_face)
            spoke = Line3D(
                [x - 0.19 * math.cos(wheel_phase), y, wheel_z - 0.19 * math.sin(wheel_phase)],
                [x + 0.19 * math.cos(wheel_phase), y, wheel_z + 0.19 * math.sin(wheel_phase)],
                thickness=0.012,
                color=WHITE,
                resolution=5,
            )
            if y < 0:
                spoke.set_z_index(32)
            wheels.add(wheel, hub, visible_faces, spoke)

    lights = VGroup()
    headlight = Sphere(radius=0.085, resolution=(8, 6))
    headlight.set_fill(TARGET, opacity=1.0).set_stroke(TARGET, width=0.2)
    headlight.move_to([0.975, -0.31, 0.08]).set_z_index(28)
    tail = Sphere(radius=0.065, resolution=(8, 6))
    tail.set_fill(ERROR, opacity=0.95).set_stroke(ERROR, width=0.2)
    tail.move_to([-0.965, -0.31, 0.06]).set_z_index(28)
    lights.add(headlight, tail)

    bumper = Prism(dimensions=[0.08, 0.92, 0.10])
    bumper.set_fill("#b7c4ce", opacity=0.9).set_stroke(WHITE, width=0.25)
    bumper.shift([0.955, 0.0, -0.02])
    bumper.set_z_index(14)
    # Far/volumetric wheel geometry is intentionally behind the opaque shell;
    # camera-facing sidewalls, glass, lights, and seams carry higher layers.
    car = VGroup(
        wheels,
        lower,
        hood,
        cabin,
        bumper,
        near_body_skin,
        side_windows,
        lights,
    )
    car.rotate(-slope, axis=np.array([0.0, 1.0, 0.0]), about_point=np.zeros(3))
    car.move_to(position)
    return car, wheels


def _standing_label(text: str, color: str, position: np.ndarray, *, width: float = 2.25) -> VGroup:
    panel = RoundedRectangle(
        width=width,
        height=0.52,
        corner_radius=0.11,
        color=color,
        fill_color=BG,
        fill_opacity=1.0,
        stroke_width=1.5,
    )
    label = Text(text, color=color, font_size=18, weight="BOLD")
    label.scale_to_fit_width(width - 0.24)
    group = VGroup(panel, label)
    group.rotate(PI / 2, axis=RIGHT)
    # Keep glyphs slightly camera-side of the backing panel to prevent
    # perspective depth flicker in the approved negative-y roadside shots.
    label.shift(np.array([0.0, -0.012, 0.0]))
    panel.set_z_index(60)
    label.set_z_index(61)
    group.move_to(position)
    return group


def _attached_label(
    text: str,
    color: str,
    position: np.ndarray,
    anchor: np.ndarray,
    *,
    width: float,
) -> VGroup:
    leader = Line3D(anchor, position, thickness=0.012, color=color, resolution=5)
    leader.set_opacity(0.72)
    leader.set_z_index(55)
    return VGroup(leader, _standing_label(text, color, position, width=width))


def _roadside_target_sign() -> VGroup:
    x = -4.15
    road_z = _road_height(x)
    pole = Line3D(
        [x, 1.62, road_z], [x, 1.62, road_z + 1.05],
        thickness=0.025,
        color=MUTED,
        resolution=6,
    )
    board = _standing_label("TARGET  25 m/s", TARGET, np.array([x, 1.61, road_z + 1.08]), width=1.8)
    return VGroup(pole, board)


def _build_feedback_world(elem, wrap, target_width, surface_factory):
    content = dict(elem.content or {})
    sample = world_sample(content)
    time = float(content.get("time", 0.0))
    feedback = bool(content.get("feedback", True))
    stage = str(content.get("stage", "overview"))

    car_x = -4.0 + 0.4 * time
    # Keep the tyre contact patch on the road even while the body rotates with
    # the slope.  The earlier 0.40 offset buried most of the chassis in the hill.
    car_z = _road_height(car_x) + 0.92
    car_pos = np.array([car_x, 0.0, car_z])
    slope = _road_slope(car_x)

    road, terrain, markings = _road_surface()
    sign = _roadside_target_sign()
    car, wheels = _car_model(
        car_pos,
        slope,
        COMMAND if feedback else "#9a6cff",
        wheel_phase=time * 1.7,
    )
    speed_scale = max(0.35, sample["speed"] / TARGET_SPEED)
    direction = np.array([math.cos(slope), 0.0, math.sin(slope)])
    speed_vector = Arrow3D(
        start=car_pos + np.array([0.0, -0.58, 0.62]),
        end=car_pos + np.array([0.0, -0.58, 0.62]) + direction * (1.55 * speed_scale),
        color=MEASURED,
        thickness=0.032,
        height=0.19,
        base_radius=0.06,
        resolution=8,
    )
    speed_vector.set_z_index(45)
    speed_label_pos = car_pos + np.array([1.35, -0.62, 1.14])
    speed_label = _attached_label(
        f"MEASURED  {sample['speed']:.1f} m/s",
        MEASURED,
        speed_label_pos,
        car_pos + np.array([0.78, -0.58, 0.72]),
        width=2.15,
    )
    control_vector = Arrow3D(
        start=car_pos + np.array([-1.12, -0.62, 0.30]),
        end=car_pos + np.array([-1.12, -0.62, 0.30]) + direction * (0.75 + 0.045 * sample["command"]),
        color=COMMAND if feedback else MUTED,
        thickness=0.03,
        height=0.18,
        base_radius=0.055,
        resolution=8,
    )
    control_vector.set_z_index(45)
    command_color = COMMAND if feedback else MUTED
    command_text = "THROTTLE CORRECTS" if feedback else "FIXED THROTTLE"
    command_label_pos = car_pos + np.array([-1.15, -0.62, 1.04])
    command_label = _attached_label(
        command_text,
        command_color,
        command_label_pos,
        car_pos + np.array([-0.52, -0.58, 0.45]),
        width=1.85,
    )
    hill_x = -1.25
    hill_z = _road_height(hill_x)
    downhill = np.array([-math.cos(_road_slope(hill_x)), 0.0, -math.sin(_road_slope(hill_x))])
    hill_marker = Arrow3D(
        start=np.array([hill_x, -0.72, hill_z + 0.62]),
        end=np.array([hill_x, -0.72, hill_z + 0.62]) + downhill * 1.35,
        color=DISTURBANCE,
        thickness=0.035,
        height=0.20,
        base_radius=0.065,
        resolution=8,
    )
    hill_marker.set_z_index(45)
    hill_label_pos = np.array([hill_x + 0.70, -0.74, hill_z + 1.30])
    hill_label = _attached_label(
        "UPHILL LOAD",
        DISTURBANCE,
        hill_label_pos,
        np.array([hill_x, -0.72, hill_z + 0.62]),
        width=1.6,
    )
    if time < HILL_START:
        hill_marker.set_opacity(0.18)
        hill_label.set_opacity(0.18)

    sensor_center = car_pos + np.array([0.12, -0.48, 0.72])
    sensor = Sphere(radius=0.105, resolution=(10, 7))
    sensor.set_fill(MEASURED, opacity=1.0).set_stroke(WHITE, width=0.45)
    sensor.move_to(sensor_center)
    sensor.set_z_index(46)
    sensor_pulse = VGroup()
    for radius, opacity in ((0.18, 0.5), (0.29, 0.25)):
        ring = Circle(radius=radius, color=MEASURED, stroke_width=2.0)
        ring.rotate(PI / 2, axis=RIGHT).move_to(sensor_center)
        ring.set_opacity(opacity)
        ring.set_z_index(47)
        sensor_pulse.add(ring)
    sensor_label_pos = car_pos + np.array([-1.02, -0.62, 1.50])
    sensor_label = _attached_label(
        "SPEED SENSOR",
        MEASURED,
        sensor_label_pos,
        sensor_center,
        width=1.55,
    )

    # Each authored stage reveals only the causal marks needed for that shot.
    show_target = stage in {"overview", "disturbance"}
    show_hill = stage == "disturbance"
    show_speed = stage in {"measurement", "correction", "recovery"}
    show_control = stage in {"correction", "recovery"}
    show_sensor = stage == "measurement"
    if not show_target:
        sign.set_opacity(0.0)
    if not show_hill:
        hill_marker.set_opacity(0.0)
        hill_label.set_opacity(0.0)
    if not show_speed:
        speed_vector.set_opacity(0.0)
        speed_label.set_opacity(0.0)
    if not show_control:
        control_vector.set_opacity(0.0)
        command_label.set_opacity(0.0)
    if not show_sensor:
        sensor.set_opacity(0.0)
        sensor_pulse.set_opacity(0.0)
        sensor_label.set_opacity(0.0)

    labels = VGroup(sign, hill_label, speed_label, command_label, sensor_label)
    world = VGroup(terrain, road, markings, hill_marker, speed_vector, control_vector, car, sensor, sensor_pulse, labels)
    world.matemium_parts = {
        "terrain": terrain,
        "road": road,
        "markings": markings,
        "target_sign": sign,
        "hill_load": hill_marker,
        "speed": speed_vector,
        "control": control_vector,
        "car": car,
        "wheels": wheels,
        "sensor": sensor,
        "sensor_pulse": sensor_pulse,
        "labels": labels,
    }
    return world


def _validate_feedback_world(content: object) -> list[str]:
    if not isinstance(content, dict):
        return ["content must be a mapping"]
    try:
        time = float(content.get("time", -1.0))
    except (TypeError, ValueError):
        return ["time must be numeric"]
    if not 0.0 <= time <= DURATION:
        return [f"time must be between 0 and {DURATION}"]
    if str(content.get("tuning", "")) not in TUNINGS:
        return [f"tuning must be one of {sorted(TUNINGS)}"]
    if str(content.get("stage", "overview")) not in {
        "overview", "disturbance", "measurement", "correction", "recovery"
    }:
        return ["stage must be overview, disturbance, measurement, correction, or recovery"]
    return []


def _feedback_world_parts(content: object) -> set[str]:
    return {
        "terrain", "road", "markings", "target_sign", "hill_load", "speed",
        "control", "car", "wheels", "sensor", "sensor_pulse", "labels",
    }


register_object_kind(
    "FeedbackVehicleWorld",
    build=_build_feedback_world,
    validate=_validate_feedback_world,
    parts=_feedback_world_parts,
)
