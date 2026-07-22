use std::fs;
use std::hash::{Hash, Hasher};
use std::path::{Path, PathBuf};
use std::process::Command;

use crate::workspace::AppPaths;

const PARTIAL_MAX_BYTES: u64 = 512 * 1024;

fn cache_key(source: &Path, modified: std::time::SystemTime, size: u64) -> String {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    source.display().to_string().hash(&mut hasher);
    modified.hash(&mut hasher);
    size.hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}

fn ensure_faststart_video(paths: &AppPaths, source: &Path) -> Result<PathBuf, String> {
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

    let output = Command::new("ffmpeg")
        .arg("-y")
        .arg("-i")
        .arg(source)
        .args(["-c", "copy", "-movflags", "+faststart"])
        .arg(&cached)
        .output()
        .map_err(|e| format!("run ffmpeg for {}: {e}", source.display()))?;

    if output.status.success() && cached.is_file() {
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

    ensure_faststart_video(paths, source)
}
