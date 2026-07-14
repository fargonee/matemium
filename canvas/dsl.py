"""Clean, dependency-free Sheet DSL for Matemium.

Supports both JSON files and programmatic Python construction.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional, Union, List, Dict

# Phase 1: world transforms (forward import to avoid cycles)
from .coords import WorldTransform, Vector3


class ObservationMode(str, Enum):
    """Explicit modes for camera observation (Phase 8 polish)."""
    NORMAL_3D = "normal_3d"      # Default: cinematic 3D for any object (incl. tapes)
    TAPE_SCROLL = "tape_scroll"  # Only this activates internal tape logic (local scroll, reveal, etc.)


@dataclass
class EntryAnimation:
    """Entry animation specification for an element."""
    type: str = "Write"          # "Write", "FadeIn", "GrowFromCenter", etc.
    run_time: float = 1.0
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateBehavior:
    """Idle / continuous behavior for elements (e.g. slow rotation)."""
    type: str                        # "rotate_slowly", "pulse", "vector_field"...
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayoutBox:
    """Resolved layout for an element (border-box sizing, post-layout).

    Stored on CanvasElement after the layout engine places the item.
    The scene reads this — not ad-hoc keys inside ``content``.
    """
    width: float
    height: float
    wrap: bool = False
    align: str = "center"  # "left" | "center" | "right"
    margin_top: float = 0.0
    margin_bottom: float = 0.0
    margin_left: float = 0.0
    margin_right: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayoutBox":
        return cls(
            width=float(data["width"]),
            height=float(data["height"]),
            wrap=bool(data.get("wrap", False)),
            align=str(data.get("align", "center")),
            margin_top=float(data.get("margin_top", data.get("margin-top", 0.0))),
            margin_bottom=float(data.get("margin_bottom", data.get("margin-bottom", 0.0))),
            margin_left=float(data.get("margin_left", data.get("margin-left", 0.0))),
            margin_right=float(data.get("margin_right", data.get("margin-right", 0.0))),
        )


@dataclass
class CanvasElement:
    """A structural element anchored at an explicit (x, y, z) canvas coordinate.

    The `type` is intentionally a plain string (not a closed Literal) to keep the
    core engine granular and abstract.

    Core primitives (handled generically by layout + scene + preview):
      Text, MathTex, VGroup, Axes, NumberPlane, ParametricFunction, Dot, Arrow,
      Image, SVG, ...

    Everything else (QuadraticPlot, Solid3D, GridBoard, lesson-specific diagrams,
    etc.) should ideally be expressed via composition (VGroups + styling) or
    registered as custom kinds so that the engine does not grow object/lesson
    specific knowledge.

    This is the main reason we have the CSS-like `style={}` + flex + LayoutEngine.
    """
    id: str
    type: str  # was a closed Literal; kept open for abstraction + extensibility
    content: Optional[Union[str, Dict[str, Any]]] = None
    # (x, y, z) — legacy for sheet/tape local position (backward compat)
    canvas_position: tuple[float, float, float] = (0.0, 0.0, 0.0)

    # Phase 1: World 3D transform for the unified space model.
    # The tape (legacy sheet) is implicitly a TapeObject at identity for now.

    # Optional: which parent object this lives under (for relative positioning later)
    parent_object_id: Optional[str] = None
    world_transform: WorldTransform = field(default_factory=WorldTransform)

    layout: Optional[LayoutBox] = None
    entry_animation: Optional[EntryAnimation] = None
    state_behavior: Optional[StateBehavior] = None
    # 3D orientation hints (degrees)
    pitch: Optional[float] = None
    yaw: Optional[float] = None

    # Static state for screenshot / full sheet export (important for 2D/3D study materials)
    # These define the "rest" or "clean" appearance for the static image/PDF, independent of animation.
    static_phi: Optional[float] = None      # for 3D elements: camera-like phi for this element
    static_theta: Optional[float] = None    # for 3D elements
    static_scale: float = 1.0
    static_opacity: float = 1.0

    # When True (default), the scene pans the viewport to this element before reveal.
    auto_focus: bool = True

    # Consecutive timeline items sharing a flex_group reveal together (one scroll, one play).
    flex_group: Optional[str] = None

    def get_anchor(self, anchor: str = "center") -> Vector3:
        """Simple anchor for CanvasElement (local to its space)."""
        if anchor == "center":
            return Vector3(0, 0, 0)
        if anchor.startswith("local:"):
            try:
                p = [float(x) for x in anchor[6:].split(",")]
                return Vector3(p[0], p[1], p[2] if len(p)>2 else 0)
            except:
                pass
        # use canvas_position as local
        if hasattr(self, 'canvas_position'):
            return Vector3.from_tuple(self.canvas_position)
        return Vector3(0, 0, 0)

    def __post_init__(self):
        # Phase 1 compat: if world_transform not set but canvas_position has data, seed it.
        if self.canvas_position != (0.0, 0.0, 0.0):
            if self.world_transform.position.x == 0.0 and self.world_transform.position.y == 0.0 and self.world_transform.position.z == 0.0:
                self.world_transform.position = Vector3.from_tuple(self.canvas_position)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.layout is None:
            d.pop("layout", None)
        if self.entry_animation is None:
            d.pop("entry_animation", None)
        if self.state_behavior is None:
            d.pop("state_behavior", None)

        return d


@dataclass
class CameraMove:
    """Viewport movement along the infinite Y (scroll) axis.
    Kept for backward compat. Phase 3 generalizes to CameraObservation / keyframes.
    """
    id: str
    type: Literal["CameraMove"] = "CameraMove"
    target_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    run_time: float = 2.0
    rate_func: str = "smooth"   # smooth | linear | rush | etc. (mapped later)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Phase 3: Generalized camera observation system (per 3D world model docs)
# Keyframes target world points, objects, or tape-specific scroll.
# When targeting TapeObject, uses special local framing + scroll+reveal protocol.
@dataclass
class WorldPoint:
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)

@dataclass
class ObjectAnchor:
    object_id: str
    anchor: str = "center"  # "center", "top", "local_y:xx" etc.
    framing: str = "cinematic"  # "cinematic" or "face_on"


@dataclass
class CameraKeyframe:
    """General camera keyframe / observation in 3D space.
    target can be absolute world point or relative to object (with special tape handling).
    """
    id: str
    time: float = 0.0
    target: ObservationTarget = field(default_factory=WorldPoint)
    duration: float = 2.0
    rate_func: str = "smooth"
    # optional params like look_at_offset, distance, etc.
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = "CameraKeyframe"  # ensure from_dict roundtrips
        # simplify target for serialization
        if isinstance(self.target, WorldPoint):
            d["target"] = {"kind": "world_point", "position": self.target.position}
        elif isinstance(self.target, ObjectAnchor):
            d["target"] = {"kind": "object_anchor", "object_id": self.target.object_id, "anchor": self.target.anchor, "framing": getattr(self.target, "framing", "cinematic")}
        return d


@dataclass
class TransformElement:
    """Re-animate or transform an already-placed element (callback / highlight)."""
    id: str
    type: Literal["TransformElement"] = "TransformElement"
    source_id: str = ""
    target_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    action: str = "FlashAndScale"
    scale_factor: float = 1.2
    run_time: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlotTrace:
    """Animate a tracing dot along a quadratic plot to show y changing with x."""
    id: str
    type: Literal["PlotTrace"] = "PlotTrace"
    element_id: str = ""
    plot_index: int = 0
    x_from: float = -2.0
    x_to: float = 2.0
    run_time: float = 3.0
    show_readout: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SolidLift:
    """Raise a volumetric element off the tape for 3D inspection."""
    id: str
    type: Literal["SolidLift"] = "SolidLift"
    element_id: str = ""
    lift: float = 1.5
    run_time: float = 1.2
    rate_func: str = "smooth"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SolidRotate:
    """Rotate a volumetric element about its center — keyframe path, preset, or one shot."""
    id: str
    type: Literal["SolidRotate"] = "SolidRotate"
    element_id: str = ""
    path: Optional[List[Dict[str, Any]]] = None
    preset: Optional[str] = None
    preset_kwargs: Dict[str, Any] = field(default_factory=dict)
    axis: str = "y"
    angle: float = 90.0
    space: Literal["local", "world"] = "local"
    run_time: float = 1.2
    hold: float = 0.0
    rate_func: str = "smooth"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not self.path:
            d.pop("path", None)
        if not self.preset:
            d.pop("preset", None)
        if not self.preset_kwargs:
            d.pop("preset_kwargs", None)
        return d


@dataclass
class CameraInspect:
    """Keyframe inspect path around a 3D target — shots, holds, presets, or legacy orbit."""
    id: str
    type: Literal["CameraInspect"] = "CameraInspect"
    element_id: str = ""
    # Keyframe path (primary API) — list of shot dicts or InspectKeyframe-compatible payloads
    path: Optional[List[Dict[str, Any]]] = None
    preset: Optional[str] = None
    preset_kwargs: Dict[str, Any] = field(default_factory=dict)
    curve: Literal["linear", "smooth"] = "smooth"
    # Legacy single-shot + orbit (expanded to keyframes automatically)
    phi: float = 65.0
    theta: float = -50.0
    run_time: float = 1.6
    hold_time: float = 0.0
    orbit: bool = False
    orbit_degrees: float = 360.0
    orbit_run_time: float = 4.0
    return_to_sheet: bool = True
    return_run_time: float = 1.0
    rate_func: str = "smooth"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not self.path:
            d.pop("path", None)
        if not self.preset:
            d.pop("preset", None)
        if not self.preset_kwargs:
            d.pop("preset_kwargs", None)
        return d


@dataclass
class CameraFocus:
    """Focus on one canvas element — isolate-zoom (default) or overlay magnifier."""
    id: str
    type: Literal["CameraFocus"] = "CameraFocus"
    element_id: str = ""
    mode: Literal["isolate", "overlay"] = "isolate"
    zoom: float = 2.0  # isolate: frame magnification | overlay: auto-fit scale multiplier
    dim_opacity: float = 0.1  # isolate only — opacity for non-target elements
    run_time: float = 1.1
    highlight: bool = True
    hold_time: float = 1.2
    reset_zoom: bool = True  # zoom out / dismiss overlay when done
    reset_run_time: float = 0.9

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Phase 1: Minimal WorldObject / scene graph concept.
# This is the foundation for treating the tape as one object among many in 3D space.
# Existing CanvasElement can be wrapped; full TapeObject comes in later phases.
@dataclass
class WorldObject:
    """An object in the unified 3D world space.

    - id: stable identifier
    - element: the visual payload (for Phase 1 mostly CanvasElement)
    - transform: position/orientation/scale in world space
    - children: nested objects (allows composition, future nested tapes)
    """
    id: str
    element: Optional[CanvasElement] = None
    transform: WorldTransform = field(default_factory=WorldTransform)
    children: List["WorldObject"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "element": self.element.to_dict() if self.element and hasattr(self.element, "to_dict") else (self.element if self.element else None),
            "transform": self.transform.to_dict(),
            "children": [c.to_dict() for c in self.children],
        }

    def get_anchor(self, anchor: str = "center") -> Vector3:
        """Basic anchor for general WorldObject (delegate to element if possible, else center)."""
        if self.element and hasattr(self.element, 'get_anchor'):
            return self.element.get_anchor(anchor)
        if anchor == "center":
            return Vector3(0, 0, 0)
        # simple local parse
        if anchor.startswith("local:"):
            try:
                parts = anchor[6:].split(",")
                return Vector3(float(parts[0]), float(parts[1]), float(parts[2]) if len(parts)>2 else 0)
            except:
                pass
        return Vector3(0, 0, 0)

    def get_surface_info(self) -> dict:
        if self.element and hasattr(self.element, 'get_surface_info'):
            return self.element.get_surface_info()
        wt = self.transform
        info = {"is_planar": False}
        if wt:
            info.update({
                "world_position": wt.position.as_tuple(),
                "world_rotation": wt.rotation.as_tuple(),
                "world_scale": wt.scale,
            })
        return info


@dataclass
class TapeObject:
    """TapeObject represents an isolated 2D infinite layout canvas.
    Content (local_elements) lives in a local 2D coordinate system where the
    existing LayoutEngine, CSS-like styling, flex, and lazy reveal apply.
    Tapes are strictly 2D and context-switched in real-time with the 3D world.
    """
    id: str
    local_elements: List[CanvasElement] = field(default_factory=list)
    local_canvas_settings: Optional[CanvasSettings] = None
    # Future: local size, surface for 3D rendering, etc.

    def get_anchor(self, anchor: str = "center") -> Vector3:
        """Return local position for a named anchor on the tape.
        Supports 'center', 'top_edge', 'bottom_edge', 'content_center', etc.
        """
        if anchor == "center":
            return Vector3(0, 0, 0)
        if anchor == "top_edge":
            h = self.local_canvas_settings.frame_height if self.local_canvas_settings else 16.0
            return Vector3(0, h/2, 0)
        if anchor == "bottom_edge":
            h = self.local_canvas_settings.frame_height if self.local_canvas_settings else 16.0
            return Vector3(0, -h/2, 0)
        if anchor == "content_center":
            # simplistic: average of element positions, or 0
            if self.local_elements:
                ys = [getattr(e, 'canvas_position', (0,0,0))[1] for e in self.local_elements if hasattr(e, 'canvas_position')]
                avg_y = sum(ys)/len(ys) if ys else 0
                return Vector3(0, avg_y, 0)
            return Vector3(0, 0, 0)
        # custom local offset like "local:0,1.5"
        if anchor.startswith("local:"):
            try:
                parts = anchor[6:].split(",")
                return Vector3(float(parts[0]), float(parts[1]), float(parts[2]) if len(parts)>2 else 0)
            except:
                pass
        return Vector3(0, 0, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "local_elements": [e.to_dict() if hasattr(e, 'to_dict') else e for e in self.local_elements],
            # omit settings for brevity
        }

    def get_local_frame(self) -> tuple[float, float]:
        s = self.local_canvas_settings
        return (s.frame_width if s else 9.0, s.frame_height if s else 16.0)

    def get_surface_info(self) -> dict:
        w, h = self.get_local_frame()
        wt = self.world_transform
        info = {
            "width": w,
            "height": h,
            "is_planar": True,
            "local_space": "2d",
        }
        if wt:
            info.update({
                "world_position": wt.position.as_tuple(),
                "world_rotation": wt.rotation.as_tuple(),
                "world_scale": wt.scale,
            })
        return info


# Union of all timeline item types
TimelineItem = Union[
    CanvasElement,
    CameraMove,
    CameraKeyframe,  # Phase 3 generalized
    TransformElement,
    PlotTrace,
    SolidLift,
    SolidRotate,
    CameraInspect,
    CameraFocus,
]


@dataclass
class CanvasSettings:
    """Global canvas and render configuration.

    This is the single source of truth for both the logical canvas viewport
    AND the final rendered video format.

    Design principle: Portrait-first (Reels / Shorts / TikTok).
    Landscape (YouTube long-form) is fully supported.

    Recommended usage:
        settings = CanvasSettings.for_reels()           # default portrait 9:16
        settings = CanvasSettings.for_youtube()         # landscape 16:9

    You can override individual values after creation:
        settings = CanvasSettings.for_reels(pixel_width=720, pixel_height=1280)
    """

    # --- Format control (explicit and opinionated) ---
    orientation: Literal["portrait", "landscape"] = "portrait"

    # Logical viewport size in Manim units (affects camera framing & scrolling feel)
    # For portrait: tall viewport (more vertical content visible at once)
    # For landscape: wide viewport
    frame_width: float = 9.0
    frame_height: float = 16.0

    background_color: str = "#111111"

    # Final rendered video resolution (this determines the actual file aspect ratio)
    pixel_width: int = 1080
    pixel_height: int = 1920

    # Optional metadata
    title: str = "Matemium"
    version: str = "matemium-0.1"

    # Phase 1: coordinate system mode for the emerging 3D world model.
    # "sheet" = legacy tape at z=0 (default for full backward compat)
    # "space" = full 3D world (future)
    coordinate_system: str = "sheet"

    def __post_init__(self):
        # Auto-correct frame and pixel sizes when orientation is explicitly set
        # and the values are still at the class defaults. This makes "portrait-first"
        # behavior very robust.
        if self.orientation == "portrait":
            if self.frame_width == 9.0 and self.frame_height == 16.0:
                pass  # already correct
            if self.pixel_width == 1080 and self.pixel_height == 1920:
                pass
        elif self.orientation == "landscape":
            if self.frame_width == 9.0 and self.frame_height == 16.0:
                self.frame_width = 16.0
                self.frame_height = 9.0
            if self.pixel_width == 1080 and self.pixel_height == 1920:
                self.pixel_width = 1920
                self.pixel_height = 1080

    @classmethod
    def for_reels(cls, **overrides) -> "CanvasSettings":
        """Convenience: Reel / TikTok / YouTube Shorts friendly (portrait 9:16).

        This is the primary, default target.
        """
        base = cls(orientation="portrait")
        for key, value in overrides.items():
            setattr(base, key, value)
        return base

    @classmethod
    def for_youtube(cls, **overrides) -> "CanvasSettings":
        """Convenience: Classic YouTube long-form friendly (landscape 16:9)."""
        base = cls(orientation="landscape")
        for key, value in overrides.items():
            setattr(base, key, value)
        return base

    def get_manim_resolution(self) -> tuple[int, int]:
        """Returns (pixel_width, pixel_height) for use in tempconfig or -r flag."""
        return (self.pixel_width, self.pixel_height)

    def get_frame_size(self) -> tuple[float, float]:
        """Returns (frame_width, frame_height) for CameraController."""
        return (self.frame_width, self.frame_height)

    @property
    def aspect_ratio(self) -> str:
        """Human readable aspect ratio, e.g. '9:16' or '16:9'."""
        return f"{int(self.frame_width)}:{int(self.frame_height)}"

    @property
    def is_portrait(self) -> bool:
        return self.orientation == "portrait"

    def get_manim_config_dict(self) -> dict:
        """Returns a ready-to-use dict for manim.tempconfig."""
        return {
            "pixel_width": self.pixel_width,
            "pixel_height": self.pixel_height,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "background_color": self.background_color,
        }


@dataclass
class SheetDSL:
    """The complete sheet specification. The source of truth for the canvas.

    Phase 2+: may represent local content of a TapeObject.
    Phase 5: evolved to support root_objects for 3D world (WorldObject graph).
    timeline kept for backward compat and tape sugar.
    """
    canvas_settings: CanvasSettings = field(default_factory=CanvasSettings)
    timeline: List[TimelineItem] = field(default_factory=list)
    root_objects: List["WorldObject"] = field(default_factory=list)
    tapes: List["TapeObject"] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SheetDSL":
        raw_settings = data.get("canvas_settings", {})

        # If orientation is explicitly given, start from the right factory
        # so __post_init__ and defaults behave correctly.
        if "orientation" in raw_settings:
            orientation = raw_settings["orientation"]
            if orientation == "portrait":
                base_settings = CanvasSettings.for_reels()
            else:
                base_settings = CanvasSettings.for_youtube()
            # Apply any user overrides on top
            for k, v in raw_settings.items():
                if hasattr(base_settings, k):
                    setattr(base_settings, k, v)
            settings = base_settings
        else:
            settings = CanvasSettings(**raw_settings)
        timeline: List[TimelineItem] = []

        for item in data.get("timeline", []):
            t = item.get("type")
            if t in ("MathTex", "Text", "ThreeDGraph", "Surface", "Solid3D", "Axes",
                     "NumberPlane", "ParametricFunction", "VGroup", "Dot", "Arrow",
                     "Image", "SVG", "GridBoard", "GridMark", "QuadraticPlot",
                     "QuadraticPlotPair"):
                entry = None
                if "entry_animation" in item:
                    entry = EntryAnimation(**item["entry_animation"])
                behavior = None
                if "state_behavior" in item or "state_behaviors" in item:
                    bdata = item.get("state_behavior") or item.get("state_behaviors") or {}
                    behavior = StateBehavior(**bdata)
                layout = None
                if "layout" in item and item["layout"]:
                    layout = LayoutBox.from_dict(item["layout"])
                elem = CanvasElement(
                    id=item["id"],
                    type=t,  # type: ignore
                    content=item.get("content"),
                    canvas_position=tuple(item.get("canvas_position", (0, 0, 0))),
                    # Phase 1
                    world_transform=WorldTransform.from_dict(item.get("world_transform")) if item.get("world_transform") else WorldTransform(),
                    layout=layout,
                    entry_animation=entry,
                    state_behavior=behavior,
                    pitch=item.get("axis_pitch") or item.get("pitch"),
                    yaw=item.get("axis_yaw") or item.get("yaw"),
                    static_phi=item.get("static_phi"),
                    static_theta=item.get("static_theta"),
                    static_scale=item.get("static_scale", 1.0),
                    static_opacity=item.get("static_opacity", 1.0),
                    auto_focus=item.get("auto_focus", True),
                    flex_group=item.get("flex_group"),
                )
                timeline.append(elem)
            elif t == "CameraMove":
                cm = CameraMove(
                    id=item["id"],
                    target_position=tuple(item.get("target_position", (0, 0, 0))),
                    run_time=item.get("run_time", 2.0),
                    rate_func=item.get("rate_func", "smooth"),
                )
                timeline.append(cm)
            elif t == "CameraKeyframe":
                # Phase 3
                target_data = item.get("target", {})
                kind = target_data.get("kind")
                if kind == "world_point":
                    tgt = WorldPoint(position=tuple(target_data.get("position", (0,0,0))))
                elif kind == "object_anchor":
                    tgt = ObjectAnchor(
                        object_id=target_data.get("object_id", ""), 
                        anchor=target_data.get("anchor", "center"),
                        framing=target_data.get("framing", "cinematic")
                    )

                else:
                    tgt = WorldPoint()
                ck = CameraKeyframe(
                    id=item["id"],
                    time=float(item.get("time", 0)),
                    target=tgt,
                    duration=float(item.get("duration", item.get("run_time", 2.0))),
                    rate_func=item.get("rate_func", "smooth"),
                    params=dict(item.get("params") or {}),
                )
                timeline.append(ck)
            elif t == "TransformElement":
                te = TransformElement(
                    id=item["id"],
                    source_id=item.get("source_id", ""),
                    target_position=tuple(item.get("target_position", (0, 0, 0))),
                    action=item.get("action", "FlashAndScale"),
                    scale_factor=item.get("scale_factor", 1.2),
                    run_time=item.get("run_time", 1.0),
                )
                timeline.append(te)
            elif t == "PlotTrace":
                timeline.append(PlotTrace(
                    id=item["id"],
                    element_id=item.get("element_id", ""),
                    plot_index=int(item.get("plot_index", 0)),
                    x_from=float(item.get("x_from", -2.0)),
                    x_to=float(item.get("x_to", 2.0)),
                    run_time=float(item.get("run_time", 3.0)),
                    show_readout=bool(item.get("show_readout", True)),
                ))
            elif t == "SolidLift":
                timeline.append(SolidLift(
                    id=item["id"],
                    element_id=item.get("element_id", ""),
                    lift=float(item.get("lift", 1.5)),
                    run_time=float(item.get("run_time", 1.2)),
                    rate_func=item.get("rate_func", "smooth"),
                ))
            elif t == "SolidRotate":
                timeline.append(SolidRotate(
                    id=item["id"],
                    element_id=item.get("element_id", ""),
                    path=item.get("path"),
                    preset=item.get("preset"),
                    preset_kwargs=dict(item.get("preset_kwargs") or {}),
                    axis=str(item.get("axis", "y")),
                    angle=float(item.get("angle", 90.0)),
                    space=item.get("space", "local"),  # type: ignore[arg-type]
                    run_time=float(item.get("run_time", 1.2)),
                    hold=float(item.get("hold", item.get("hold_time", 0.0))),
                    rate_func=item.get("rate_func", "smooth"),
                ))
            elif t == "CameraInspect":
                timeline.append(CameraInspect(
                    id=item["id"],
                    element_id=item.get("element_id", ""),
                    path=item.get("path"),
                    preset=item.get("preset"),
                    preset_kwargs=dict(item.get("preset_kwargs") or {}),
                    curve=item.get("curve", "smooth"),  # type: ignore[arg-type]
                    phi=float(item.get("phi", 65.0)),
                    theta=float(item.get("theta", -50.0)),
                    run_time=float(item.get("run_time", 1.6)),
                    hold_time=float(item.get("hold_time", 0.0)),
                    orbit=bool(item.get("orbit", False)),
                    orbit_degrees=float(item.get("orbit_degrees", 360.0)),
                    orbit_run_time=float(item.get("orbit_run_time", 4.0)),
                    return_to_sheet=bool(item.get("return_to_sheet", True)),
                    return_run_time=float(item.get("return_run_time", 1.0)),
                    rate_func=item.get("rate_func", "smooth"),
                ))
            elif t == "CameraFocus":
                timeline.append(CameraFocus(
                    id=item["id"],
                    element_id=item.get("element_id", ""),
                    mode=item.get("mode", "isolate"),
                    zoom=float(item.get("zoom", 2.0)),
                    dim_opacity=float(item.get("dim_opacity", 0.1)),
                    run_time=float(item.get("run_time", 1.1)),
                    highlight=bool(item.get("highlight", True)),
                    hold_time=float(item.get("hold_time", 1.2)),
                    reset_zoom=bool(item.get("reset_zoom", True)),
                    reset_run_time=float(item.get("reset_run_time", 0.9)),
                ))
            else:
                # Unknown type - skip or raise in strict mode
                continue

        dsl = cls(canvas_settings=settings, timeline=timeline)
        
        tapes_data = data.get("tapes", [])
        if "additional_tapes" in data:
            tapes_data.extend(data["additional_tapes"])
        if "root_tape" in data and data["root_tape"]:
            tapes_data.insert(0, data["root_tape"])
            
        for tdata in tapes_data:
            t = TapeObject(
                id=tdata.get("id", "tape"),
                local_elements=[], # Timeline reconstructs local_elements in Scene
                local_canvas_settings=CanvasSettings(**tdata.get("local_canvas_settings", {})),
            )
            dsl.tapes.append(t)

        # Phase 5: support root_objects for general 3D
        root_objs_data = data.get("root_objects", [])
        for obj_data in root_objs_data:
            wo = WorldObject(
                id=obj_data["id"],
                transform=WorldTransform.from_dict(obj_data.get("transform", {})),
                # element and children would be reconstructed if needed
            )
            dsl.root_objects.append(wo)
        return dsl

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "SheetDSL":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "canvas_settings": asdict(self.canvas_settings),
            "timeline": [item.to_dict() if hasattr(item, "to_dict") else asdict(item) for item in self.timeline],
            "tapes": [t.to_dict() for t in self.tapes],
        }
        if getattr(self, "root_tape", None):
            d["root_tape"] = self.root_tape.to_dict()
        if self.root_objects:
            d["root_objects"] = [o.to_dict() for o in self.root_objects]
        return d

    def to_json(self, path: Union[str, Path] | None = None, indent: int = 2) -> str:
        s = json.dumps(self.to_dict(), indent=indent)
        if path:
            Path(path).write_text(s, encoding="utf-8")
        return s

    # Convenience builders (lightweight Python DSL)
    def add_element(self, elem: CanvasElement) -> "SheetDSL":
        self.timeline.append(elem)
        return self

    def add_camera_move(self, cm: CameraMove) -> "SheetDSL":
        self.timeline.append(cm)
        return self

    def add_transform(self, te: TransformElement) -> "SheetDSL":
        self.timeline.append(te)
        return self

    def add_plot_trace(self, pt: PlotTrace) -> "SheetDSL":
        self.timeline.append(pt)
        return self

    def add_solid_lift(self, sl: SolidLift) -> "SheetDSL":
        self.timeline.append(sl)
        return self

    def add_solid_rotate(self, sr: SolidRotate) -> "SheetDSL":
        self.timeline.append(sr)
        return self

    def add_camera_inspect(self, ci: CameraInspect) -> "SheetDSL":
        self.timeline.append(ci)
        return self

    def add_camera_focus(self, cf: CameraFocus) -> "SheetDSL":
        self.timeline.append(cf)
        return self
