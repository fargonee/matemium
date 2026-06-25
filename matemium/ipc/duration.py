"""Timeline duration estimates for desktop preview UX."""

from __future__ import annotations

from canvas.dsl import (
    CameraFocus,
    CameraInspect,
    CameraMove,
    CanvasElement,
    PlotTrace,
    SheetDSL,
    SolidLift,
    SolidRotate,
    TransformElement,
)


def _element_entry_time(elem: CanvasElement) -> float:
    if elem.entry_animation is not None:
        return float(elem.entry_animation.run_time)
    return 1.0


def estimate_timeline_duration(dsl: SheetDSL) -> float:
    """Sum known run_time fields — conservative lower bound for preview."""
    total = 0.0
    for item in dsl.timeline:
        if isinstance(item, CanvasElement):
            total += _element_entry_time(item)
            if item.auto_focus:
                total += 0.8
        elif isinstance(item, CameraMove):
            total += float(item.run_time)
        elif isinstance(item, TransformElement):
            total += float(item.run_time)
        elif isinstance(item, PlotTrace):
            total += float(item.run_time)
        elif isinstance(item, SolidLift):
            total += float(item.run_time)
        elif isinstance(item, SolidRotate):
            total += float(item.run_time) + float(item.hold)
        elif isinstance(item, CameraInspect):
            total += float(item.run_time) + float(item.hold_time)
            if item.orbit:
                total += float(item.orbit_run_time)
            if item.return_to_sheet:
                total += float(item.return_run_time)
        elif isinstance(item, CameraFocus):
            total += float(item.run_time) + float(item.hold_time)
            if item.reset_zoom:
                total += float(item.reset_run_time)
    return round(total, 3)


def estimate_animation_count(dsl: SheetDSL) -> int:
    """Conservative ``play()`` count for Manim partial-movie progress."""
    count = 2  # intro pause + tail padding
    for item in dsl.timeline:
        if isinstance(
            item,
            (
                CanvasElement,
                CameraMove,
                TransformElement,
                PlotTrace,
                SolidLift,
                SolidRotate,
            ),
        ):
            count += 1
        elif isinstance(item, CameraInspect):
            count += 2 if item.orbit else 1
            if item.return_to_sheet:
                count += 1
        elif isinstance(item, CameraFocus):
            count += 2 if item.reset_zoom else 1
    return max(count, 1)