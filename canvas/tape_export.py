"""Deterministic, camera-independent tape document exports.

Tape exports are documents, not snapshots of the animated world.  This module
therefore rebuilds a tape in its own local XY coordinate system and renders it
with fresh orthographic cameras.  It deliberately does not reuse a
``CanvasScene`` camera, renderer, mobjects, or updaters.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Iterable, Literal

import numpy as np
from manim import DEGREES, RIGHT, UP
from manim.camera.camera import Camera

from .dsl import (
    ElementMorph,
    SheetDSL,
    StateTransition,
    TapeObject,
    TransformElement,
)
from .generic_visuals import resolve_semantic_part
from .measure import build_mobject, make_render_surface
from .solids import place_solid_on_tape

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - handled by the public entry point
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]


DEFAULT_TILE_PIXELS = 4096
DEFAULT_MAX_IMAGE_PIXELS = 160_000_000
TILE_OVERLAP_PIXELS = 4


@dataclass(frozen=True)
class TapeExportLayout:
    """Resolved document bounds and raster dimensions."""

    min_x: float
    max_x: float
    min_y: float
    max_y: float
    pixels_per_unit: float
    pixel_width: int
    pixel_height: int

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y


def available_tapes(dsl: SheetDSL) -> list[TapeObject]:
    """Return every tape once, covering both current and legacy DSL shapes."""
    candidates: list[TapeObject] = []
    root = getattr(dsl, "root_tape", None)
    if root is not None:
        candidates.append(root)
    candidates.extend(getattr(dsl, "tapes", None) or [])
    candidates.extend(getattr(dsl, "additional_tapes", None) or [])

    result: list[TapeObject] = []
    seen: set[str] = set()
    for tape in candidates:
        tape_id = getattr(tape, "id", None)
        if tape is None or not tape_id or tape_id in seen:
            continue
        seen.add(tape_id)
        result.append(tape)
    return result


def resolve_tape(dsl: SheetDSL, tape_id: str | None = None) -> TapeObject:
    tapes = available_tapes(dsl)
    if tape_id is None:
        root = getattr(dsl, "root_tape", None)
        if root is not None and getattr(root, "local_elements", None):
            return root
        nonempty = [t for t in tapes if getattr(t, "local_elements", None)]
        if len(nonempty) == 1:
            return nonempty[0]
        if not nonempty:
            raise ValueError("The DSL contains no tapes to export.")
        raise ValueError(
            "tape_id is required when multiple tapes contain content and the root tape is empty."
        )

    for tape in tapes:
        if tape.id == tape_id:
            return tape
    available = ", ".join(t.id for t in tapes) or "(none)"
    raise ValueError(f"Unknown tape_id {tape_id!r}. Available tapes: {available}.")


def _vector3(value: Any) -> np.ndarray:
    values = list(value)
    if len(values) == 2:
        values.append(0.0)
    return np.array(values[:3], dtype=float)


def _apply_state_changes(target, changes: dict[str, Any]) -> None:
    if "color" in changes:
        target.set_color(changes["color"])
    if "fill_color" in changes:
        target.set_fill(color=changes["fill_color"])
    if "fill_opacity" in changes:
        target.set_fill(opacity=float(changes["fill_opacity"]))
    stroke_kwargs: dict[str, Any] = {}
    if "stroke_color" in changes:
        stroke_kwargs["color"] = changes["stroke_color"]
    if "stroke_opacity" in changes:
        stroke_kwargs["opacity"] = float(changes["stroke_opacity"])
    if "stroke_width" in changes:
        stroke_kwargs["width"] = float(changes["stroke_width"])
    if stroke_kwargs:
        target.set_stroke(**stroke_kwargs)
    if "opacity" in changes:
        target.set_opacity(float(changes["opacity"]))
    if "scale" in changes:
        target.scale(float(changes["scale"]))
    if "shift" in changes:
        target.shift(_vector3(changes["shift"]))
    if "position" in changes:
        target.move_to(_vector3(changes["position"]))


def build_tape_mobjects(
    dsl: SheetDSL,
    tape: TapeObject,
) -> tuple[list[Any], dict[str, Any]]:
    """Compile fresh, updater-free mobjects in the tape's local coordinates."""
    ordered: list[Any] = []
    by_id: dict[str, Any] = {}
    tape_ids = {elem.id for elem in tape.local_elements}

    for elem in tape.local_elements:
        mob = build_mobject(elem, surface_factory=make_render_surface)
        if mob is None:
            continue

        position = _vector3(getattr(elem, "canvas_position", (0.0, 0.0, 0.0)))
        if elem.type == "Solid3D":
            place_solid_on_tape(mob, tuple(position), elem.content)
        else:
            mob.move_to(position)

        # Static state is explicit author intent.  Unlike the former exporter,
        # no inferred rotations are ever applied to ordinary tape text/math.
        if elem.static_scale != 1.0:
            mob.scale(float(elem.static_scale))
        if elem.static_opacity != 1.0:
            mob.set_opacity(float(elem.static_opacity))
        if elem.static_phi is not None:
            mob.rotate(
                float(elem.static_phi) * DEGREES,
                axis=UP,
                about_point=mob.get_center(),
            )
        if elem.static_theta is not None:
            mob.rotate(
                float(elem.static_theta) * DEGREES,
                axis=RIGHT,
                about_point=mob.get_center(),
            )

        mob.clear_updaters(recursive=True)
        ordered.append(mob)
        by_id[elem.id] = mob

    # Reduce supported timeline mutations to their final state without playing
    # animations.  Camera/focus/inspection actions intentionally have no place
    # in a document export.
    for item in getattr(dsl, "timeline", None) or []:
        if isinstance(item, TransformElement) and item.source_id in tape_ids:
            target = by_id.get(item.source_id)
            if target is not None:
                target.move_to(_vector3(item.target_position))
        elif isinstance(item, StateTransition):
            for patch in item.patches:
                element_id, separator, part_id = patch.target_id.partition("::")
                if element_id not in tape_ids:
                    continue
                target = by_id.get(element_id)
                if target is None:
                    continue
                if separator:
                    target = resolve_semantic_part(target, part_id)
                if target is not None:
                    _apply_state_changes(target, patch.changes)
        elif isinstance(item, ElementMorph) and item.element_id in tape_ids:
            source = by_id.get(item.element_id)
            if source is None:
                continue
            target = build_mobject(item.target, surface_factory=make_render_surface)
            if target is None:
                continue
            target.move_to(source.get_center())
            target.clear_updaters(recursive=True)
            index = ordered.index(source)
            ordered[index] = target
            by_id[item.element_id] = target

    return ordered, by_id


