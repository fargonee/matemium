use std::fs;
use std::hash::{Hash, Hasher};
use std::path::{Path, PathBuf};
use std::process::Command;

use serde::Deserialize;

use crate::workspace::AppPaths;

const PARTIAL_MAX_BYTES: u64 = 512 * 1024;
const PREVIEW_CACHE_VERSION: u64 = 2;

fn cache_key(source: &Path, modified: std::time::SystemTime, size: u64) -> String {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    PREVIEW_CACHE_VERSION.hash(&mut hasher);
    source.display().to_string().hash(&mut hasher);
    modified.hash(&mut hasher);
    size.hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}

#[derive(Debug, Deserialize)]
struct ProbeStream {
    codec_name: Option<String>,
    profile: Option<String>,
    pix_fmt: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ProbeResult {
    streams: Vec<ProbeStream>,
}

fn probe_video_stream(source: &Path) -> Result<Option<ProbeStream>, String> {
    let output = Command::new("ffprobe")
        .args([
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,profile,pix_fmt",
            "-of",
            "json",
        ])
        .arg(source)
        .output()
        .map_err(|e| format!("run ffprobe for {}: {e}", source.display()))?;

    if !output.status.success() {
        return Ok(None);
    }

    let probe: ProbeResult =
        serde_json::from_slice(&output.stdout).map_err(|e| format!("parse ffprobe output: {e}"))?;
    Ok(probe.streams.into_iter().next())
}

fn should_transcode_for_preview(source: &Path) -> bool {
    let Some(stream) = probe_video_stream(source).ok().flatten() else {
        return false;
    };

    let codec_name = stream.codec_name.unwrap_or_default();
    if codec_name != "h264" {
        return true;
    }

    let profile = stream.profile.unwrap_or_default();
    let profile = profile.to_lowercase();
    if !(profile.contains("baseline") || profile.contains("main")) {
        return true;
    }

    let pix_fmt = stream.pix_fmt.unwrap_or_default();
    if pix_fmt != "yuv420p" {
        return true;
    }

    false
}

fn run_ffmpeg_preview(source: &Path, output: &Path, transcode: bool) -> Result<(), String> {
    let mut command = Command::new("ffmpeg");
    command.arg("-y").arg("-i").arg(source);

    if transcode {
        command.args(["-map", "0:v:0", "-map", "0:a?"]).args([
            "-c:v",
            "libx264",
            "-profile:v",
            "baseline",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
        ]);
    } else {
        command.args(["-map", "0", "-c", "copy"]);
    }

    let output_result = command
        .args(["-movflags", "+faststart"])
        .arg(output)
        .output()
        .map_err(|e| format!("run ffmpeg for {}: {e}", source.display()))?;

    if output_result.status.success() && output.is_file() {
        return Ok(());
    }

    Err(String::from_utf8_lossy(&output_result.stderr)
        .trim()
        .to_string())
}

fn ensure_preview_video(paths: &AppPaths, source: &Path) -> Result<PathBuf, String> {
    let meta = fs::metadata(source).map_err(|e| format!("stat {}: {e}", source.display()))?;
    let cache_dir = paths.data_root.join("cache").join("web-previews");
    fs::create_dir_all(&cache_dir).map_err(|e| format!("create {}: {e}", cache_dir.display()))?;

    let cached = cache_dir.join(format!(
        "{}.mp4",
        cache_key(
            source,
            meta.modified().unwrap_or(std::time::UNIX_EPOCH),
            meta.len()
        )
    ));

    if cached.is_file() {
        let cache_meta =
            fs::metadata(&cached).map_err(|e| format!("stat {}: {e}", cached.display()))?;
        if cache_meta.modified().unwrap_or(std::time::UNIX_EPOCH)
            >= meta.modified().unwrap_or(std::time::UNIX_EPOCH)
        {
            return Ok(cached);
        }
    }

    let temp = cached.with_extension("tmp");
    let _ = fs::remove_file(&temp);

    let transcode = should_transcode_for_preview(source);
    let ffmpeg_result = run_ffmpeg_preview(source, &temp, transcode).or_else(|copy_error| {
        if transcode {
            let _ = fs::remove_file(&temp);
            run_ffmpeg_preview(source, &temp, false).map_err(|copy_fallback_error| {
                format!(
                    "preview encode failed for {}: {}; fallback copy also failed: {}",
                    source.display(),
                    copy_error,
                    copy_fallback_error
                )
            })
        } else {
            Err(format!(
                "preview encode failed for {}: {}",
                source.display(),
                copy_error
            ))
        }
    });

    if ffmpeg_result.is_ok() && temp.is_file() {
        fs::rename(&temp, &cached)
            .map_err(|e| format!("finalize preview cache {}: {e}", cached.display()))?;
        return Ok(cached);
    }

    Ok(source.to_path_buf())
}

pub fn playback_path_for_media(
    paths: &AppPaths,
    source: &Path,
    mime_type: &str,
) -> Result<PathBuf, String> {
    if !mime_type.starts_with("video/") {
        return Ok(source.to_path_buf());
    }

    let size = fs::metadata(source)
        .map_err(|e| format!("stat {}: {e}", source.display()))?
        .len();

    if size <= PARTIAL_MAX_BYTES {
        return Ok(source.to_path_buf());
    }

    ensure_preview_video(paths, source)
}
