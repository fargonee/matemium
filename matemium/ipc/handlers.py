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


_EDIT_REQUEST_TERMS = (
    "add",
    "change",
    "delete",
    "edit",
    "fix",
    "implement",
    "modify",
    "move",
    "patch",
    "remove",
    "rename",
    "replace",
    "revert",
    "update",
)


_EVIDENCE_REQUEST_TERMS = (
    "animation",
    "code",
    "does",
    "explain",
    "generate",
    "scene",
    "show",
    "summarize",
    "what",
)


_WORKSPACE_TASK_TERMS = (
    "animation",
    "helpers.py",
    "brief",
    "build",
    "canvas",
    "check",
    "class",
    "code",
    "compile",
    "dsl",
    "file",
    "graph",
    "lint",
    "project",
    "render",
    "scene",
    "scenes.py",
    "workspace",
)


def _looks_like_workspace_edit_request(text: str) -> bool:
    lowered = f" {text.lower()} "
    return any(f" {term} " in lowered for term in _EDIT_REQUEST_TERMS)


def _looks_like_workspace_evidence_request(text: str) -> bool:
    lowered = f" {text.lower()} "
    return any(f" {term} " in lowered for term in _EVIDENCE_REQUEST_TERMS)


def _looks_like_workspace_task_request(text: str) -> bool:
    lowered = f" {text.lower()} "
    return (
        _looks_like_workspace_edit_request(text)
        or _looks_like_workspace_evidence_request(text)
        or any(f" {term} " in lowered for term in _WORKSPACE_TASK_TERMS)
        or "scenes.py" in lowered
        or "helpers.py" in lowered
    )


def _local_chat_needs_workspace_context(prompt: str, scenes_excerpt: str) -> bool:
    """Avoid feeding large workspace context into plain conversational turns."""
    if not scenes_excerpt:
        return False
    if "--- REFERENCE FILE:" in scenes_excerpt:
        return True
    return _looks_like_workspace_task_request(prompt)


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
    
    # Base files to index
    files = list(
        params.get("files")
        or [
            "scenes.py",
            "helpers.py",
            "brief/passport.json",
            "brief/description.md",
            "brief/tapes/main.md",
            "brief/orchestration.md",
            "brief/roadmap.json",
            "brief/tts-narration.md",
            "brief/tts-narration-style.md",
            "brief/audio-description.md",
            "brief/custom-narration.md",
            "brief/transcript.md",
            "brief/timestamps.json",
        ]
    )
    if workspace:
        tapes_dir = workspace / "brief" / "tapes"
        if tapes_dir.is_dir():
            for tape_path in sorted(tapes_dir.glob("*.md")):
                relative = tape_path.relative_to(workspace).as_posix()
                if relative not in files:
                    files.append(relative)
    
    # Auto-scan references/ directory if it exists and append those files for indexing
    if workspace:
        ref_dir = workspace / "references"
        if ref_dir.is_dir():
            for f_path in ref_dir.rglob("*"):
                if f_path.is_file() and f_path.suffix.lower() in (".pdf", ".md", ".txt", ".tex", ".py", ".json", ".csv"):
                    try:
                        rel_path = f_path.relative_to(workspace)
                        files.append(str(rel_path))
                    except Exception:
                        pass

    retriever = get_retriever(workspace)
    
    results = []
    
    # 1. Separate reference files and codebase files
    reference_files = []
    codebase_files = []
    for f in files:
        if f.startswith("references/") or f.startswith("references\\"):
            reference_files.append(f)
        else:
            codebase_files.append(f)
            
    # 2. Extract and parse reference files using autodetected chunkers (guaranteed context)
    for f in reference_files:
        p = workspace / f if workspace else Path(f)
        if p.is_file():
            try:
                if p.suffix.lower() == ".pdf":
                    import subprocess
                    text = subprocess.check_output(["pdftotext", str(p), "-"], text=True, errors="ignore")
                else:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    
                from ..intelligence.chunking import autodetect_and_chunk
                file_chunks = autodetect_and_chunk(text, file_path=p)
                # Cap maximum chunks to prevent context overflow (e.g. max 25 chunks per reference)
                for fc in file_chunks[:25]:
                    results.append({
                        "file": f,
                        "chunk": fc["text"],
                        "score": 1.0,  # guaranteed score
                    })
            except Exception:
                pass
                
    # 3. Perform semantic retrieval on the approved code and brief files.
    if codebase_files:
        if hasattr(retriever, "index_files"):
            try:
                retriever.index_files(codebase_files, events=events)
            except Exception:
                pass
        elif hasattr(retriever, "load_files"):
            try:
                retriever.load_files(codebase_files)
            except Exception:
                pass
                
        semantic_results = retriever.retrieve(query, top_k=top_k)
        for r in semantic_results:
            results.append({
                "file": r.get("file"),
                "chunk": r.get("chunk"),
                "score": r.get("score", 0.85)
            })

    return {"query": query, "results": results, "top_k": top_k}