def _content_bounds(mobjects: Iterable[Any]) -> tuple[float, float, float, float]:
    min_x = math.inf
    max_x = -math.inf
    min_y = math.inf
    max_y = -math.inf
    found = False
    for mob in mobjects:
        try:
            points = np.asarray(mob.get_all_points(), dtype=float)
            if points.size:
                box = points
            else:
                box = np.asarray(
                    [
                        mob.get_left(),
                        mob.get_right(),
                        mob.get_bottom(),
                        mob.get_top(),
                    ],
                    dtype=float,
                )
        except Exception:
            try:
                box = np.asarray(
                    [
                        mob.get_left(),
                        mob.get_right(),
                        mob.get_bottom(),
                        mob.get_top(),
                    ],
                    dtype=float,
                )
            except Exception:
                continue
        if box.size == 0 or not np.all(np.isfinite(box)):
            continue
        min_x = min(min_x, float(np.min(box[:, 0])))
        max_x = max(max_x, float(np.max(box[:, 0])))
        min_y = min(min_y, float(np.min(box[:, 1])))
        max_y = max(max_y, float(np.max(box[:, 1])))
        found = True
    if not found:
        raise ValueError("The selected tape has no renderable content.")
    return min_x, max_x, min_y, max_y


def plan_tape_export(
    mobjects: Iterable[Any],
    *,
    settings,
    margin: float,
    high_res_height: int | None,
    natural_aspect: bool,
) -> TapeExportLayout:
    if margin < 0:
        raise ValueError("margin must be non-negative.")
    min_x, max_x, min_y, max_y = _content_bounds(mobjects)
    min_x -= margin
    max_x += margin
    min_y -= margin
    max_y += margin

    width = max(max_x - min_x, 1e-6)
    height = max(max_y - min_y, 1e-6)
    if not natural_aspect:
        target_aspect = float(settings.frame_width) / float(settings.frame_height)
        if width / height < target_aspect:
            extra = (height * target_aspect - width) / 2
            min_x -= extra
            max_x += extra
            width = max_x - min_x
        else:
            extra = (width / target_aspect - height) / 2
            min_y -= extra
            max_y += extra
            height = max_y - min_y

    if high_res_height is not None:
        if high_res_height <= 0:
            raise ValueError("high_res_height must be positive.")
        pixels_per_unit = float(high_res_height) / height
    else:
        # Preserve the video's native detail per logical unit.  Long tapes get
        # more pixels instead of progressively smaller, unreadable text.
        pixels_per_unit = max(
            float(settings.pixel_width) / float(settings.frame_width),
            float(settings.pixel_height) / float(settings.frame_height),
        )

    pixels_per_unit = max(pixels_per_unit, 1.0)
    pixel_width = max(1, int(math.ceil(width * pixels_per_unit)))
    pixel_height = max(1, int(math.ceil(height * pixels_per_unit)))
    return TapeExportLayout(
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        pixels_per_unit=pixels_per_unit,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
    )


