"""Matemium — layout-to-animation compiler for infinite scrollable math sheets.

Elements appear as the view scrolls, stay at fixed positions in default state,
and can be re-animated on demand. Full-tape export captures the entire sheet
in its natural aspect (no forced portrait/landscape crop).

**Video formats (portrait-first)**:
- `CanvasSettings.for_reels()`      → 9:16 vertical (default)
- `CanvasSettings.for_youtube()`    → 16:9 landscape

Render videos: `./matemium.sh demo` or `python -m matemium --help`

See project-spec.md, architecture.md, and canvas/USAGE.md.
"""

from .dsl import (
    SheetDSL,
    CanvasSettings,
    CanvasElement,
    LayoutBox,
    CameraMove,
    CameraKeyframe,  # Phase 3 generalized observation
    WorldPoint,
    ObjectAnchor,
    TapeScroll,
    ObservationTarget,
    ObservationMode,  # Phase 8
    TransformElement,
    EntryAnimation,
    StateBehavior,
    # Phase 1
    WorldObject,
    # Phase 2
    TapeObject,
)
# Phase 1+: world coordinate primitives (exported for authors and tests)
from .coords import Vector3, WorldTransform, resolve_world_position
from .layout import LayoutEngine, Style
from .measure import (
    build_mobject,
    measure_element,
    set_measurement_backend,
    get_measurement_backend,
    register_element_builder,
    register_object_kind,  # Phase 9
)
from .measurement import MeasuredSize, MeasurementBackend, BoundingBox3D
from .measurement.manim_backend import ManimMeasurementBackend
from .scene import CanvasScene
from .builder import CanvasBuilder

# High-level builder (recommended for most use, especially AI-generated videos):
# See canvas/USAGE.md for plain examples and guidelines.
#
# builder = CanvasBuilder(title="My Video")
# builder.add_text("...")
# builder.add_math(r"...")
# builder.add_3d("z=x^2-y^2")
# dsl = builder.build()
# scene = CanvasScene(dsl)
#
# Full static sheet export (PNG/PDF) is available via scene.export_full_sheet(...)
# (see project-spec.md for full_tape mode etc.)
from .registry import MobjectRegistry, RegistryEntry
from .camera import CameraController
from .animations import get_entry_animation, FLASH_AND_SCALE
from .cutter import ReelCutter

__all__ = [
    "SheetDSL",
    "CanvasSettings",
    "CanvasElement",
    "LayoutBox",
    "LayoutEngine",
    "Style",
    "build_mobject",
    "measure_element",
    "set_measurement_backend",
    "get_measurement_backend",
    "register_element_builder",
    "register_object_kind",  # Phase 9 / canonical
    "MeasuredSize",
    "MeasurementBackend",
    "ManimMeasurementBackend",
    "BoundingBox3D",
    "CameraMove",
    "CameraKeyframe",
    "TransformElement",
    "EntryAnimation",
    "StateBehavior",
    "CanvasScene",
    "MobjectRegistry",
    "RegistryEntry",
    "CameraController",
    "get_entry_animation",
    "FLASH_AND_SCALE",
    "ReelCutter",
    "CanvasBuilder",
    # 3D world model (Phase 1-10 canonical)
    "Vector3",
    "WorldTransform",
    "WorldObject",
    "TapeObject",
    "WorldPoint",
    "ObjectAnchor",
    "TapeScroll",
    "ObservationTarget",
    "ObservationMode",  # Phase 8
    "resolve_world_position",
]