def handle_upload_reference(params: dict[str, Any], events: EventEmitter) -> dict[str, Any]:
    """Uploads a reference document into the workspace references folder and indexes it.

    Params:
      workspace: The root path of the workspace (resolved dynamically).
      file_name: The name of the file to save.
      file_content_base64: Optional base64 encoded string (for binary or any files).
      file_content_text: Optional plain text string (for markdown/txt notes).
    """
    workspace = _require_workspace(params)
    file_name = str(params.get("file_name", "")).strip()
    if not file_name:
        raise ValueError("file_name is required")

    # Sanitize file name to prevent path traversal
    file_name = Path(file_name).name

    ref_dir = workspace / "references"
    ref_dir.mkdir(parents=True, exist_ok=True)
    target_path = ref_dir / file_name

    import base64
    if b64_content := params.get("file_content_base64"):
        content_bytes = base64.b64decode(str(b64_content))
        target_path.write_bytes(content_bytes)
    elif text_content := params.get("file_content_text"):
        target_path.write_text(str(text_content), encoding="utf-8")
    else:
        raise ValueError("Either file_content_base64 or file_content_text must be provided")

    # Trigger immediate indexing of the new reference file
    retriever = get_retriever(workspace)
    relative_file_name = f"references/{file_name}"
    
    indexed = False
    if hasattr(retriever, "index_files"):
        try:
            retriever.index_files([relative_file_name], force=True, events=events)
            indexed = True
        except Exception as e:
            print(f"[RAG] Failed to index new reference: {e}")
    elif hasattr(retriever, "load_files"):
        try:
            retriever.load_files([relative_file_name])
            indexed = True
        except Exception as e:
            print(f"[RAG] Failed to load new reference: {e}")

    return {
        "status": "success",
        "file_name": file_name,
        "path": str(target_path.resolve()),
        "indexed": indexed
    }


def handle_list_references(params: dict[str, Any], _events: EventEmitter) -> dict[str, Any]:
    """Lists all uploaded reference documents in the workspace references folder."""
    workspace = _require_workspace(params)
    ref_dir = workspace / "references"
    
    files = []
    if ref_dir.is_dir():
        for p in ref_dir.iterdir():
            if p.is_file():
                files.append(p.name)
                
    return {"status": "success", "references": sorted(files)}


def handle_delete_reference(params: dict[str, Any], _events: EventEmitter) -> dict[str, Any]:
    """Deletes a reference document from the references folder."""
    workspace = _require_workspace(params)
    file_name = str(params.get("file_name", "")).strip()
    if not file_name:
        raise ValueError("file_name is required")
        
    file_name = Path(file_name).name
    target_path = workspace / "references" / file_name
    
    deleted = False
    if target_path.is_file():
        target_path.unlink()
        deleted = True
        
    return {"status": "success", "file_name": file_name, "deleted": deleted}


def handle_get_reference_content(params: dict[str, Any], _events: EventEmitter) -> dict[str, Any]:
    """Retrieves the full extracted text content of an uploaded reference document."""
    workspace = _require_workspace(params)
    file_name = str(params.get("file_name", "")).strip()
    if not file_name:
        raise ValueError("file_name is required")
        
    file_name = Path(file_name).name
    p = workspace / "references" / file_name
    
    if not p.is_file():
        raise FileNotFoundError(f"Reference file not found: {p}")
        
    content = ""
    try:
        if p.suffix.lower() == ".pdf":
            import subprocess
            content = subprocess.check_output(["pdftotext", str(p), "-"], text=True, errors="ignore")
        else:
            content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        content = f"Error reading reference content: {e}"
        
    return {"status": "success", "file_name": file_name, "content": content}


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


