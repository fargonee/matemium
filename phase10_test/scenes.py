"""Phase 10 comprehensive test scenes.py

Copy this into a project as scenes.py (with a matching assets.py).

Exercises:
- Default root_tape + posed/rotated TapeObject in 3D space
- World objects placed with absolute + relative transforms
- builder.add_object (registered kinds)
- builder.add_world_object
- builder.add_relative + anchors
- Custom object kind registration
- All ObservationTarget types: WorldPoint, ObjectAnchor, TapeScroll
- Mixed content (sheet inside tape + free 3D)
- Legacy compat still works
"""

from __future__ import annotations

from canvas import (
    CanvasScene,
    CanvasSettings,
    CanvasBuilder,
    register_object_kind,
    CanvasElement,
    WorldObject,
    WorldTransform,
    Vector3,
    ObjectAnchor,
    TapeScroll,
    WorldPoint,
)

# Safe import for assets (works whether run as package or flat project)
try:
    from . import assets as test_assets
except ImportError:
    import assets as test_assets


# ------------------------------------------------------------------
# Custom registered kind (tests extensibility via register_object_kind)
# ------------------------------------------------------------------
def build_marker(elem: CanvasElement, wrap: bool, target_width, surface_factory):
    """A simple custom 3D marker with a label."""
    from manim import Dot, Text, VGroup, WHITE, UP

    data = elem.content or {}
    label = str(data.get("label", "P"))
    color = data.get("color", "#ffaa00")

    dot = Dot(radius=0.18, color=color)
    txt = Text(label, font_size=20, color=WHITE)
    txt.next_to(dot, UP, buff=0.12)
    grp = VGroup(dot, txt)

    if target_width:
        grp.set_width(float(target_width))
    return grp


register_object_kind(
    "Marker",
    build=build_marker,
    # measure / observe / preview can be added later if needed
)


# ------------------------------------------------------------------
# Main Phase 10 test scene
# ------------------------------------------------------------------
class Phase10Comprehensive(CanvasScene):
    """Comprehensive test of the unified infinite 3D space model (Phase 10).

    Features demonstrated:
    - Tape posed in 3D (rotated)
    - Traditional tape content (headings, math, flex, 3D graphs inside the tape)
    - Free world objects (Solids, Axes, custom Marker)
    - Absolute + relative placement (add_object + add_relative)
    - All camera target types (ObjectAnchor, TapeScroll, WorldPoint)
    - Custom registered object kind
    - Mixed 2D-in-3D + pure 3D content
    """

    def __init__(self, **kwargs):
        builder = CanvasBuilder(
            title="Phase 10 — 3D World Test",
            canvas_settings=CanvasSettings.for_reels(title="Phase 10 3D Test"),
        )

        # === 1. Content inside the (soon to be rotated) root tape ===
        builder.add_heading("Phase 10: Unified 3D Space", style={"align": "center", "margin-bottom": 0.6})
        builder.add_body(
            "The old infinite tape is now a TapeObject that can live anywhere in 3D space.",
            style={"margin-bottom": 0.8},
        )
        builder.add_math(r"\vec{r} = (x, y, z)", style={"margin-bottom": 0.6})

        # Pose the tape in 3D (XZ ground, Y up)
        positions = test_assets.get_test_positions()
        builder.set_tape_pose(
            position=(0.0, 0.0, 0.0),
            rotation=(22, -18, 5),   # pitch, yaw, roll (degrees)
            scale=1.0,
        )

        builder.add_body(
            "Everything below lives in the tape's local 2D plane, even though the plane itself is tilted in world space.",
            style={"margin-top": 0.3, "margin-bottom": 0.8},
        )

        # Flex + math inside the rotated tape
        builder.add_flex_row(
            [
                builder.text_spec("Flex still works →", style={"align": "right"}),
                builder.math_spec(r"\sin^2\theta + \cos^2\theta = 1", style={"width": 4.2}),
            ],
            gap=0.6,
            style={"margin-bottom": 1.0},
        )

        builder.add_3d(
            r"z = \sin(x) \cos(y)",
            pitch=38,
            style={"width": 5.5, "align": "center"},
        )

        builder.add_body(
            "Tape content uses the normal lazy-reveal + styling system.",
            style={"margin-top": 0.5},
        )

        # === 2. Free world objects (outside any tape) ===
        # Primary cube
        builder.add_object(
            "Solid3D",
            id="main_cube",
            position=(4.2, 1.2, 2.8),
            rotation=(10, 35, 0),
            content={
                "shape": "cube",
                "size": 1.1,
                "color": "#5eb3ff",
                "opacity": 0.85,
            },
        )

        # Sphere placed relative to the cube (using high-level API)
        builder.add_object(
            "Solid3D",
            id="hover_sphere",
            position=(0.0, 2.1, 0.0),
            relative_to="main_cube",
            anchor="top",
            content={"shape": "sphere", "size": 0.65, "color": "#ffcc66"},
        )

        # Label attached with add_relative (classic relative helper)
        label_el = CanvasElement(
            id="cube_label",
            type="Text",
            content="Floating cube + relative label",
        )
        builder.add_relative(
            "main_cube",
            label_el,
            local_offset=(0.0, 2.6, 0.0),
            anchor="top",
        )

        # Custom registered Marker
        builder.add_object(
            "Marker",
            id="special_point",
            position=(-2.8, 0.6, -3.5),
            content={"label": "P1", "color": "#ffaa00"},
        )

        # Axes as a world object
        builder.add_object(
            "Axes",
            position=(-1.5, 0.3, -5.0),
            scale=0.55,
        )

        # Another marker using WorldObject directly (low-level)
        marker_wo = WorldObject(
            id="origin_marker",
            element=CanvasElement(
                id="origin_el",
                type="Marker",
                content={"label": "O", "color": "#66ff99"},
            ),
            transform=WorldTransform(position=Vector3(-0.5, 0.2, -1.8)),
        )
        builder.add_world_object(marker_wo)

        # === 3. Camera tour using all target types ===
        # Look at the floating cube
        builder.add_camera_keyframe(
            target=ObjectAnchor(object_id="main_cube", anchor="center"),
            duration=3.2,
        )

        # Scroll along the rotated tape
        builder.add_camera_keyframe(
            target=TapeScroll(tape_id="root_tape", local_y=5.5, framing_mode="sheet"),
            duration=4.5,
        )

        # Jump to a world point
        builder.add_camera_keyframe(
            target=WorldPoint(position=(1.5, 3.8, 7.0)),
            duration=2.8,
        )

        # Focus the sphere
        builder.add_camera_keyframe(
            target=ObjectAnchor(object_id="hover_sphere", anchor="center"),
            duration=2.0,
        )

        # End on the custom marker
        builder.add_camera_keyframe(
            target=ObjectAnchor(object_id="special_point", anchor="center"),
            duration=2.5,
        )

        super().__init__(dsl=builder.build(), **kwargs)