def render_tape_tiles(
    mobjects: list[Any],
    layout: TapeExportLayout,
    *,
    background_color: str,
    tile_pixels: int = DEFAULT_TILE_PIXELS,
    max_image_pixels: int = DEFAULT_MAX_IMAGE_PIXELS,
):
    """Render an arbitrarily shaped document through bounded fresh cameras."""
    if Image is None:
        raise RuntimeError("Pillow (PIL) is required for tape export.")
    if tile_pixels <= 0:
        raise ValueError("tile_pixels must be positive.")
    total_pixels = layout.pixel_width * layout.pixel_height
    if total_pixels > max_image_pixels:
        raise ValueError(
            f"Tape export would contain {total_pixels:,} pixels "
            f"({layout.pixel_width}x{layout.pixel_height}), exceeding the "
            f"safety limit of {max_image_pixels:,}. Pass high_res_height to "
            "request a smaller output."
        )

    output = Image.new("RGBA", (layout.pixel_width, layout.pixel_height))
    ppu = layout.pixels_per_unit

    for top in range(0, layout.pixel_height, tile_pixels):
        tile_h = min(tile_pixels, layout.pixel_height - top)
        for left in range(0, layout.pixel_width, tile_pixels):
            tile_w = min(tile_pixels, layout.pixel_width - left)
            # Render a small overlap around every internal tile edge, then
            # discard it.  Cairo can otherwise antialias a stroke differently
            # when the stroke lands exactly on a camera boundary, creating a
            # faint one-pixel stitch line.
            render_left = max(0, left - TILE_OVERLAP_PIXELS)
            render_top = max(0, top - TILE_OVERLAP_PIXELS)
            render_right = min(
                layout.pixel_width,
                left + tile_w + TILE_OVERLAP_PIXELS,
            )
            render_bottom = min(
                layout.pixel_height,
                top + tile_h + TILE_OVERLAP_PIXELS,
            )
            render_w = render_right - render_left
            render_h = render_bottom - render_top

            world_top = layout.max_y - render_top / ppu
            world_bottom = layout.max_y - render_bottom / ppu
            world_left = layout.min_x + render_left / ppu
            world_right = layout.min_x + render_right / ppu

            # A tape is an XY document.  The plain Cairo camera is intentional:
            # ThreeDCamera applies its world projection around frame_center and
            # is the source of the historical double-offset/camera-pose bugs.
            camera = Camera(
                pixel_width=render_w,
                pixel_height=render_h,
                frame_width=world_right - world_left,
                frame_height=world_top - world_bottom,
                frame_center=np.array(
                    [
                        (world_left + world_right) / 2,
                        (world_bottom + world_top) / 2,
                        0.0,
                    ]
                ),
                background_color=background_color,
                background_opacity=1.0,
            )
            camera.reset()
            camera.capture_mobjects(mobjects)
            rendered = camera.get_image().convert("RGBA")
            crop_left = left - render_left
            crop_top = top - render_top
            rendered = rendered.crop(
                (
                    crop_left,
                    crop_top,
                    crop_left + tile_w,
                    crop_top + tile_h,
                )
            )
            output.paste(rendered, (left, top))

    return output


def _add_title_banner(image, title: str):
    banner_h = 70
    banner = Image.new("RGB", (image.width, banner_h), (15, 15, 15))
    draw = ImageDraw.Draw(banner)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            32,
        )
    except Exception:
        font = ImageFont.load_default()
    draw.text((25, 18), title, fill=(230, 230, 230), font=font)
    draw.rectangle([0, banner_h - 3, image.width, banner_h], fill=(60, 60, 60))
    result = Image.new("RGB", (image.width, image.height + banner_h), (0, 0, 0))
    result.paste(banner, (0, 0))
    result.paste(image.convert("RGB"), (0, banner_h))
    return result


def export_tape_document(
    dsl: SheetDSL,
    filename: str | Path,
    *,
    format: Literal["png", "pdf"] = "png",
    tape_id: str | None = None,
    high_res_height: int | None = None,
    margin: float = 1.2,
    title: str | None = None,
    natural_aspect: bool = True,
) -> Path:
    """Build and export a tape without touching the animated scene."""
    if Image is None:
        raise RuntimeError("Pillow (PIL) is required for tape export.")
    if format not in ("png", "pdf"):
        raise ValueError("format must be 'png' or 'pdf'.")

    output = Path(filename).with_suffix(f".{format}")
    output.parent.mkdir(parents=True, exist_ok=True)
    tape = resolve_tape(dsl, tape_id)
    mobjects, _ = build_tape_mobjects(dsl, tape)
    layout = plan_tape_export(
        mobjects,
        settings=tape.local_canvas_settings or dsl.canvas_settings,
        margin=margin,
        high_res_height=high_res_height,
        natural_aspect=natural_aspect,
    )
    image = render_tape_tiles(
        mobjects,
        layout,
        background_color=dsl.canvas_settings.background_color,
    )
    if title:
        image = _add_title_banner(image, title)

    if format == "pdf":
        save_kwargs: dict[str, Any] = {"resolution": 200.0}
        if title:
            save_kwargs["title"] = title
        image.convert("RGB").save(output, "PDF", **save_kwargs)
    else:
        image.save(output, "PNG", optimize=True)
    return output
