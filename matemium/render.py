"""Render pipeline — project-aware, isolated outputs per video."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import replace
from pathlib import Path
from typing import Type

from manim import tempconfig

from canvas import CanvasScene, SheetDSL
from canvas.dsl import CanvasSettings

from .manim_progress import ManimProgressReporter, ProgressCallback, make_progress_renderer
from .paths import output_media_dir

_PARTIAL_SEGMENT = "partial_movie_files"
# Bumped when render config semantics change (desktop sidecar must be rebuilt).
RENDER_PIPELINE_ID = "partial-movie-progress-v1"


def normalize_orientation(value: str | None) -> str:
    """Map UI / IPC values to ``portrait`` or ``landscape``."""
    name = (value or "portrait").lower().strip().replace("-", "_").replace(":", "_")
    if name in {"portrait", "reels", "vertical", "9_16", "9x16"}:
        return "portrait"
    if name in {"landscape", "youtube", "horizontal", "16_9", "16x9"}:
        return "landscape"
    raise ValueError(f"unsupported orientation: {value!r}")


def apply_render_orientation(dsl: SheetDSL, orientation: str | None) -> SheetDSL:
    """Apply a render-time aspect ratio without editing scenes.py on disk."""
    target = normalize_orientation(orientation)
    current = dsl.canvas_settings
    if current.orientation == target:
        return dsl

    factory = CanvasSettings.for_youtube if target == "landscape" else CanvasSettings.for_reels
    settings = factory(
        title=current.title,
        background_color=current.background_color,
    )
    return replace(dsl, canvas_settings=settings)


def render_quality_config(
    quality: str,
    *,
    base_width: int,
    base_height: int,
) -> dict:
    """Map CLI quality presets to Manim tempconfig fields.

    Profiles:
    - ``fast_preview`` — quickest iteration (quarter resolution, 10 fps)
    - ``preview`` — fast iteration (half resolution, 15 fps)
    - ``draft`` / ``low`` — default dev renders
    - ``medium`` — sharper draft
    - ``high`` / ``final`` — production output (60 fps)
    """
    name = (quality or "low").lower().replace("-", "_")
    # Do not set Manim's ``quality`` preset here — presets like ``low_quality`` force
    # 854×480 landscape and ignore portrait pixel_width/height from CanvasSettings.
    profiles = {
        "fast_preview": {"frame_rate": 10, "scale": 0.25},
        "preview": {"frame_rate": 15, "scale": 0.5},
        "draft": {"frame_rate": 30, "scale": 0.75},
        "low": {"frame_rate": 30, "scale": 1.0},
        "medium": {"frame_rate": 30, "scale": 1.0},
        "high": {"frame_rate": 60, "scale": 1.0},
        "final": {"frame_rate": 60, "scale": 1.0},
    }
    profile = profiles.get(name, profiles["low"])
    scale = float(profile["scale"])
    pw = max(2, int(round(base_width * scale)))
    ph = max(2, int(round(base_height * scale)))
    # Even dimensions help some encoders.
    if pw % 2:
        pw += 1
    if ph % 2:
        ph += 1
    return {
        "frame_rate": int(profile["frame_rate"]),
        "pixel_width": pw,
        "pixel_height": ph,
    }


def _is_final_video(path: Path) -> bool:
    return path.is_file() and _PARTIAL_SEGMENT not in path.parts


def find_rendered_video(
    media: Path,
    *,
    scene_name: str,
    output_name: str | None = None,
    timeout_s: float = 30.0,
) -> Path:
    """Locate the final Manim MP4, excluding partial segment files."""
    stem = output_name or scene_name
    deadline = time.monotonic() + timeout_s

    while time.monotonic() < deadline:
        videos_root = media / "videos"
        candidates: list[Path] = []
        if videos_root.is_dir():
            candidates = [
                path
                for path in videos_root.rglob("*.mp4")
                if _is_final_video(path)
            ]

        exact = [path for path in candidates if path.stem == stem]
        if exact:
            return max(exact, key=lambda path: path.stat().st_mtime)

        named = [path for path in candidates if stem in path.stem]
        if named:
            return max(named, key=lambda path: path.stat().st_mtime)

        if candidates:
            return max(candidates, key=lambda path: path.stat().st_mtime)

        time.sleep(0.25)

    raise FileNotFoundError(
        f"No final render MP4 for {stem!r} under {media / 'videos'} "
        f"(waited {timeout_s:.0f}s)"
    )


def publish_preview_video(source: Path, preview_dir: Path, scene_name: str) -> Path:
    """Copy the rendered MP4 to a stable top-level preview path."""
    if not source.is_file():
        raise FileNotFoundError(f"render output missing: {source}")
    if source.stat().st_size == 0:
        raise OSError(f"render output is empty: {source}")

    preview_dir.mkdir(parents=True, exist_ok=True)
    preview = preview_dir / f"{scene_name}.mp4"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(preview),
            ],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        shutil.copy2(source, preview)
    return preview


def render_sheet(
    dsl: SheetDSL,
    *,
    project: str = "default",
    scene_name: str = "CanvasScene",
    output_name: str | None = None,
    quality: str = "low",
    resolution: tuple[int, int] | None = None,
    media_dir: str | Path | None = None,
    on_progress: ProgressCallback | None = None,
    animation_estimate: int | None = None,
) -> Path:
    """Render a SheetDSL; writes to outputs/<project>/media/ by default."""
    settings = dsl.canvas_settings
    pw, ph = resolution if resolution else settings.get_manim_resolution()
    media = Path(media_dir) if media_dir else output_media_dir(project)

    config = settings.get_manim_config_dict()
    config.update(render_quality_config(quality, base_width=pw, base_height=ph))
    if resolution:
        config["pixel_width"] = pw
        config["pixel_height"] = ph
    config["media_dir"] = str(media)
    config["disable_caching"] = False
    config["flush_cache"] = False
    if output_name:
        config["output_file"] = output_name

    print(f"[matemium] project: {project}")
    print(f"[matemium] format: {settings.orientation} ({settings.aspect_ratio})")
    print(f"[matemium] quality: {quality} ({config['frame_rate']} fps)")
    print(f"[matemium] resolution: {config['pixel_width']}x{config['pixel_height']}")
    print(f"[matemium] output: {media}")

    renderer = None
    if on_progress is not None:
        from .play_count import resolve_animation_count

        estimate = animation_estimate or resolve_animation_count(dsl)
        reporter = ManimProgressReporter(on_progress, animation_estimate=estimate)
        renderer = make_progress_renderer(reporter)
        on_progress(pct=0.0, message="Starting Manim render", section="animate")

    with tempconfig(config):
        # Always render via CanvasScene(dsl) so Manim honors media_dir from tempconfig.
        scene = CanvasScene(dsl=dsl, renderer=renderer)
        scene.render()

    if on_progress is not None and renderer is not None:
        reporter = renderer._reporter
        reporter.on_render_finished(renderer)
        total = renderer.num_plays
        on_progress(
            pct=1.0,
            message="Render complete",
            section="animate",
            partial_index=total,
            partial_total=total,
        )
    elif on_progress is not None:
        on_progress(pct=1.0, message="Render complete", section="animate")

    video_path = find_rendered_video(
        media,
        scene_name=scene_name,
        output_name=output_name,
    )
    print(f"[matemium] video: {video_path}")
    return video_path


def render_scene_class(
    scene_cls: Type[CanvasScene],
    *,
    project: str,
    output_name: str | None = None,
    quality: str = "low",
    resolution: tuple[int, int] | None = None,
    media_dir: str | Path | None = None,
    on_progress: ProgressCallback | None = None,
    animation_estimate: int | None = None,
) -> Path:
    """Instantiate a project scene class and render it."""
    instance = scene_cls()
    return render_sheet(
        instance.dsl,
        project=project,
        scene_name=scene_cls.__name__,
        output_name=output_name or scene_cls.__name__,
        quality=quality,
        resolution=resolution,
        media_dir=media_dir,
        on_progress=on_progress,
        animation_estimate=animation_estimate,
    )