def handle_update_llm_config(params: dict[str, Any], _events: EventEmitter) -> dict[str, Any]:
    """Lightweight: tell sidecar whether to use a local GGUF LLM and its path.

    Example: {"use_local_llm": true, "model_path": "/path/to/models/qwen.gguf"}
    """
    import os
    use_local = params.get("use_local_llm", False)
    model_path = params.get("model_path", "")
    previous_model_path = os.environ.get("MATEMIUM_LOCAL_LLM_MODEL_PATH", "")

    os.environ["MATEMIUM_USE_LOCAL_LLM"] = "true" if use_local else "false"
    if model_path:
        if previous_model_path and str(model_path) != previous_model_path:
            from ..agent.local_runner import unload_cached_model

            unload_cached_model()
        os.environ["MATEMIUM_LOCAL_LLM_MODEL_PATH"] = str(model_path)

    return {"ok": True, "configured": list(params.keys())}


def _generate_local_messages(runner: Any, messages: list[dict[str, str]]) -> str:
    """Run one local inference call for either chat or an agent turn."""
    if runner.is_ollama_running():
        return runner._generate_via_ollama_messages(messages)

    if not runner.model_path or not runner.model_path.is_file():
        raise FileNotFoundError(
            f"Local GGUF model path not found or invalid: {runner.model_path}. "
            "Ensure the model is fully downloaded via Settings."
        )
    from ..agent.llm_worker import generate_in_worker

    return generate_in_worker(
        model_path=runner.model_path,
        context_window=runner.context_window,
        messages=messages,
    )


