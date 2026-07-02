"""Sidecar command handlers — thin wrappers over canvas/ engine APIs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

# NOTE: No heavy imports (canvas, manim, render that pulls them) at module top level.
# All engine loading is deferred via matemium.lazy and local imports inside handlers.
# This makes the sidecar control-plane start instantly (CORE_READY / ping / get_status).

import os

from .. import lazy
from ..__version__ import __version__
from ..intelligence import get_retriever
from .duration import estimate_timeline_duration
from .events import EventEmitter
from .protocol import IPC_PROTOCOL_VERSION, ProtocolError
from .validate import validate_dsl_payload

# Lightweight workspace helpers (we still import the module, but its canvas use is now deferred)
from ..workspace import (
    exports_dir_for_workspace,
    media_dir_for_workspace,
    project_media_cache_dir,
    resolve_job_workspace,
)
from ..workspace_project import (
    check_project,
    lint_scenes_file,
    list_scenes_in_workspace,
    resolve_workspace,
)

HandlerFn = Callable[[dict[str, Any], EventEmitter], dict[str, Any]]


def _render_progress(events: EventEmitter) -> Callable[..., None]:
    def emit(**kwargs: Any) -> None:
        events.render_progress(**kwargs)

    return emit


def _resolve_scene_or_error(
    workspace: Path,
    scene: str | None,
    *,
    path: str | None = None,
) -> str:
    # Deferred: only called from heavy paths
    from ..workspace_project import resolve_scene_name
    try:
        return resolve_scene_name(workspace, scene, path=path)
    except (ValueError, RuntimeError) as exc:
        raise ProtocolError("SCENE_ERROR", str(exc)) from exc


def _exports_dir(params: dict[str, Any]) -> tuple[Path, str]:
    if params.get("workspace"):
        ws = _require_workspace(params)
        exports = ws / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        return exports, str(ws)
    job = resolve_job_workspace(params)
    return exports_dir_for_workspace(job), str(job)


def _require_workspace(params: dict[str, Any]) -> Path:
    try:
        return resolve_workspace(params)
    except FileNotFoundError as exc:
        raise ProtocolError("WORKSPACE_NOT_FOUND", str(exc)) from exc
    except ValueError as exc:
        raise ProtocolError("MISSING_WORKSPACE", str(exc)) from exc


def _dsl_from_params(params: dict[str, Any], *, strict: bool = True) -> Any:
    lazy.ensure_engine_loaded(None)
    from ..workspace_project import instantiate_scene

    if params.get("workspace"):
        workspace = _require_workspace(params)
        scene_name = _resolve_scene_or_error(
            workspace,
            params.get("scene"),
            path=params.get("path"),
        )
        return instantiate_scene(
            workspace,
            scene_name,
            path=params.get("path"),
        ).dsl
    return _require_dsl(params, strict=strict)


def _require_dsl(params: dict[str, Any], *, strict: bool = True) -> Any:
    dsl_data = params.get("dsl")
    if dsl_data is None:
        raise ProtocolError("MISSING_DSL", "params.dsl is required")
    result = validate_dsl_payload(dsl_data, strict=strict)
    if not result.valid or result.dsl is None:
        detail = "; ".join(e.message for e in result.errors[:3]) or "DSL validation failed"
        raise ProtocolError("INVALID_DSL", detail)
    return result.dsl


def handle_ping(_params: dict[str, Any], _events: EventEmitter) -> dict[str, Any]:
    # ping must stay completely light — no engine load
    return {
        "ok": True,
        "version": __version__,
        "protocol": IPC_PROTOCOL_VERSION,
        "engine": "matemium",
        "render_pipeline": "partial-movie-progress-v1",
    }


def handle_get_status(_params: dict[str, Any], _events: EventEmitter) -> dict[str, Any]:
    """Lightweight status. Does NOT trigger engine load."""
    status = lazy.get_status()
    status.update({
        "version": __version__,
        "protocol": IPC_PROTOCOL_VERSION,
    })
    return status


def handle_retrieve(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    """RAG retrieve using vector or keyword fallback."""
    lazy.ensure_intelligence_loaded(events)
    workspace = None
    if params.get("workspace"):
        workspace = _require_workspace(params)

    query = str(params.get("query", ""))
    top_k = int(params.get("top_k", 8))
    files = params.get("files") or ["scenes.py", "assets.py"]

    retriever = get_retriever(workspace)
    # Try to index relevant files if it's the vector retriever and not yet indexed
    if hasattr(retriever, "index_files"):
        try:
            retriever.index_files(files)
        except Exception:
            pass

    results = retriever.retrieve(query, top_k=top_k)
    return {"query": query, "results": results, "top_k": top_k}


def handle_configure_assets(params: dict[str, Any], _events: EventEmitter) -> dict[str, Any]:
    """Lightweight (no engine load): tell sidecar where first-run assets live.

    Example: {"tinytex_dir": "/path/to/Matemium/bin/tinytex"}
    Used by Rust desktop before any heavy command.
    """
    if td := params.get("tinytex_dir"):
        os.environ["MATEMIUM_TINYTEX_DIR"] = str(td)
    # Future: embeddings_model_dir, etc.
    return {"ok": True, "configured": list(params.keys())}


def handle_validate_dsl(params: dict[str, Any], _events: EventEmitter) -> dict[str, Any]:
    dsl_data = params.get("dsl")
    if dsl_data is None:
        raise ProtocolError("MISSING_DSL", "params.dsl is required")
    strict = bool(params.get("strict", True))
    result = validate_dsl_payload(dsl_data, strict=strict)
    payload = result.to_dict()
    if result.valid and result.dsl is not None:
        payload["duration_estimate"] = estimate_timeline_duration(result.dsl)
        payload["timeline_length"] = len(result.dsl.timeline)
    return payload


def handle_estimate_duration(params: dict[str, Any], _events: EventEmitter) -> dict[str, Any]:
    dsl = _require_dsl(params)
    return {"duration_estimate": estimate_timeline_duration(dsl)}


def handle_compile_preview(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    lazy.ensure_engine_loaded(events)
    # Local import after ensure (canvas now loaded)
    from canvas.dsl import CanvasElement

    dsl = _require_dsl(params)
    workspace = resolve_job_workspace(params)
    exports = exports_dir_for_workspace(workspace)
    quality = str(params.get("quality", "preview"))

    element_count = sum(1 for item in dsl.timeline if isinstance(item, CanvasElement))
    events.compile_started(element_count=element_count)
    duration = estimate_timeline_duration(dsl)
    events.layout_done(duration_estimate=duration)

    sheet_png = _export_static_sheet(dsl, exports / "preview_sheet", quality=quality)
    events.render_progress(pct=1.0, message="preview export complete")

    return {
        "duration_estimate": duration,
        "sheet_png": str(sheet_png),
        "workspace": str(workspace),
    }


def handle_render(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    lazy.ensure_engine_loaded(events)
    from ..play_count import resolve_animation_count

    # Local heavy imports
    from ..render import render_sheet

    dsl = _require_dsl(params)
    workspace = resolve_job_workspace(params)
    media = media_dir_for_workspace(workspace)
    quality = str(params.get("quality", "low"))
    output_name = params.get("output_name") or "CanvasScene"

    element_count = len(getattr(dsl, "timeline", [])) + len(getattr(dsl, "root_objects", []))
    events.compile_started(element_count=element_count)
    animation_count = resolve_animation_count(dsl)
    events.layout_done(
        duration_estimate=estimate_timeline_duration(dsl),
        animation_count=animation_count,
    )
    events.render_started(quality=quality, animation_count=animation_count)

    video = render_sheet(
        dsl,
        project="desktop",
        scene_name="CanvasScene",
        output_name=str(output_name),
        quality=quality,
        media_dir=media,
        on_progress=_render_progress(events),
        animation_estimate=animation_count,
    )

    events.render_complete(video=str(video))

    return {
        "video": str(video),
        "workspace": str(workspace),
        "duration_estimate": estimate_timeline_duration(dsl),
    }


def handle_list_scenes(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    # list_scenes will cause user scenes.py + canvas load inside workspace_project helpers
    lazy.ensure_engine_loaded(events)
    workspace = _require_workspace(params)
    scenes = list_scenes_in_workspace(workspace, path=params.get("path"))
    return {"scenes": scenes, "workspace": str(workspace)}


def handle_lint_project(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    # Lint is intentionally lightweight (syntax + ruff) — does not require full engine load
    workspace = _require_workspace(params)
    events.lint_started(workspace=str(workspace))
    diagnostics = lint_scenes_file(workspace, path=params.get("path"))
    events.lint_complete(count=len(diagnostics))
    return {
        "diagnostics": [d.to_dict() for d in diagnostics],
        "workspace": str(workspace),
        "ok": not any(d.severity == "error" for d in diagnostics),
    }


def handle_check_project(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    lazy.ensure_engine_loaded(events)
    workspace = _require_workspace(params)
    result = check_project(
        workspace,
        scene=params.get("scene"),
        path=params.get("path"),
    )
    events.check_complete(ok=bool(result.get("ok")), scene=str(result.get("scene", "")))
    return {**result, "workspace": str(workspace)}


def handle_render_project(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    lazy.ensure_engine_loaded(events)

    from ..play_count import resolve_animation_count

    # Heavy imports inside after ensure
    from ..render import (
        apply_render_orientation,
        normalize_orientation,
        publish_preview_video,
        render_quality_config,
        render_scene_class,
        render_sheet,
    )
    from ..workspace_project import (
        instantiate_scene,
        load_scene_class,
        resolve_scene_name,
    )

    workspace = _require_workspace(params)
    scene_name = _resolve_scene_or_error(
        workspace,
        params.get("scene"),
        path=params.get("path"),
    )

    check = check_project(workspace, scene=scene_name, path=params.get("path"))
    if not check.get("ok"):
        errors = check.get("errors") or []
        detail = errors[0].get("message", "check failed") if errors else "check failed"
        raise ProtocolError("CHECK_FAILED", detail)

    default_renders = workspace / "renders"
    export_dir_raw = params.get("output_dir")
    media = project_media_cache_dir(workspace)
    quality = str(params.get("quality", "low"))
    try:
        orientation = normalize_orientation(params.get("orientation"))
    except ValueError as exc:
        raise ProtocolError("INVALID_ORIENTATION", str(exc)) from exc

    scene_cls = load_scene_class(workspace, scene_name, path=params.get("path"))
    native = instantiate_scene(workspace, scene_name, path=params.get("path"))
    native_orientation = native.dsl.canvas_settings.orientation

    events.compile_started(element_count=len(native.dsl.timeline))
    progress = _render_progress(events)

    if orientation == native_orientation:
        dsl = native.dsl
    else:
        dsl = apply_render_orientation(native.dsl, orientation)
        progress(
            pct=0.02,
            message=(
                f"format {orientation} — scene authored for {native_orientation}; "
                "layout not reflowed"
            ),
        )

    animation_count = resolve_animation_count(dsl)
    events.layout_done(
        duration_estimate=estimate_timeline_duration(dsl),
        animation_count=animation_count,
    )
    events.render_started(quality=quality, animation_count=animation_count)

    if orientation == native_orientation:
        # Same code path as ``matemium render`` / ``./matemium.sh render``.
        manim_video = render_scene_class(
            scene_cls,
            project=workspace.name or "desktop",
            output_name=scene_name,
            quality=quality,
            media_dir=media,
            on_progress=progress,
            animation_estimate=animation_count,
        )
    else:
        manim_video = render_sheet(
            dsl,
            project=workspace.name or "desktop",
            scene_name=scene_name,
            output_name=scene_name,
            quality=quality,
            media_dir=media,
            on_progress=progress,
            animation_estimate=animation_count,
        )

    pw, ph = dsl.canvas_settings.get_manim_resolution()
    quality_cfg = render_quality_config(quality, base_width=pw, base_height=ph)

    default_renders.mkdir(parents=True, exist_ok=True)
    preview_video = publish_preview_video(manim_video, default_renders, scene_name)

    export_video = preview_video
    if export_dir_raw:
        export_base = Path(str(export_dir_raw)).resolve()
        if export_base != default_renders.resolve():
            export_video = publish_preview_video(manim_video, export_base, scene_name)

    events.render_complete(video=str(preview_video))

    return {
        "video": str(preview_video),
        "export_video": str(export_video),
        "manim_video": str(manim_video),
        "workspace": str(workspace),
        "scene": scene_name,
        "orientation": orientation,
        "aspect_ratio": dsl.canvas_settings.aspect_ratio,
        "pixel_width": quality_cfg["pixel_width"],
        "pixel_height": quality_cfg["pixel_height"],
        "duration_estimate": estimate_timeline_duration(dsl),
    }


def handle_export_sheet(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    dsl = _dsl_from_params(params)
    exports, workspace_str = _exports_dir(params)
    fmt = str(params.get("format", "png")).lower()
    if fmt not in ("png", "pdf"):
        raise ProtocolError("INVALID_FORMAT", "format must be png or pdf")

    quality = str(params.get("quality", "preview"))
    stem = params.get("filename") or "full_sheet"
    full_tape = bool(params.get("full_tape", True))
    title = params.get("title")

    element_count = len(getattr(dsl, "timeline", [])) + len(getattr(dsl, "root_objects", []))
    events.compile_started(element_count=element_count)
    path = _export_static_sheet(
        dsl,
        exports / str(stem),
        quality=quality,
        format=fmt,
        full_tape=full_tape,
        title=title,
    )
    return {"path": str(path), "format": fmt, "workspace": workspace_str}


def handle_cut_reels(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    lazy.ensure_engine_loaded(events)
    from ..workspace import resolve_job_workspace
    from canvas import ReelCutter

    video_raw = params.get("video")
    if not video_raw:
        raise ProtocolError("MISSING_VIDEO", "params.video is required")
    video = Path(str(video_raw))
    if not video.is_file():
        raise ProtocolError("VIDEO_NOT_FOUND", f"Video not found: {video}")

    if params.get("workspace"):
        dsl = _dsl_from_params(params)
        workspace = _require_workspace(params)
        workspace_str = str(workspace)
    elif params.get("dsl"):
        dsl = _require_dsl(params)
        workspace = resolve_job_workspace(params)
        workspace_str = str(workspace)
    else:
        dsl = None
        workspace = resolve_job_workspace(params)
        workspace_str = str(workspace)
    reels_dir = workspace / "reels"
    segment_duration = float(params.get("segment_duration", 55.0))

    cutter = ReelCutter(segment_duration=segment_duration)
    manifest = cutter.generate_manifest_from_dsl(dsl) if dsl else params.get("manifest")
    if not manifest:
        raise ProtocolError("MISSING_MANIFEST", "Provide params.dsl or params.manifest")

    produced = cutter.cut(video, reels_dir, manifest=manifest)
    return {
        "reels": [str(p) for p in produced],
        "workspace": workspace_str,
        "manifest": manifest,
    }


def _export_static_sheet(
    dsl: Any,
    stem: Path,
    *,
    quality: str = "preview",
    format: str = "png",
    full_tape: bool = True,
    title: str | None = None,
) -> Path:
    """Build a static sheet export without playing the full video timeline."""
    lazy.ensure_engine_loaded(None)
    from manim import tempconfig
    from canvas import CanvasScene

    from ..render import render_quality_config

    settings = dsl.canvas_settings
    pw, ph = settings.get_manim_resolution()
    config = settings.get_manim_config_dict()
    config.update(render_quality_config(quality, base_width=pw, base_height=ph))
    config["write_to_movie"] = False
    config["save_last_frame"] = False

    with tempconfig(config):
        scene = CanvasScene(dsl=dsl)
        scene.populate_from_dsl(play_entries=False)
        return scene.export_full_sheet(
            stem,
            format=format,  # type: ignore[arg-type]
            full_tape=full_tape,
            title=title or settings.title,
        )


def _serialize_preview_element(el: Any) -> dict[str, Any]:
    """Rich serialization for manim-web preview (1-1 as possible)."""
    # Lazy canvas names resolved by caller ensure; local import for isinstance safety in future calls
    from canvas.dsl import CanvasElement as _CanvasElement
    if not isinstance(el, _CanvasElement):
        # defensive
        pass
    raw_content = el.content
    runs = None
    plain = ""
    content_for_preview: Any = None

    if isinstance(raw_content, dict):
        if "runs" in raw_content:
            runs = raw_content.get("runs", [])
            plain = "".join(str(r.get("text", "")) for r in runs)
            content_for_preview = raw_content
        elif "text" in raw_content:
            plain = raw_content.get("text", "")
            content_for_preview = raw_content
        elif "equation" in raw_content:
            plain = raw_content.get("equation", "")
            content_for_preview = raw_content
        else:
            # Complex custom element (QuadraticPlot, GridBoard, Solid3D, etc.)
            # Keep the full spec dict for the preview renderer to interpret
            content_for_preview = raw_content
            # For display / fallback use formula or a short label if present
            plain = raw_content.get("formula") or raw_content.get("text") or str(el.type)
    elif isinstance(raw_content, list):
        plain = "".join(str(x) for x in raw_content)
        content_for_preview = raw_content
    elif raw_content is not None:
        plain = str(raw_content)
        content_for_preview = raw_content

    # Always keep the original spec available under "spec" for custom types
    if content_for_preview is None:
        content_for_preview = raw_content

    layout = el.layout
    layout_dict = layout.to_dict() if layout is not None else {
        "width": 0.0, "height": 0.0, "wrap": False, "align": "center",
        "margin_top": 0.0, "margin_bottom": 0.0, "margin_left": 0.0, "margin_right": 0.0,
    }

    item: dict[str, Any] = {
        "id": el.id,
        "type": el.type,
        "content": plain,
        "spec": content_for_preview,   # full spec for custom types (QuadraticPlot etc.)
        "x": float(el.canvas_position[0]),
        "y": float(el.canvas_position[1]),
        "z": float(el.canvas_position[2]),
        "canvas_position": list(el.canvas_position),
        # Phase 1: include world transform for the 3D space model (backward compat)
        "world_transform": getattr(el, "world_transform", None) and el.world_transform.to_dict() or None,
        "width": float(layout_dict.get("width", 0)),
        "height": float(layout_dict.get("height", 0)),
        "layout": layout_dict,
        "align": layout_dict.get("align", "center"),
        "margin_top": float(layout_dict.get("margin_top", 0)),
        "margin_bottom": float(layout_dict.get("margin_bottom", 0)),
        "is_math": el.type == "MathTex",
        "is_3d": el.type in ("ThreeDGraph", "Surface", "Solid3D"),
        "pitch": getattr(el, "pitch", None),
        "yaw": getattr(el, "yaw", None),
        "static_phi": getattr(el, "static_phi", None),
        "static_theta": getattr(el, "static_theta", None),
        "static_scale": getattr(el, "static_scale", 1.0),
        "static_opacity": getattr(el, "static_opacity", 1.0),
        "auto_focus": getattr(el, "auto_focus", True),
        "flex_group": getattr(el, "flex_group", None),
    }
    if runs:
        item["runs"] = runs
    if content_for_preview and not isinstance(content_for_preview, (str, list)):
        # also keep raw content object for preview renderers
        item["raw_content"] = content_for_preview
    if el.entry_animation:
        item["entry_animation"] = {
            "type": el.entry_animation.type,
            "run_time": el.entry_animation.run_time,
            "kwargs": el.entry_animation.kwargs or {},
        }
    if el.state_behavior:
        item["state_behavior"] = {
            "type": el.state_behavior.type,
            "params": el.state_behavior.params or {},
        }
    return item


def _serialize_timeline_action(item: Any) -> dict[str, Any]:
    """Serialize any TimelineItem for the manim-web replay engine. Phase 3 support."""
    from canvas.dsl import CameraKeyframe, CanvasElement

    if isinstance(item, CanvasElement):
        base = _serialize_preview_element(item)
        base["kind"] = "element"
        return base
    if isinstance(item, CameraKeyframe):
        d = item.to_dict()
        d["kind"] = "CameraKeyframe"
        return d
    # Special commands
    if hasattr(item, "to_dict"):
        d = item.to_dict()
        # Normalize kind
        kind = d.get("type", type(item).__name__)
        d = dict(d)
        d["kind"] = kind
        return d
    return {"kind": "unknown", "raw": str(item)}


def handle_get_preview_data(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    lazy.ensure_engine_loaded(events)
    from ..workspace_project import (
        instantiate_scene,
        resolve_workspace,
        workspace_context,
    )
    # Canvas classes for serializers (loaded by ensure)
    from canvas.dsl import CameraKeyframe, CanvasElement

    if params.get("workspace"):
        workspace = resolve_workspace(params)
        attempted_scene = params.get("scene")
        try:
            scene_name = _resolve_scene_or_error(workspace, attempted_scene)
            with workspace_context(workspace):
                inst = instantiate_scene(workspace, scene_name, path=params.get("path"))
            dsl = inst.dsl
        except Exception as e:
            # Do not fall back to _require_dsl if this was a workspace call
            raise ProtocolError(
                "PREVIEW_LOAD_FAILED",
                f"Failed to load scene for preview (workspace={workspace}, scene={attempted_scene}): {e}"
            ) from e
    else:
        dsl = _require_dsl(params)
    # Rich data for sophisticated manim-web 1-1 preview
    full_timeline = [_serialize_timeline_action(it) for it in getattr(dsl, "timeline", [])]
    elements = [a for a in full_timeline if a.get("kind") == "element"]

    settings = dsl.canvas_settings
    return {
        "elements": elements,
        "timeline": full_timeline,           # ordered actions (elements + CameraMove + flex etc.)
        "frame_width": settings.frame_width,
        "frame_height": settings.frame_height,
        "title": getattr(settings, "title", None),
        "orientation": getattr(settings, "orientation", "portrait"),
        "background_color": getattr(settings, "background_color", "#111111"),
        # Phase 1
        "coordinate_system": getattr(settings, "coordinate_system", "sheet"),
        # Phase 5/7: object graph + observations for full 3D preview
        "root_objects": [o.to_dict() for o in getattr(dsl, "root_objects", [])],
        "root_tape": dsl.root_tape.to_dict() if getattr(dsl, "root_tape", None) else None,
        "observations": [a for a in full_timeline if a.get("kind") in ("CameraMove", "CameraKeyframe", "CameraFocus", "CameraInspect")],
    }


COMMANDS: dict[str, HandlerFn] = {
    "ping": handle_ping,
    "get_status": handle_get_status,
    "configure_assets": handle_configure_assets,
    "retrieve": handle_retrieve,
    "list_scenes": handle_list_scenes,
    "lint_project": handle_lint_project,
    "check_project": handle_check_project,
    "render_project": handle_render_project,
    "validate_dsl": handle_validate_dsl,
    "estimate_duration": handle_estimate_duration,
    "get_preview_data": handle_get_preview_data,
    "compile_preview": handle_compile_preview,
    "render": handle_render,
    "export_sheet": handle_export_sheet,
    "cut_reels": handle_cut_reels,
}


def dispatch(command: str, params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    handler = COMMANDS.get(command)
    if handler is None:
        raise ProtocolError("UNKNOWN_COMMAND", f"Unknown command: {command}")
    return handler(params, events)