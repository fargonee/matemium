"""Sphere-in-cube geometry lesson — project helpers, not engine API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from canvas.builder import CanvasBuilder


def inscribed_solid_parts(
    cube_side: float = 2.0,
    *,
    cube_color: str = "#8ab4f8",
    sphere_color: str = "#ff8a65",
) -> list[Dict[str, Any]]:
    """Cube + inscribed sphere sharing one center anchor."""
    radius = cube_side / 2.0
    return [
        {
            "shape": "cube",
            "side": cube_side,
            "color": cube_color,
            "opacity": 0.32,
            "stroke_color": "#ffffff",
            "stroke_width": 1.5,
        },
        {
            "shape": "sphere",
            "radius": radius,
            "color": sphere_color,
            "opacity": 0.88,
        },
    ]


def add_inscribed_pair(
    builder: CanvasBuilder,
    *,
    id: str = "inscribed_pair",
    cube_side: float = 2.0,
    style: Optional[Dict[str, Any]] = None,
) -> str:
    """Place a transparent cube with an inscribed sphere — one addressable element."""
    builder.add_solid(
        shape="cube",
        size=cube_side,
        id=id,
        parts=inscribed_solid_parts(cube_side),
        style=style or {"align": "center", "margin-bottom": 0.5},
    )
    return id


def inscribed_inspect_path(builder: CanvasBuilder) -> List[Dict[str, Any]]:
    """Simple inspect tour (legacy / quick test)."""
    return inscribed_tangency_study_path(builder) + inscribed_orbit_finale_path(builder)[1:]


def inscribed_tangency_study_path(builder: CanvasBuilder) -> List[Dict[str, Any]]:
    """Act I–II: establish the pair, then hold on each tangency-facing view."""
    shot = builder.inspect_shot
    return [
        # Establish — high wide view of lifted solid
        shot(phi=82.0, theta=-28.0, zoom=0.88, run_time=2.0, hold=1.0),
        shot(phi=72.0, theta=-48.0, zoom=0.95, run_time=1.6, hold=0.6),
        # Front face tangency — long dwell
        shot(phi=64.0, theta=-52.0, zoom=1.12, run_time=1.5, hold=2.2),
        # Slide along edge toward right face (non-cardinal angle)
        shot(phi=58.0, theta=-18.0, zoom=1.08, run_time=2.1, hold=1.8),
        # Right face
        shot(phi=61.0, theta=38.0, zoom=1.14, run_time=1.7, hold=2.0),
        # Under-edge peek (low phi — see sphere kiss the bottom face)
        shot(phi=42.0, theta=72.0, zoom=1.05, run_time=2.3, hold=1.6),
        # Back-right corner ( awkward angle — path not a simple orbit )
        shot(phi=55.0, theta=128.0, zoom=1.1, run_time=2.2, hold=1.9),
        # Back face
        shot(phi=67.0, theta=178.0, zoom=1.12, run_time=1.9, hold=2.1),
        # Left face via high sweep
        shot(phi=74.0, theta=248.0, zoom=1.06, run_time=2.0, hold=1.5),
        # Top-ish tangency (look down on top face contact)
        shot(phi=38.0, theta=310.0, zoom=1.15, run_time=2.4, hold=1.8),
    ]


def inscribed_edge_corner_path(builder: CanvasBuilder) -> List[Dict[str, Any]]:
    """Act III: edge and corner drama — zoom pulses, slight target offsets."""
    shot = builder.inspect_shot
    return [
        # Zoom into front-top edge
        shot(
            phi=48.0, theta=-62.0, zoom=1.28,
            target_offset=(0.0, 0.15, 0.12),
            run_time=1.8, hold=2.0,
        ),
        # Pull back to see full corner triad
        shot(phi=62.0, theta=-95.0, zoom=0.92, run_time=2.0, hold=1.2),
        # Vertex corner — sphere tangent to three faces at once (corner view)
        shot(
            phi=52.0, theta=-135.0, zoom=1.22,
            target_offset=(0.1, -0.08, 0.0),
            run_time=2.2, hold=2.4,
        ),
        # Opposite corner (non-formulateable diagonal approach)
        shot(phi=68.0, theta=42.0, zoom=1.0, run_time=2.5, hold=0.8),
        shot(
            phi=54.0, theta=88.0, zoom=1.25,
            target_offset=(-0.12, 0.1, 0.05),
            run_time=2.0, hold=2.2,
        ),
        # Low worm's-eye — sheet plane visible under the solid
        shot(phi=28.0, theta=195.0, zoom=1.08, run_time=2.6, hold=1.7),
    ]


def inscribed_orbit_finale_path(builder: CanvasBuilder) -> List[Dict[str, Any]]:
    """Act IV: accelerating sweep + hero hold, then settle for return to sheet."""
    shot = builder.inspect_shot
    return [
        shot(phi=70.0, theta=260.0, zoom=1.0, run_time=1.4, hold=0.4),
        # S-curve in theta with phi wobble — not a single orbit formula
        shot(phi=63.0, theta=310.0, zoom=0.98, run_time=1.6, hold=0.3),
        shot(phi=58.0, theta=350.0, zoom=0.96, run_time=1.5, hold=0.3),
        shot(phi=54.0, theta=20.0, zoom=0.94, run_time=1.4, hold=0.3),
        shot(phi=50.0, theta=55.0, zoom=0.95, run_time=1.3, hold=0.3),
        shot(phi=56.0, theta=95.0, zoom=0.97, run_time=1.3, hold=0.3),
        shot(phi=62.0, theta=140.0, zoom=1.0, run_time=1.2, hold=0.3),
        shot(phi=66.0, theta=185.0, zoom=1.02, run_time=1.2, hold=0.3),
        shot(phi=64.0, theta=230.0, zoom=1.04, run_time=1.2, hold=0.3),
        shot(phi=60.0, theta=275.0, zoom=1.05, run_time=1.2, hold=0.3),
        shot(phi=58.0, theta=320.0, zoom=1.06, run_time=1.2, hold=0.3),
        shot(phi=62.0, theta=365.0, zoom=1.08, run_time=1.2, hold=0.3),
        # Hero — inscribed silhouette, longest hold of the finale
        shot(phi=66.0, theta=400.0, zoom=1.18, run_time=1.8, hold=2.5),
        # Pull out for graceful return transition
        shot(phi=78.0, theta=415.0, zoom=0.9, run_time=1.6, hold=0.6),
    ]


def inscribed_full_inspect_tour(builder: CanvasBuilder) -> List[Dict[str, Any]]:
    """Complete multi-act inspect — tangency, corners, sweep finale."""
    return (
        inscribed_tangency_study_path(builder)
        + inscribed_edge_corner_path(builder)
        + inscribed_orbit_finale_path(builder)
    )


def inscribed_point_labels(builder: CanvasBuilder, half: float = 1.2) -> List[Dict[str, Any]]:
    """Billboard labels at face tangency points and center (local coords)."""
    lbl = builder.solid_label
    r = half * 0.52
    return [
        lbl("center O", (0.0, 0.0, 0.0), color="#ffffff", font_size=20),
        lbl("+x face", (half + 0.08, 0.0, 0.0), color="#8ab4f8"),
        lbl("-x face", (-half - 0.08, 0.0, 0.0), color="#8ab4f8"),
        lbl("+y", (0.0, half + 0.08, 0.0), color="#81c784"),
        lbl("tangent", (r, 0.0, 0.0), color="#ff8a65", font_size=18),
        lbl("top", (0.0, 0.0, half + 0.08), color="#ffdd66"),
    ]


def add_labeled_inscribed_pair(
    builder: CanvasBuilder,
    *,
    id: str = "labeled_pair",
    cube_side: float = 2.4,
    style: Optional[Dict[str, Any]] = None,
) -> str:
    """Cube + sphere with billboard point labels."""
    half = cube_side / 2.0
    builder.add_solid(
        shape="cube",
        size=cube_side,
        id=id,
        parts=inscribed_solid_parts(cube_side),
        labels=inscribed_point_labels(builder, half=half),
        style=style or {"align": "center", "margin-bottom": 0.45},
    )
    return id


def cube_face_rotation_path(builder: CanvasBuilder) -> List[Dict[str, Any]]:
    """Turn a cube to show four faces — local Y/X with holds at each pose."""
    shot = builder.rotate_shot
    return [
        shot(axis="y", angle=90.0, hold=1.2, run_time=1.1),
        shot(axis="y", angle=90.0, hold=1.2, run_time=1.1),
        shot(axis="x", angle=35.0, hold=1.0, run_time=1.2),
        shot(axis="y", angle=90.0, hold=0.9, run_time=1.0),
    ]


def short_billboard_inspect_path(builder: CanvasBuilder) -> List[Dict[str, Any]]:
    """Quick inspect tour — enough motion to verify labels face the camera."""
    shot = builder.inspect_shot
    return [
        shot(phi=72.0, theta=-40.0, zoom=1.0, run_time=1.4, hold=0.8),
        shot(phi=58.0, theta=15.0, zoom=1.1, run_time=1.5, hold=1.2),
        shot(phi=48.0, theta=95.0, zoom=1.12, run_time=1.6, hold=1.0),
        shot(phi=65.0, theta=185.0, zoom=1.05, run_time=1.5, hold=1.0),
        shot(phi=35.0, theta=280.0, zoom=1.15, run_time=1.6, hold=0.8),
        shot(phi=70.0, theta=350.0, zoom=1.0, run_time=1.3, hold=0.5),
    ]