def _split_reference_context(scenes_excerpt: str) -> tuple[str, str]:
    if "--- REFERENCE FILE:" not in scenes_excerpt:
        return "", scenes_excerpt
    parts = scenes_excerpt.split("// --- workspace context below ---", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return scenes_excerpt.strip(), ""


def _handle_aider_chat(
    params: dict[str, Any],
    *,
    user_prompt: str,
    scenes_excerpt: str,
) -> dict[str, Any]:
    import uuid

    from ..agent.aider_runner import AiderAgentRunner, AiderUnavailableError
    from ..agent.local_runner import LocalInferenceRunner

    workspace = _require_workspace(params)
    use_local_model = bool(params.get("use_local_llm"))
    provider = str(params.get("llm_provider") or "")
    model = str(params.get("model") or "")
    openrouter_api_key = str(params.get("openrouter_api_key") or "")
    openai_api_key = str(params.get("openai_api_key") or "")
    groq_api_key = str(params.get("groq_api_key") or "")
    xai_api_key = str(params.get("xai_api_key") or "")
    cerebras_api_key = str(params.get("cerebras_api_key") or "")
    github_api_key = str(params.get("github_api_key") or "")
    mistral_api_key = str(params.get("mistral_api_key") or "")
    gemini_api_key = str(params.get("gemini_api_key") or "")
    if use_local_model and not model:
        model = LocalInferenceRunner().model_name

    references, current_scene_context = _split_reference_context(scenes_excerpt)
    extra_context = []
    if references:
        extra_context.append(f"Reference documents:\n{references}")
    if current_scene_context:
        extra_context.append(
            "Current editor buffer supplied by the UI. Treat files on disk as the "
            f"editable source of truth:\n```python\n{current_scene_context}\n```"
        )

    agent_trace: list[dict[str, Any]] = []
    try:
        env = {}
        provider_name = provider.strip().lower()
        if not use_local_model:
            if provider_name == "openrouter" and openrouter_api_key:
                env["OPENROUTER_API_KEY"] = openrouter_api_key
            elif provider_name == "openai" and openai_api_key:
                env["OPENAI_API_KEY"] = openai_api_key
            elif provider_name == "groq" and groq_api_key:
                env["GROQ_API_KEY"] = groq_api_key
            elif provider_name == "xai" and xai_api_key:
                env["XAI_API_KEY"] = xai_api_key
            elif provider_name == "cerebras" and cerebras_api_key:
                env["CEREBRAS_API_KEY"] = cerebras_api_key
            elif provider_name == "github" and github_api_key:
                env["GITHUB_TOKEN"] = github_api_key
            elif provider_name == "mistral" and mistral_api_key:
                env["MISTRAL_API_KEY"] = mistral_api_key
            elif provider_name == "gemini" and gemini_api_key:
                env["GEMINI_API_KEY"] = gemini_api_key
        runner = AiderAgentRunner(env=env)
        result = runner.run(
            workspace=workspace,
            prompt=user_prompt,
            model=model or None,
            provider=provider or None,
            use_local_model=use_local_model,
            extra_context=extra_context,
        )
        response_text = result.output or "Aider completed the workspace edit."
        resolved_model = result.model
        agent_trace.extend(result.trace)
        edited_files = {
            str(file)
            for event in result.trace
            for file in (
                (event.get("details") or {}).get("files", [])
                if isinstance(event.get("details"), dict)
                else []
            )
        }
        if edited_files.intersection({"scenes.py", "helpers.py"}):
            for attempt in range(4):
                check = check_project(workspace)
                agent_trace.append({
                    "type": "verification_completed",
                    "summary": "Project check passed." if check.get("ok") else f"Project check failed (recovery {attempt}/3).",
                    "details": {"ok": bool(check.get("ok")), "errors": check.get("errors", [])},
                })
                if check.get("ok"):
                    break
                if attempt == 3:
                    response_text = (
                        "I could not make the scene pass the local project check after three "
                        "targeted repairs. I stopped without claiming this authoring phase is complete."
                    )
                    break
                diagnostics = check.get("errors") or []
                fix_result = runner.run(
                    workspace=workspace,
                    prompt=(
                        "The local Matemium project check failed after your edit. Fix these exact "
                        f"diagnostics, preserve approved brief decisions, and do not ask the user to debug them:\n{diagnostics}"
                    ),
                    model=model or None,
                    provider=provider or None,
                    use_local_model=use_local_model,
                    extra_context=extra_context,
                )
                response_text = fix_result.output or response_text
                agent_trace.extend(fix_result.trace)
    except AiderUnavailableError as exc:
        if use_local_model:
            response_text = (
                "Local autonomous editing is not ready yet. Switch to an external "
                "model for this edit, or wait for the local agent provider to become ready."
            )
        else:
            response_text = (
                "Autonomous editing is not ready yet. Matemium is preparing the "
                "managed Aider runtime; try again after the agent runtime is ready."
            )
        agent_trace.append({
            "type": "error",
            "summary": "Aider runtime unavailable",
            "details": {"error": str(exc)},
        })
        resolved_model = model or ("local" if use_local_model else "external")
    except Exception as exc:
        response_text = "Aider could not complete the agent task. Review the agent trace for details."
        agent_trace.append({
            "type": "error",
            "summary": "Aider task failed",
            "details": {"error": str(exc)},
        })
        resolved_model = model or ("local" if use_local_model else "external")

    return {
        "id": str(uuid.uuid4()),
        "message": {
            "role": "assistant",
            "content": response_text,
        },
        "code_edit": None,
        "model": resolved_model,
        "stub": False,
        "agent_runtime_version": "aider-v1",
        "provider": "aider-local" if use_local_model else (provider or "aider"),
        "billing_mode": "local" if use_local_model else "byo_external",
        "request_id": str(uuid.uuid4()),
        "agent_trace": agent_trace,
    }


def handle_prepare_agent_runtime(
    _params: dict[str, Any], _events: EventEmitter
) -> dict[str, Any]:
    import uuid

    from ..agent.aider_runner import AiderAgentRunner

    try:
        executable = AiderAgentRunner(timeout_seconds=900.0).prepare_runtime()
        return {
            "ok": True,
            "runtime": "aider-v1",
            "executable": executable,
            "request_id": str(uuid.uuid4()),
        }
    except Exception as exc:
        return {
            "ok": False,
            "runtime": "aider-v1",
            "error": str(exc),
            "request_id": str(uuid.uuid4()),
        }


def handle_local_chat(params: dict[str, Any], _events: EventEmitter) -> dict[str, Any]:
    """Offline local LLM chat completion using LocalInferenceRunner."""
    import uuid
    from ..agent.local_runner import LocalInferenceRunner
    
    messages = params.get("messages", [])
    scenes_excerpt = params.get("scenes_excerpt", "")
    user_prompt = next(
        (str(msg.get("content", "")) for msg in reversed(messages) if msg.get("role") == "user"),
        "",
    )

    if (
        params.get("use_autonomous_agent")
        and params.get("workspace")
    ):
        return _handle_aider_chat(
            params,
            user_prompt=user_prompt,
            scenes_excerpt=scenes_excerpt,
        )

    full_messages = []
    
    # 1. Read scene authoring system prompt
    from ..paths import ROOT
    prompt_path = ROOT / "shared" / "prompts" / "scene-authoring-system.txt"
    manager_prompt_path = ROOT / "shared" / "prompts" / "project-manager-system.txt"
    system_prompt = ""
    if prompt_path.is_file():
        try:
            system_prompt = prompt_path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    if not system_prompt:
        system_prompt = (
            "You are Ferganus, a Matemium assistant. Users author animations in scenes.py "
            "using CanvasBuilder and CanvasScene — not raw Manim. Respond with concise "
            "guidance and propose concrete Python edits when asked."
        )
    if manager_prompt_path.is_file():
        try:
            manager_prompt = manager_prompt_path.read_text(encoding="utf-8").strip()
            if manager_prompt:
                system_prompt = f"{manager_prompt}\n\n{system_prompt}"
        except Exception:
            pass

    include_workspace_context = _local_chat_needs_workspace_context(
        user_prompt, scenes_excerpt
    )
    if not include_workspace_context:
        system_prompt = (
            f"{system_prompt}\n\n"
            "Casual-chat constraint: answer directly and briefly. Do not ask for "
            "project context unless it is needed. For greetings, use available "
            "project context to give a natural status pulse and a concrete next step."
        )
    full_messages.append({"role": "system", "content": system_prompt})

    # 2. Append scenes excerpt as system context if provided
    if scenes_excerpt and include_workspace_context:
        if "--- REFERENCE FILE:" in scenes_excerpt:
            parts = scenes_excerpt.split("// --- workspace context below ---")
            if len(parts) == 2:
                references_part = parts[0].strip()
                scenes_part = parts[1].strip()
                full_messages.append({
                    "role": "system",
                    "content": f"Reference documents provided by the user:\n{references_part}"
                })
                if scenes_part:
                    full_messages.append({
                        "role": "system",
                        "content": f"Current scenes.py:\n```python\n{scenes_part}\n```"
                    })
            else:
                full_messages.append({
                    "role": "system",
                    "content": f"Workspace context and reference files:\n{scenes_excerpt}"
                })
        else:
            full_messages.append({
                "role": "system",
                "content": f"Current scenes.py:\n```python\n{scenes_excerpt}\n```"
            })

    # 3. Append conversation history
    for msg in messages:
        if msg.get("role") != "system":
            full_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

    # 4. Initialize LocalInferenceRunner
    runner = LocalInferenceRunner()
    
    response_text = _generate_local_messages(runner, full_messages)

    # 6. Normalize high-confidence small edits before parsing model-authored blocks.
    code_edit = None
    from ..agent.edit_normalization import has_edit_proposal, normalize_model_edit
    normalized = normalize_model_edit(response_text, scenes_excerpt)
    if normalized:
        code_edit = {
            "description": normalized.description,
            "search": normalized.search,
            "replace": normalized.replace,
            "full_file": normalized.full_file,
        }
        response_text = "Prepared a validated, bounded edit from the model proposal. Review the diff below and choose Apply to editor; no file has been changed yet."
    elif has_edit_proposal(response_text):
        response_text = "The local model proposed a code change, but it was not safely applicable to the current file: its precondition was missing or ambiguous, or the change exceeded the bounded-edit policy. Nothing was changed. Ask for a smaller edit."

    model_name = runner.model_path.name if runner.model_path else runner.model_name
    return {
        "id": str(uuid.uuid4()),
        "message": {
            "role": "assistant",
            "content": response_text
        },
        "code_edit": code_edit,
        "model": model_name,
        "stub": False,
        "agent_runtime_version": None,
        "provider": "local",
        "billing_mode": "local",
        "request_id": str(uuid.uuid4()),
        "agent_trace": [],
    }


COMMANDS: dict[str, HandlerFn] = {
    "ping": handle_ping,
    "get_status": handle_get_status,
    "configure_assets": handle_configure_assets,
    "update_llm_config": handle_update_llm_config,
    "prepare_agent_runtime": handle_prepare_agent_runtime,
    "local_chat": handle_local_chat,
    "retrieve": handle_retrieve,
    "upload_reference": handle_upload_reference,
    "list_references": handle_list_references,
    "delete_reference": handle_delete_reference,
    "get_reference_content": handle_get_reference_content,
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
