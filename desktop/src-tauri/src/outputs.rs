use std::fs;
use std::path::{Component, Path, PathBuf};

use chrono::{DateTime, Utc};
use serde::Serialize;

use crate::workspace::AppPaths;

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct OutputEntry {
    pub path: String,
    pub relative_path: String,
    pub name: String,
    pub kind: String,
    pub size_bytes: u64,
    pub modified_at: String,
    pub resolution: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct OutputKindSummary {
    pub kind: String,
    pub count: usize,
    pub size_bytes: u64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct OutputListResult {
    pub entries: Vec<OutputEntry>,
    pub total_bytes: u64,
    pub renders_dir: String,
    pub by_kind: Vec<OutputKindSummary>,
}

#[derive(Debug, Clone, Copy)]
pub enum CacheKind {
    Partials,
    Tex,
    Texts,
    Images,
    Previews,
    Videos,
    All,
}

impl CacheKind {
    fn from_str(raw: &str) -> Result<Self, String> {
        match raw {
            "partials" => Ok(Self::Partials),
            "tex" => Ok(Self::Tex),
            "texts" => Ok(Self::Texts),
            "images" => Ok(Self::Images),
            "previews" => Ok(Self::Previews),
            "videos" => Ok(Self::Videos),
            "all" => Ok(Self::All),
            other => Err(format!("unknown cache kind: {other}")),
        }
    }
}

pub fn renders_root(paths: &AppPaths, project_id: &str) -> PathBuf {
    paths.renders_dir(project_id)
}

fn project_media_roots(paths: &AppPaths, project_id: &str) -> Vec<PathBuf> {
    vec![
        paths.project_media_dir(project_id),
        paths.renders_dir(project_id).join("media"),
    ]
}

pub fn validate_project_workspace_path(
    paths: &AppPaths,
    project_id: &str,
    raw: &str,
) -> Result<PathBuf, String> {
    let candidate = PathBuf::from(raw);
    if !candidate.is_absolute() {
        return Err("output path must be absolute".to_string());
    }

    let path = candidate
        .canonicalize()
        .map_err(|e| format!("resolve output path: {e}"))?;
    let workspace = paths
        .workspace_dir(project_id)
        .canonicalize()
        .map_err(|e| format!("resolve workspace dir: {e}"))?;

    if !path.starts_with(&workspace) {
        return Err("output path is outside the project workspace".to_string());
    }
    Ok(path)
}

/// Resolve and ensure a writable directory for final render output.
/// Accepts any absolute path on disk (not limited to the project renders folder).
pub fn validate_render_output_dir(raw: &str) -> Result<PathBuf, String> {
    let candidate = PathBuf::from(raw);
    if !candidate.is_absolute() {
        return Err("output directory must be an absolute path".to_string());
    }

    fs::create_dir_all(&candidate)
        .map_err(|e| format!("create output directory {}: {e}", candidate.display()))?;

    let path = candidate
        .canonicalize()
        .map_err(|e| format!("resolve output directory: {e}"))?;

    if !path.is_dir() {
        return Err(format!("output path is not a directory: {}", path.display()));
    }

    let probe = path.join(".matemium-write-test");
    fs::write(&probe, b"ok").map_err(|e| format!("output directory is not writable: {e}"))?;
    let _ = fs::remove_file(&probe);

    Ok(path)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputPathScope {
    /// Final preview MP4s directly under ``renders/``.
    RendersOnly,
    /// Any listed render output (``renders/`` or project Manim ``media/`` cache).
    Deletable,
}

fn is_allowed_output_relative(relative: &Path, scope: OutputPathScope) -> bool {
    let top = relative
        .components()
        .find_map(|c| match c {
            Component::Normal(s) => Some(s.to_string_lossy().to_string()),
            _ => None,
        });
    match scope {
        OutputPathScope::RendersOnly => top.as_deref() == Some("renders"),
        OutputPathScope::Deletable => {
            matches!(top.as_deref(), Some("renders") | Some("media"))
        }
    }
}

pub fn validate_output_path(
    paths: &AppPaths,
    project_id: &str,
    raw: &str,
    scope: OutputPathScope,
) -> Result<PathBuf, String> {
    let path = validate_project_workspace_path(paths, project_id, raw)?;
    let workspace = paths
        .workspace_dir(project_id)
        .canonicalize()
        .map_err(|e| format!("resolve workspace dir: {e}"))?;
    let relative = path
        .strip_prefix(&workspace)
        .map_err(|_| format!("output path is outside project workspace: {}", path.display()))?;

    if is_allowed_output_relative(relative, scope) {
        return Ok(path);
    }

    let msg = match scope {
        OutputPathScope::RendersOnly => {
            "output path is outside the project renders directory".to_string()
        }
        OutputPathScope::Deletable => {
            "output path is outside the project renders or media cache".to_string()
        }
    };
    Err(msg)
}

fn classify_kind(relative: &Path) -> (String, Option<String>) {
    let parts: Vec<&str> = relative
        .components()
        .filter_map(|c| match c {
            Component::Normal(s) => s.to_str(),
            _ => None,
        })
        .collect();

    if parts.iter().any(|p| *p == "partial_movie_files") {
        return ("partial".to_string(), extract_resolution(&parts));
    }

    if parts.len() >= 2 && parts[0] == "media" {
        match parts[1] {
            "Tex" => return ("tex".to_string(), None),
            "texts" => return ("text".to_string(), None),
            "images" => return ("image".to_string(), None),
            "videos" if parts.len() >= 3 => {
                let resolution = Some(parts[2].to_string());
                if relative.extension().and_then(|e| e.to_str()) == Some("mp4") {
                    return ("video".to_string(), resolution);
                }
                return ("other".to_string(), resolution);
            }
            _ => {}
        }
    }

    if parts.len() == 1 && relative.extension().and_then(|e| e.to_str()) == Some("mp4") {
        return ("preview".to_string(), None);
    }

    ("other".to_string(), extract_resolution(&parts))
}

fn extract_resolution(parts: &[&str]) -> Option<String> {
    parts
        .windows(2)
        .find(|w| w[0] == "videos")
        .map(|w| w[1].to_string())
}

fn modified_iso(path: &Path) -> String {
    let modified = fs::metadata(path)
        .and_then(|m| m.modified())
        .unwrap_or_else(|_| std::time::SystemTime::UNIX_EPOCH);
    let datetime: DateTime<Utc> = modified.into();
    datetime.to_rfc3339()
}

fn walk_outputs(renders: &Path) -> Result<Vec<OutputEntry>, String> {
    if !renders.exists() {
        return Ok(Vec::new());
    }

    let mut entries = Vec::new();
    let mut stack = vec![renders.to_path_buf()];

    while let Some(dir) = stack.pop() {
        let read_dir = fs::read_dir(&dir).map_err(|e| format!("read {}: {e}", dir.display()))?;
        for item in read_dir {
            let item = item.map_err(|e| format!("read dir entry: {e}"))?;
            let path = item.path();
            let meta = item
                .metadata()
                .map_err(|e| format!("stat {}: {e}", path.display()))?;

            if meta.is_dir() {
                stack.push(path);
                continue;
            }

            let relative = path
                .strip_prefix(renders)
                .map_err(|_| format!("strip prefix for {}", path.display()))?;
            let (kind, resolution) = classify_kind(relative);

            entries.push(OutputEntry {
                path: path.display().to_string(),
                relative_path: relative.display().to_string(),
                name: path
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("?")
                    .to_string(),
                kind,
                size_bytes: meta.len(),
                modified_at: modified_iso(&path),
                resolution,
            });
        }
    }

    entries.sort_by(|a, b| {
        b.modified_at
            .cmp(&a.modified_at)
            .then_with(|| a.relative_path.cmp(&b.relative_path))
    });
    Ok(entries)
}

pub fn list_outputs(paths: &AppPaths, project_id: &str) -> Result<OutputListResult, String> {
    let renders = renders_root(paths, project_id);
    fs::create_dir_all(&renders).map_err(|e| format!("create renders dir: {e}"))?;

    let mut entries = walk_outputs(&renders)?;
    for media_root in project_media_roots(paths, project_id) {
        if !media_root.exists() {
            continue;
        }
        for entry in walk_outputs(&media_root)? {
            if entries.iter().any(|e| e.path == entry.path) {
                continue;
            }
            entries.push(OutputEntry {
                relative_path: format!("media/{}", entry.relative_path),
                ..entry
            });
        }
    }
    let total_bytes: u64 = entries.iter().map(|e| e.size_bytes).sum();

    let mut kind_map: std::collections::BTreeMap<String, (usize, u64)> =
        std::collections::BTreeMap::new();
    for entry in &entries {
        let slot = kind_map.entry(entry.kind.clone()).or_insert((0, 0));
        slot.0 += 1;
        slot.1 += entry.size_bytes;
    }

    let by_kind = kind_map
        .into_iter()
        .map(|(kind, (count, size_bytes))| OutputKindSummary {
            kind,
            count,
            size_bytes,
        })
        .collect();

    Ok(OutputListResult {
        entries,
        total_bytes,
        renders_dir: renders.display().to_string(),
        by_kind,
    })
}

pub fn delete_output(
    paths: &AppPaths,
    project_id: &str,
    raw_path: &str,
) -> Result<(), String> {
    let path = validate_output_path(paths, project_id, raw_path, OutputPathScope::Deletable)?;
    if !path.exists() {
        return Err(format!("output not found: {}", path.display()));
    }
    if path.is_dir() {
        fs::remove_dir_all(&path).map_err(|e| format!("delete dir {}: {e}", path.display()))?;
    } else {
        fs::remove_file(&path).map_err(|e| format!("delete file {}: {e}", path.display()))?;
    }
    Ok(())
}

fn remove_dir_if_exists(path: &Path) -> Result<u64, String> {
    if !path.exists() {
        return Ok(0);
    }
    let size = dir_size(path)?;
    if path.is_dir() {
        fs::remove_dir_all(path).map_err(|e| format!("remove {}: {e}", path.display()))?;
    } else {
        fs::remove_file(path).map_err(|e| format!("remove {}: {e}", path.display()))?;
    }
    Ok(size)
}

fn dir_size(path: &Path) -> Result<u64, String> {
    if path.is_file() {
        return fs::metadata(path)
            .map(|m| m.len())
            .map_err(|e| format!("stat {}: {e}", path.display()));
    }
    if !path.is_dir() {
        return Ok(0);
    }

    let mut total = 0u64;
    let mut stack = vec![path.to_path_buf()];
    while let Some(dir) = stack.pop() {
        for item in fs::read_dir(&dir).map_err(|e| format!("read {}: {e}", dir.display()))? {
            let item = item.map_err(|e| format!("read dir entry: {e}"))?;
            let child = item.path();
            let meta = item
                .metadata()
                .map_err(|e| format!("stat {}: {e}", child.display()))?;
            if meta.is_dir() {
                stack.push(child);
            } else {
                total += meta.len();
            }
        }
    }
    Ok(total)
}

fn clear_partial_dirs(renders: &Path) -> Result<u64, String> {
    if !renders.exists() {
        return Ok(0);
    }

    let mut freed = 0u64;
    let mut stack = vec![renders.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let read_dir = fs::read_dir(&dir).map_err(|e| format!("read {}: {e}", dir.display()))?;
        for item in read_dir {
            let item = item.map_err(|e| format!("read dir entry: {e}"))?;
            let path = item.path();
            if !path.is_dir() {
                continue;
            }
            if path
                .file_name()
                .and_then(|n| n.to_str())
                .is_some_and(|n| n == "partial_movie_files")
            {
                freed += remove_dir_if_exists(&path)?;
            } else {
                stack.push(path);
            }
        }
    }
    Ok(freed)
}

pub fn clear_render_cache(
    paths: &AppPaths,
    project_id: &str,
    kind_raw: &str,
) -> Result<u64, String> {
    let kind = CacheKind::from_str(kind_raw)?;
    let renders = renders_root(paths, project_id);
    let media_roots = project_media_roots(paths, project_id);

    let freed = match kind {
        CacheKind::Partials => {
            let mut total = clear_partial_dirs(&renders)?;
            for media_root in &media_roots {
                total += clear_partial_dirs(media_root)?;
            }
            total
        }
        CacheKind::Tex => {
            let mut total = 0u64;
            for media_root in &media_roots {
                total += remove_dir_if_exists(&media_root.join("Tex"))?;
            }
            total
        }
        CacheKind::Texts => {
            let mut total = 0u64;
            for media_root in &media_roots {
                total += remove_dir_if_exists(&media_root.join("texts"))?;
            }
            total
        }
        CacheKind::Images => {
            let mut total = 0u64;
            for media_root in &media_roots {
                total += remove_dir_if_exists(&media_root.join("images"))?;
            }
            total
        }
        CacheKind::Previews => {
            let mut total = 0u64;
            if renders.is_dir() {
                for item in fs::read_dir(&renders)
                    .map_err(|e| format!("read {}: {e}", renders.display()))?
                {
                    let item = item.map_err(|e| format!("read dir entry: {e}"))?;
                    let path = item.path();
                    if path.is_file()
                        && path.extension().and_then(|e| e.to_str()) == Some("mp4")
                    {
                        total += remove_dir_if_exists(&path)?;
                    }
                }
            }
            total
        }
        CacheKind::Videos => {
            let mut total = 0u64;
            for media_root in &media_roots {
                total += remove_dir_if_exists(&media_root.join("videos"))?;
            }
            total
        }
        CacheKind::All => {
            let mut total = dir_size(&renders)?;
            if renders.exists() {
                fs::remove_dir_all(&renders)
                    .map_err(|e| format!("clear renders dir: {e}"))?;
            }
            fs::create_dir_all(&renders).map_err(|e| format!("recreate renders dir: {e}"))?;

            for media_root in &media_roots {
                if media_root.exists() {
                    total += dir_size(media_root)?;
                    fs::remove_dir_all(media_root)
                        .map_err(|e| format!("clear media cache {}: {e}", media_root.display()))?;
                }
                fs::create_dir_all(media_root)
                    .map_err(|e| format!("recreate media dir {}: {e}", media_root.display()))?;
            }
            total
        }
    };

    Ok(freed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn fixture_paths(project_id: &str) -> (AppPaths, PathBuf) {
        let paths = AppPaths::resolve().expect("paths");
        paths.ensure().expect("ensure");
        let renders = paths.renders_dir(project_id);
        if renders.exists() {
            fs::remove_dir_all(&renders).ok();
        }
        fs::create_dir_all(&renders).expect("renders");
        (paths, renders)
    }

    #[test]
    fn classify_preview_and_partial_entries() {
        let (paths, renders) = fixture_paths("outputs-classify-test");
        let preview = renders.join("MyScene.mp4");
        fs::write(&preview, b"mp4").expect("preview");

        let partial = renders
            .join("media/videos/1920p30/partial_movie_files/MyScene/seg.mp4");
        fs::create_dir_all(partial.parent().expect("parent")).expect("partial dir");
        fs::write(&partial, b"partial").expect("partial");

        let tex = renders.join("media/Tex/abc.svg");
        fs::create_dir_all(tex.parent().expect("parent")).expect("tex dir");
        fs::write(&tex, b"svg").expect("tex");

        let result = list_outputs(&paths, "outputs-classify-test").expect("list");
        let kinds: std::collections::BTreeMap<_, _> = result
            .entries
            .iter()
            .map(|e| (e.relative_path.clone(), e.kind.clone()))
            .collect();

        assert_eq!(kinds.get("MyScene.mp4").map(String::as_str), Some("preview"));
        assert_eq!(
            kinds
                .get("media/videos/1920p30/partial_movie_files/MyScene/seg.mp4")
                .map(String::as_str),
            Some("partial")
        );
        assert_eq!(
            kinds.get("media/Tex/abc.svg").map(String::as_str),
            Some("tex")
        );
    }

    #[test]
    fn clear_partials_keeps_final_video() {
        let (paths, renders) = fixture_paths("outputs-clear-partial-test");
        let final_video = renders.join("media/videos/960p15/Demo.mp4");
        fs::create_dir_all(final_video.parent().expect("parent")).expect("video dir");
        fs::write(&final_video, b"final").expect("final");

        let partial = renders
            .join("media/videos/960p15/partial_movie_files/Demo/seg.mp4");
        fs::create_dir_all(partial.parent().expect("parent")).expect("partial dir");
        fs::write(&partial, b"partial").expect("partial");

        clear_render_cache(&paths, "outputs-clear-partial-test", "partials").expect("clear");
        assert!(final_video.exists());
        assert!(!partial.exists());
    }

    #[test]
    fn delete_output_accepts_workspace_media_cache() {
        let paths = AppPaths::resolve().expect("paths");
        paths.ensure().expect("ensure");
        let project_id = "outputs-delete-media-test";
        let workspace = paths.workspace_dir(project_id);
        if workspace.exists() {
            fs::remove_dir_all(&workspace).ok();
        }
        fs::create_dir_all(&workspace).expect("workspace");

        let media_video = paths
            .project_media_dir(project_id)
            .join("videos/960p15/Demo.mp4");
        fs::create_dir_all(media_video.parent().expect("parent")).expect("video dir");
        fs::write(&media_video, b"final").expect("video");

        delete_output(
            &paths,
            project_id,
            &media_video.display().to_string(),
        )
        .expect("delete media cache file");
        assert!(!media_video.exists());
    }

    #[test]
    fn clear_all_includes_workspace_media() {
        let paths = AppPaths::resolve().expect("paths");
        paths.ensure().expect("ensure");
        let project_id = "outputs-clear-all-media-test";
        let renders = paths.renders_dir(project_id);
        if renders.exists() {
            fs::remove_dir_all(&renders).ok();
        }
        let media = paths.project_media_dir(project_id);
        if media.exists() {
            fs::remove_dir_all(&media).ok();
        }

        fs::create_dir_all(&renders).expect("renders");
        fs::write(renders.join("Preview.mp4"), b"mp4").expect("preview");

        let tex = media.join("Tex/abc.svg");
        fs::create_dir_all(tex.parent().expect("parent")).expect("tex dir");
        fs::write(&tex, b"svg").expect("tex");

        clear_render_cache(&paths, project_id, "all").expect("clear all");
        assert!(renders.exists());
        assert!(media.exists());
        assert!(!tex.exists());
        assert!(!renders.join("Preview.mp4").exists());
    }

    #[test]
    fn validate_output_path_rejects_non_output_workspace_files() {
        let (paths, renders) = fixture_paths("outputs-guard-test");
        let outside = renders.parent().expect("workspace").join("scenes.py");
        fs::write(&outside, b"# test").expect("scenes");

        let err = validate_output_path(
            &paths,
            "outputs-guard-test",
            &outside.display().to_string(),
            OutputPathScope::Deletable,
        )
        .expect_err("outside output roots");
        assert!(err.contains("outside"));
    }
}