# ------------------------------------------------------------------
# Simple legacy-style scene (proves backward compatibility)
# ------------------------------------------------------------------
class LegacyCompatScene(CanvasScene):
    """Traditional sheet authoring still works unchanged."""

    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(title="Legacy Compat")
        b = CanvasBuilder(title="Legacy Compat", canvas_settings=settings)

        b.add_heading("Legacy path still works")
        b.add_math(r"\int_{-\infty}^{\infty} e^{-x^2} \, dx = \sqrt{\pi}")
        b.add_3d("z = x^2 - y^2", pitch=42)
        b.add_body(
            "Old add_heading / add_math / add_3d / flex continue to target the default tape."
        )

        super().__init__(dsl=b.build(), **kwargs)


# ------------------------------------------------------------------
# Scene that mixes posed tape + many world objects
# ------------------------------------------------------------------
class MixedWorldTour(CanvasScene):
    """Another mixed scene for deeper testing."""

    def __init__(self, **kwargs):
        b = CanvasBuilder(title="Mixed World Tour")

        b.set_tape_pose(rotation=(30, 12, 0))

        b.add_heading("Mixed 3D Tour")
        b.add_body("One rotated tape + several independently placed 3D objects.")

        # Several world objects at different locations
        b.add_object("Solid3D", id="c1", position=(5, 0, 1), content={"shape": "cube", "size": 0.9})
        b.add_object("Solid3D", id="c2", position=(-3.5, 1.5, -2), content={"shape": "sphere", "size": 1.1})
        b.add_object("Axes", position=(0, 0, -6), scale=0.5)

        # Camera that jumps between them
        b.add_camera_keyframe(target=ObjectAnchor(object_id="c1", anchor="center"), duration=2.5)
        b.add_camera_keyframe(target=ObjectAnchor(object_id="c2", anchor="center"), duration=2.5)
        b.add_camera_keyframe(target=WorldPoint(position=(0, 5, 8)), duration=3.0)
        b.add_camera_keyframe(target=TapeScroll(tape_id="root_tape", local_y=2.0), duration=3.0)

        super().__init__(dsl=b.build(), **kwargs)


# Aliases for convenience
Phase10Test = Phase10Comprehensive
Mixed3D = MixedWorldTour
