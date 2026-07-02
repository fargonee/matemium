"""Reel Cutter for Matemium.

Splits a long rendered vertical video into short 9:16 social reels,
aligned to natural CameraMove boundaries in the sheet.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any


class ReelCutter:
    """Cuts a long canvas video into multiple short reels.

    Can either:
    1. Use an externally provided cut manifest (list of {"time": seconds, "label": "..."})
    2. Generate a manifest by simulating the DSL timeline (recommended).
    """

    def __init__(self, segment_duration: float = 55.0):
        self.segment_duration = segment_duration

    def generate_manifest_from_dsl(self, dsl: "SheetDSL") -> List[Dict[str, Any]]:
        """Walk the timeline and accumulate time at CameraMove or CameraKeyframe events.

        These become the chapter / reel boundary points.
        Phase 8: supports mixed 3D + tape-scroll observation types.
        Includes mode hint for mixed scenes.
        """
        from .dsl import CameraMove, CameraKeyframe

        manifest: List[Dict[str, Any]] = []
        cumulative = 0.0
        for item in getattr(dsl, "timeline", []):
            if isinstance(item, CameraMove):
                cumulative += item.run_time
                manifest.append({
                    "time": round(cumulative, 3),
                    "label": item.id,
                    "target_y": item.target_position[1] if hasattr(item, 'target_position') else 0,
                })
            elif isinstance(item, CameraKeyframe):
                # For tape scrolls, use local_y as target_y; for world, 0 or extract
                dur = getattr(item, 'duration', getattr(item, 'run_time', 0))
                cumulative += dur
                tgt = getattr(item, 'target', None)
                ty = 0
                mode = "3d"
                if tgt and hasattr(tgt, 'local_y'):
                    ty = tgt.local_y
                    mode = "tape_scroll"
                elif tgt and isinstance(tgt, dict) and 'local_y' in tgt:
                    ty = tgt['local_y']
                    mode = "tape_scroll"
                elif tgt and hasattr(tgt, 'object_id'):
                    mode = "3d_object"
                manifest.append({
                    "time": round(cumulative, 3),
                    "label": item.id,
                    "target_y": ty,
                    "mode": mode,
                })
        return manifest

    def cut(
        self,
        input_video: Path,
        output_dir: Path,
        manifest: List[Dict[str, Any]] | None = None,
        reel_prefix: str = "reel_",
    ) -> List[Path]:
        """Perform the actual splitting using ffmpeg (stream copy where possible)."""
        output_dir.mkdir(parents=True, exist_ok=True)

        if not manifest:
            raise ValueError("A cut manifest (list of time points) is required")

        # Ensure we have an end marker
        try:
            probe = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", str(input_video)
            ]
            out = subprocess.check_output(probe, stderr=subprocess.DEVNULL)
            total = float(json.loads(out)["format"]["duration"])
        except Exception:
            total = manifest[-1]["time"] + 10 if manifest else 300

        points = list(manifest)
        points.append({"time": total, "label": "end"})

        produced: List[Path] = []
        start = 0.0
        reel_num = 1

        for point in points:
            end = float(point["time"])
            while (end - start) > self.segment_duration + 0.5:
                cut_end = start + self.segment_duration
                out_path = output_dir / f"{reel_prefix}{reel_num:03d}.mp4"
                self._ffmpeg_cut(input_video, start, cut_end, out_path)
                produced.append(out_path)
                start = cut_end
                reel_num += 1

            if (end - start) > 0.8:
                out_path = output_dir / f"{reel_prefix}{reel_num:03d}.mp4"
                self._ffmpeg_cut(input_video, start, end, out_path)
                produced.append(out_path)
                reel_num += 1
            start = end

        return produced

    def _ffmpeg_cut(self, src: Path, ss: float, to: float, dst: Path):
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{ss:.3f}",
            "-to", f"{to:.3f}",
            "-i", str(src),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            str(dst),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def save_manifest(self, manifest: List[Dict[str, Any]], path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
