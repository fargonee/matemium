use std::collections::BTreeMap;
use std::fs;
use std::path::{Component, Path, PathBuf};
use std::time::SystemTime;

use chrono::Utc;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::workspace::{read_json_file, write_json, AppPaths};

const SCENES_TEMPLATE: &str = include_str!("../../../shared/templates/scenes.py");
const HELPERS_TEMPLATE: &str = include_str!("../../../shared/templates/helpers.py");
const PASSPORT_TEMPLATE: &str = include_str!("../../../shared/templates/passport.json");
const DESCRIPTION_TEMPLATE: &str = include_str!("../../../shared/templates/description.md");
const TAPE_TEMPLATE: &str = include_str!("../../../shared/templates/tape.md");
const ORCHESTRATION_TEMPLATE: &str = include_str!("../../../shared/templates/orchestration.md");
const ROADMAP_TEMPLATE: &str = include_str!("../../../shared/templates/roadmap.json");
const NARRATION_TEMPLATE: &str = include_str!("../../../shared/templates/narration.md");
const TTS_STYLE_TEMPLATE: &str = include_str!("../../../shared/templates/tts-narration-style.md");
const AUDIO_DESCRIPTION_TEMPLATE: &str =
    include_str!("../../../shared/templates/audio-description.md");
const CUSTOM_NARRATION_TEMPLATE: &str =
    include_str!("../../../shared/templates/custom-narration.md");
const TRANSCRIPT_TEMPLATE: &str = include_str!("../../../shared/templates/transcript.md");
const TIMESTAMPS_TEMPLATE: &str = include_str!("../../../shared/templates/timestamps.json");

const PROJECT_FILES: [(&str, &str); 13] = [
    ("scenes", "scenes.py"),
    ("helpers", "helpers.py"),
    ("passport", "brief/passport.json"),
    ("description", "brief/description.md"),
    ("tape_content", "brief/tapes/main.md"),
    ("orchestration", "brief/orchestration.md"),
    ("roadmap", "brief/roadmap.json"),
    ("tts_narration", "brief/tts-narration.md"),
    ("tts_style", "brief/tts-narration-style.md"),
    ("audio_description", "brief/audio-description.md"),
    ("custom_narration", "brief/custom-narration.md"),
    ("transcript", "brief/transcript.md"),
    ("timestamps", "brief/timestamps.json"),
];

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectMeta {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub description: String,
    #[serde(default = "default_scene_class")]
    pub scene_class: String,
    #[serde(default = "default_orientation")]
    pub orientation: String,
    pub created_at: String,
    pub updated_at: String,
}

fn default_scene_class() -> String {
    "MyScene".to_string()
}

fn default_orientation() -> String {
    "portrait".to_string()
}

#[derive(Debug, Clone, Serialize)]
pub struct ProjectSummary {
    pub id: String,
    pub name: String,
    pub description: String,
    pub scene_class: String,
    pub updated_at: String,
    pub preview_video: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ProjectMediaEntry {
    pub name: String,
    pub path: String,
    pub bytes: u64,
}

fn media_dir(workspace: &Path, category: &str) -> Result<PathBuf, String> {
    let folder = match category {
        "images" => "images",
        "video" => "video",
        "audio" => "audio",
        _ => return Err(format!("unsupported media category: {category}")),
    };
    Ok(workspace.join("assets").join(folder))
}

fn media_extension_allowed(category: &str, extension: &str) -> bool {
    let extension = extension.to_ascii_lowercase();
    match category {
        "images" => ["png", "jpg", "jpeg", "webp", "gif", "svg"].contains(&extension.as_str()),
        "video" => ["mp4", "mov", "webm", "mkv"].contains(&extension.as_str()),
        "audio" => ["mp3", "wav", "ogg", "m4a", "flac"].contains(&extension.as_str()),
        _ => false,
    }
}

pub fn list_project_media(
    paths: &AppPaths,
    project_id: &str,
    category: &str,
) -> Result<Vec<ProjectMediaEntry>, String> {
    let workspace = paths.workspace_dir(project_id);
    if !workspace.is_dir() {
        return Err(format!("project not found: {project_id}"));
    }
    let directory = media_dir(&workspace, category)?;
    fs::create_dir_all(&directory).map_err(|e| format!("create media directory: {e}"))?;
    let mut entries = Vec::new();
    for entry in fs::read_dir(&directory).map_err(|e| format!("read media directory: {e}"))? {
        let entry = entry.map_err(|e| format!("read media entry: {e}"))?;
        if !entry.file_type().map_err(|e| e.to_string())?.is_file() {
            continue;
        }
        entries.push(ProjectMediaEntry {
            name: entry.file_name().to_string_lossy().into_owned(),
            path: entry.path().display().to_string(),
            bytes: entry.metadata().map_err(|e| e.to_string())?.len(),
        });
    }
    entries.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    Ok(entries)
}

pub fn import_project_media(
    paths: &AppPaths,
    project_id: &str,
    category: &str,
    source: &str,
) -> Result<ProjectMediaEntry, String> {
    let workspace = paths.workspace_dir(project_id);
    let source = Path::new(source);
    if !workspace.is_dir() || !source.is_file() {
        return Err("project or source media file not found".to_string());
    }
    let extension = source
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or("");
    if !media_extension_allowed(category, extension) {
        return Err(format!(".{extension} is not supported in {category}"));
    }
    let directory = media_dir(&workspace, category)?;
    fs::create_dir_all(&directory).map_err(|e| format!("create media directory: {e}"))?;
    let original_name = source
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or("invalid media filename")?;
    let stem = source
        .file_stem()
        .and_then(|value| value.to_str())
        .unwrap_or("media");
    let mut destination = directory.join(original_name);
    let mut suffix = 2;
    while destination.exists() {
        destination = directory.join(format!("{stem}-{suffix}.{extension}"));
        suffix += 1;
    }
    fs::copy(source, &destination).map_err(|e| format!("import media: {e}"))?;
    touch_project_updated(paths, project_id)?;
    let metadata = destination.metadata().map_err(|e| e.to_string())?;
    Ok(ProjectMediaEntry {
        name: destination
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .into_owned(),
        path: destination.display().to_string(),
        bytes: metadata.len(),
    })
}

pub fn delete_project_media(
    paths: &AppPaths,
    project_id: &str,
    category: &str,
    name: &str,
) -> Result<(), String> {
    if Path::new(name).components().count() != 1 {
        return Err("invalid media filename".to_string());
    }
    let workspace = paths.workspace_dir(project_id);
    let path = media_dir(&workspace, category)?.join(name);
    if !path.is_file() {
        return Err(format!("media file not found: {name}"));
    }
    fs::remove_file(&path).map_err(|e| format!("delete media: {e}"))?;
    touch_project_updated(paths, project_id)
}

fn is_rendered_mp4(path: &Path) -> bool {
    path.extension().and_then(|ext| ext.to_str()) == Some("mp4")
        && !path
            .components()
            .any(|part| matches!(part, Component::Normal(name) if name == "partial_movie_files"))
}

fn find_preview_video(paths: &AppPaths, project_id: &str) -> Option<String> {
    let renders = paths.renders_dir(project_id);
    if !renders.is_dir() {
        return None;
    }

    let mut newest: Option<(SystemTime, std::path::PathBuf)> = None;
    let mut stack = vec![renders];
    while let Some(dir) = stack.pop() {
        let Ok(read_dir) = fs::read_dir(&dir) else {
            continue;
        };
        for entry in read_dir.flatten() {
            let path = entry.path();
            if path.is_dir() {
                stack.push(path);
                continue;
            }
            if !is_rendered_mp4(&path) {
                continue;
            }
            let Ok(modified) = entry.metadata().and_then(|meta| meta.modified()) else {
                continue;
            };
            if newest
                .as_ref()
                .map(|(best, _)| modified > *best)
                .unwrap_or(true)
            {
                newest = Some((modified, path));
            }
        }
    }

    newest.map(|(_, path)| path.display().to_string())
}

#[derive(Debug, Clone, Serialize)]
pub struct ProjectOpen {
    pub id: String,
    pub name: String,
    pub description: String,
    pub scene_class: String,
    pub orientation: String,
    pub files: BTreeMap<String, String>,
    pub tapes: BTreeMap<String, String>,
    pub project_json: serde_json::Value,
    pub renders_dir: String,
}

fn valid_tape_slug(slug: &str) -> bool {
    !slug.is_empty()
        && slug.len() <= 64
        && slug
            .chars()
            .next()
            .is_some_and(|ch| ch.is_ascii_lowercase() || ch.is_ascii_digit())
        && slug
            .chars()
            .all(|ch| ch.is_ascii_lowercase() || ch.is_ascii_digit() || ch == '-' || ch == '_')
}

fn read_tape_contents(workspace: &Path) -> Result<BTreeMap<String, String>, String> {
    let mut tapes = BTreeMap::new();
    let directory = workspace.join("brief/tapes");
    for entry in
        fs::read_dir(&directory).map_err(|e| format!("read {}: {e}", directory.display()))?
    {
        let entry = entry.map_err(|e| format!("read tape entry: {e}"))?;
        if !entry.file_type().map_err(|e| e.to_string())?.is_file() {
            continue;
        }
        let path = entry.path();
        if path.extension().and_then(|value| value.to_str()) != Some("md") {
            continue;
        }
        let Some(slug) = path.file_stem().and_then(|value| value.to_str()) else {
            continue;
        };
        if !valid_tape_slug(slug) {
            continue;
        }
        let content =
            fs::read_to_string(&path).map_err(|e| format!("read {}: {e}", path.display()))?;
        tapes.insert(slug.to_string(), content);
    }
    Ok(tapes)
}

pub fn create_tape_content(
    paths: &AppPaths,
    project_id: &str,
    slug: &str,
    title: &str,
) -> Result<(), String> {
    if !valid_tape_slug(slug) {
        return Err(
            "tape slug must contain 1-64 lowercase letters, numbers, hyphens, or underscores"
                .to_string(),
        );
    }
    let title = title.trim();
    if title.is_empty() || title.len() > 120 {
        return Err("tape title must contain 1-120 characters".to_string());
    }
    let workspace = paths.workspace_dir(project_id);
    if !workspace.is_dir() {
        return Err(format!("project not found: {project_id}"));
    }
    let path = workspace.join("brief/tapes").join(format!("{slug}.md"));
    if path.exists() {
        return Err(format!("tape content already exists: {slug}"));
    }
    let content = TAPE_TEMPLATE.replace("Main tape", title);
    ensure_file(&path, &content)?;
    touch_project_updated(paths, project_id)
}

pub fn save_tape_content(
    paths: &AppPaths,
    project_id: &str,
    slug: &str,
    content: &str,
) -> Result<(), String> {
    if !valid_tape_slug(slug) {
        return Err("invalid tape slug".to_string());
    }
    let workspace = paths.workspace_dir(project_id);
    let path = workspace.join("brief/tapes").join(format!("{slug}.md"));
    if !path.is_file() {
        return Err(format!("tape content not found: {slug}"));
    }
    fs::write(&path, content).map_err(|e| format!("write {}: {e}", path.display()))?;
    touch_project_updated(paths, project_id)
}

fn project_file_path(workspace: &Path, key: &str) -> Result<PathBuf, String> {
    let relative = PROJECT_FILES
        .iter()
        .find_map(|(candidate, path)| (*candidate == key).then_some(*path))
        .ok_or_else(|| format!("unsupported project file: {key}"))?;
    Ok(workspace.join(relative))
}

fn ensure_file(path: &Path, content: &str) -> Result<(), String> {
    if path.exists() {
        return Ok(());
    }
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    fs::write(path, content).map_err(|e| format!("write {}: {e}", path.display()))
}

fn migrate_lifecycle_json(workspace: &Path) -> Result<(), String> {
    let passport_path = workspace.join("brief/passport.json");
    let mut passport = read_json_file(&passport_path)?;
    let passport_object = passport
        .as_object_mut()
        .ok_or_else(|| "brief/passport.json must contain a JSON object".to_string())?;
    let mut passport_changed = false;
    if passport_object
        .get("schema_version")
        .and_then(|v| v.as_u64())
        .unwrap_or(0)
        < 2
    {
        passport_object.insert("schema_version".into(), serde_json::json!(2));
        passport_changed = true;
    }
    if !passport_object.contains_key("production_path") {
        passport_object.insert("production_path".into(), serde_json::Value::Null);
        passport_changed = true;
    }
    let production_path_missing = passport_object
        .get("production_path")
        .is_some_and(|value| value.is_null());
    if let Some(missing) = passport_object
        .get_mut("readiness")
        .and_then(|value| value.as_object_mut())
        .and_then(|readiness| readiness.get_mut("missing_fields"))
        .and_then(|value| value.as_array_mut())
    {
        if !missing
            .iter()
            .any(|value| value.as_str() == Some("production_path"))
            && production_path_missing
        {
            missing.push(serde_json::json!("production_path"));
            passport_changed = true;
        } else if !production_path_missing {
            let before = missing.len();
            missing.retain(|value| value.as_str() != Some("production_path"));
            passport_changed |= before != missing.len();
        }
    }
    if passport_changed {
        write_json(&passport_path, &passport)?;
    }

    let roadmap_path = workspace.join("brief/roadmap.json");
    let roadmap = read_json_file(&roadmap_path)?;
    let legacy_default = roadmap
        .get("phases")
        .and_then(|value| value.as_array())
        .map(|phases| {
            phases
                .iter()
                .filter_map(|phase| phase.get("id").and_then(|id| id.as_str()))
                .collect::<Vec<_>>()
                == ["concept", "production", "review"]
        })
        .unwrap_or(false);
    if legacy_default {
        let mut lifecycle: serde_json::Value = serde_json::from_str(ROADMAP_TEMPLATE)
            .map_err(|e| format!("invalid lifecycle roadmap template: {e}"))?;
        lifecycle
            .as_object_mut()
            .expect("roadmap template is an object")
            .insert("legacy_roadmap".into(), roadmap);
        write_json(&roadmap_path, &lifecycle)?;
    } else if let Some(object) = roadmap.as_object() {
        if !object.contains_key("schema_version") || !object.contains_key("production_path") {
            let mut migrated = roadmap;
            let migrated_object = migrated.as_object_mut().expect("checked object");
            migrated_object
                .entry("schema_version")
                .or_insert_with(|| serde_json::json!(2));
            migrated_object
                .entry("production_path")
                .or_insert(serde_json::Value::Null);
            write_json(&roadmap_path, &migrated)?;
        }
    }
    Ok(())
}

fn production_path_valid(value: &serde_json::Value) -> bool {
    value.is_null() || matches!(value.as_str(), Some("mute_video" | "tts" | "custom_audio"))
}

fn expected_phase_ids(path: Option<&str>) -> &'static [&'static str] {
    match path {
        Some("mute_video") => &[
            "project_creation",
            "description",
            "passport",
            "tape_content",
            "orchestration",
            "authoring",
            "render_repair",
            "mute_delivery",
        ],
        Some("tts") => &[
            "project_creation",
            "description",
            "passport",
            "tape_content",
            "orchestration",
            "tts_narration",
            "authoring",
            "render_repair",
            "timing_regulation",
            "tts_generation",
            "final_assembly",
        ],
        Some("custom_audio") => &[
            "project_creation",
            "description",
            "passport",
            "tape_content",
            "orchestration",
            "audio_specification",
            "audio_generation",
            "transcription_validation",
            "content_reconciliation",
            "authoring",
            "render_repair",
            "final_assembly",
        ],
        _ => &["project_creation", "description", "passport"],
    }
}

fn validate_structured_brief(file: &str, value: &serde_json::Value) -> Result<(), String> {
    let object = value
        .as_object()
        .ok_or_else(|| format!("{file} must contain a JSON object"))?;
    match file {
        "passport" => {
            if let Some(path) = object.get("production_path") {
                if !production_path_valid(path) {
                    return Err(
                        "passport.production_path must be null, mute_video, tts, or custom_audio"
                            .to_string(),
                    );
                }
            }
        }
        "roadmap" => {
            if let Some(path) = object.get("production_path") {
                if !production_path_valid(path) {
                    return Err(
                        "roadmap.production_path must be null, mute_video, tts, or custom_audio"
                            .to_string(),
                    );
                }
            }
            let phases = object
                .get("phases")
                .and_then(|value| value.as_array())
                .ok_or_else(|| "roadmap.phases must be an array".to_string())?;
            let path = object
                .get("production_path")
                .and_then(|value| value.as_str());
            let actual_ids = phases
                .iter()
                .filter_map(|phase| phase.get("id").and_then(|value| value.as_str()))
                .collect::<Vec<_>>();
            if actual_ids != expected_phase_ids(path) {
                return Err(format!(
                    "roadmap phases do not match the {:?} production lifecycle",
                    path.unwrap_or("unselected")
                ));
            }
            let current = object
                .get("current_phase")
                .and_then(|value| value.as_str())
                .ok_or_else(|| "roadmap.current_phase must be a string".to_string())?;
            let mut current_exists = false;
            for phase in phases {
                let phase = phase
                    .as_object()
                    .ok_or_else(|| "each roadmap phase must be an object".to_string())?;
                let id = phase
                    .get("id")
                    .and_then(|value| value.as_str())
                    .ok_or_else(|| "each roadmap phase needs an id".to_string())?;
                current_exists |= id == current;
                if !matches!(
                    phase.get("status").and_then(|value| value.as_str()),
                    Some("todo" | "in_progress" | "done")
                ) {
                    return Err(format!("roadmap phase {id} has an invalid status"));
                }
            }
            if !current_exists {
                return Err("roadmap.current_phase must reference a phase id".to_string());
            }
        }
        "timestamps" => {
            let segments = object
                .get("segments")
                .and_then(|value| value.as_array())
                .ok_or_else(|| "timestamps.segments must be an array".to_string())?;
            for segment in segments {
                let start = segment.get("start").and_then(|value| value.as_f64());
                let end = segment.get("end").and_then(|value| value.as_f64());
                let text = segment.get("text").and_then(|value| value.as_str());
                if start.map_or(true, |value| value < 0.0)
                    || end.map_or(true, |value| value <= 0.0)
                    || start.zip(end).map_or(true, |(start, end)| end < start)
                    || text.is_none()
                {
                    return Err("each timestamp segment needs start <= end and text".to_string());
                }
            }
        }
        _ => {}
    }
    Ok(())
}

fn migrate_legacy_assets_imports(source: &str) -> String {
    source
        .split_inclusive('\n')
        .map(|line| {
            let indent_len = line.len() - line.trim_start_matches([' ', '\t']).len();
            let (indent, code) = line.split_at(indent_len);
            if let Some(rest) = code.strip_prefix("from .assets import ") {
                format!("{indent}from .helpers import {rest}")
            } else if let Some(rest) = code.strip_prefix("from assets import ") {
                format!("{indent}from helpers import {rest}")
            } else {
                line.to_string()
            }
        })
        .collect()
}

fn ensure_workspace_structure(workspace: &Path, project_name: &str) -> Result<(), String> {
    let helpers = workspace.join("helpers.py");
    let legacy_assets = workspace.join("assets.py");
    if !helpers.exists() && legacy_assets.is_file() {
        fs::rename(&legacy_assets, &helpers)
            .map_err(|e| format!("migrate assets.py to helpers.py: {e}"))?;
    }

    ensure_file(&helpers, HELPERS_TEMPLATE)?;
    if helpers.is_file() && !legacy_assets.is_file() {
        let scenes = workspace.join("scenes.py");
        if scenes.is_file() {
            let source = fs::read_to_string(&scenes)
                .map_err(|e| format!("read {}: {e}", scenes.display()))?;
            let migrated = migrate_legacy_assets_imports(&source);
            if migrated != source {
                fs::write(&scenes, migrated)
                    .map_err(|e| format!("migrate imports in {}: {e}", scenes.display()))?;
            }
        }
    }
    let passport = PASSPORT_TEMPLATE.replace("Untitled project", project_name);
    ensure_file(&workspace.join("brief/passport.json"), &passport)?;
    ensure_file(
        &workspace.join("brief/description.md"),
        DESCRIPTION_TEMPLATE,
    )?;
    let tape_content = workspace.join("brief/tapes/main.md");
    let legacy_tape = workspace.join("brief/tape.md");
    if !tape_content.exists() && legacy_tape.is_file() {
        let legacy = fs::read_to_string(&legacy_tape)
            .map_err(|e| format!("read {}: {e}", legacy_tape.display()))?;
        ensure_file(&tape_content, &legacy)?;
    } else {
        ensure_file(&tape_content, TAPE_TEMPLATE)?;
    }
    ensure_file(
        &workspace.join("brief/orchestration.md"),
        ORCHESTRATION_TEMPLATE,
    )?;
    ensure_file(&workspace.join("brief/roadmap.json"), ROADMAP_TEMPLATE)?;
    let tts_narration = workspace.join("brief/tts-narration.md");
    let legacy_narration = workspace.join("brief/narration.md");
    if !tts_narration.exists() && legacy_narration.is_file() {
        let legacy = fs::read_to_string(&legacy_narration)
            .map_err(|e| format!("read {}: {e}", legacy_narration.display()))?;
        ensure_file(&tts_narration, &legacy)?;
    } else {
        ensure_file(&tts_narration, NARRATION_TEMPLATE)?;
    }
    ensure_file(
        &workspace.join("brief/tts-narration-style.md"),
        TTS_STYLE_TEMPLATE,
    )?;
    ensure_file(
        &workspace.join("brief/audio-description.md"),
        AUDIO_DESCRIPTION_TEMPLATE,
    )?;
    ensure_file(
        &workspace.join("brief/custom-narration.md"),
        CUSTOM_NARRATION_TEMPLATE,
    )?;
    ensure_file(&workspace.join("brief/transcript.md"), TRANSCRIPT_TEMPLATE)?;
    ensure_file(
        &workspace.join("brief/timestamps.json"),
        TIMESTAMPS_TEMPLATE,
    )?;
    migrate_lifecycle_json(workspace)?;
    for directory in ["assets/images", "assets/video", "assets/audio", "renders"] {
        fs::create_dir_all(workspace.join(directory))
            .map_err(|e| format!("create {directory}: {e}"))?;
    }
    Ok(())
}

pub fn list_projects(paths: &AppPaths) -> Result<Vec<ProjectSummary>, String> {
    if !paths.workspaces_root.exists() {
        return Ok(Vec::new());
    }

    let mut projects = Vec::new();
    for entry in
        fs::read_dir(&paths.workspaces_root).map_err(|e| format!("read workspaces: {e}"))?
    {
        let entry = entry.map_err(|e| format!("workspace entry: {e}"))?;
        if !entry.file_type().map_err(|e| e.to_string())?.is_dir() {
            continue;
        }
        let project_json = entry.path().join("project.json");
        if !project_json.exists() {
            continue;
        }
        let meta: ProjectMeta = serde_json::from_value(read_json_file(&project_json)?)
            .map_err(|e| format!("invalid project.json in {}: {e}", entry.path().display()))?;
        projects.push(ProjectSummary {
            id: meta.id.clone(),
            name: meta.name,
            description: meta.description,
            scene_class: meta.scene_class,
            updated_at: meta.updated_at,
            preview_video: find_preview_video(paths, &meta.id),
        });
    }

    projects.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    Ok(projects)
}

pub fn create_project(paths: &AppPaths, name: String) -> Result<ProjectOpen, String> {
    let trimmed = name.trim();
    if trimmed.is_empty() {
        return Err("project name is required".to_string());
    }

    let id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();
    let workspace = paths.workspace_dir(&id);
    fs::create_dir_all(&workspace).map_err(|e| format!("create workspace: {e}"))?;

    let meta = ProjectMeta {
        id: id.clone(),
        name: trimmed.to_string(),
        description: String::new(),
        scene_class: default_scene_class(),
        orientation: default_orientation(),
        created_at: now.clone(),
        updated_at: now,
    };

    write_json(&paths.project_json_path(&id), &meta)?;
    fs::write(paths.scenes_path(&id), SCENES_TEMPLATE)
        .map_err(|e| format!("write scenes.py: {e}"))?;
    ensure_workspace_structure(&workspace, trimmed)?;

    open_project(paths, &id)
}

pub fn open_project(paths: &AppPaths, project_id: &str) -> Result<ProjectOpen, String> {
    let workspace = paths.workspace_dir(project_id);
    if !workspace.is_dir() {
        return Err(format!("project not found: {project_id}"));
    }

    let project_json_path = paths.project_json_path(project_id);
    if !project_json_path.exists() {
        return Err(format!("missing project.json for {project_id}"));
    }

    let scenes_path = paths.scenes_path(project_id);
    if !scenes_path.exists() {
        return Err(format!("missing scenes.py for {project_id}"));
    }

    let meta: ProjectMeta = serde_json::from_value(read_json_file(&project_json_path)?)
        .map_err(|e| format!("invalid project.json: {e}"))?;
    ensure_workspace_structure(&workspace, &meta.name)?;
    let mut files = BTreeMap::new();
    for (key, _) in PROJECT_FILES {
        let path = project_file_path(&workspace, key)?;
        let content =
            fs::read_to_string(&path).map_err(|e| format!("read {}: {e}", path.display()))?;
        files.insert(key.to_string(), content);
    }
    let project_json = read_json_file(&project_json_path)?;
    let tapes = read_tape_contents(&workspace)?;

    Ok(ProjectOpen {
        id: meta.id,
        name: meta.name,
        description: meta.description,
        scene_class: meta.scene_class,
        orientation: meta.orientation,
        files,
        tapes,
        project_json,
        renders_dir: paths.renders_dir(project_id).display().to_string(),
    })
}

fn touch_project_updated(paths: &AppPaths, project_id: &str) -> Result<(), String> {
    let project_json_path = paths.project_json_path(project_id);
    if !project_json_path.exists() {
        return Ok(());
    }
    let mut meta: ProjectMeta = serde_json::from_value(read_json_file(&project_json_path)?)
        .map_err(|e| format!("invalid project.json: {e}"))?;
    meta.updated_at = Utc::now().to_rfc3339();
    write_json(&project_json_path, &meta)
}

pub fn save_scenes(paths: &AppPaths, project_id: &str, content: &str) -> Result<(), String> {
    let scenes_path = paths.scenes_path(project_id);
    if !scenes_path.exists() {
        return Err(format!("project not found: {project_id}"));
    }

    fs::write(&scenes_path, content).map_err(|e| format!("write scenes.py: {e}"))?;
    touch_project_updated(paths, project_id)
}

pub fn save_project_file(
    paths: &AppPaths,
    project_id: &str,
    file: &str,
    content: &str,
) -> Result<(), String> {
    let workspace = paths.workspace_dir(project_id);
    if !workspace.is_dir() {
        return Err(format!("project not found: {project_id}"));
    }

    if matches!(file, "passport" | "roadmap" | "timestamps") {
        let value = serde_json::from_str::<serde_json::Value>(content)
            .map_err(|e| format!("invalid JSON for {file}: {e}"))?;
        validate_structured_brief(file, &value)?;
    }
    let path = project_file_path(&workspace, file)?;
    fs::write(&path, content).map_err(|e| format!("write {}: {e}", path.display()))?;
    touch_project_updated(paths, project_id)
}

pub fn delete_project(paths: &AppPaths, project_id: &str) -> Result<(), String> {
    let workspace = paths.workspace_dir(project_id);
    if !workspace.is_dir() {
        return Err(format!("project not found: {project_id}"));
    }
    fs::remove_dir_all(&workspace).map_err(|e| format!("delete workspace: {e}"))
}

pub fn workspace_path(paths: &AppPaths, project_id: &str) -> Result<String, String> {
    let workspace = paths.workspace_dir(project_id);
    if !workspace.is_dir() {
        return Err(format!("project not found: {project_id}"));
    }
    Ok(workspace.display().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_paths() -> AppPaths {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!("matemium-test-{stamp}"));
        AppPaths {
            data_root: root.clone(),
            workspaces_root: root.join("workspaces"),
            config_dir: root.join("config"),
            settings_path: root.join("config/settings.json"),
            assets_root: root.join("assets"),
            agent_root: root.join("agent"),
        }
    }

    #[test]
    fn create_open_delete_project_roundtrip() {
        let paths = temp_paths();
        paths.ensure().expect("ensure");
        let created = create_project(&paths, "Quadratic".to_string()).expect("create");
        assert_eq!(created.name, "Quadratic");
        assert!(created.files["scenes"].contains("CanvasBuilder"));
        assert!(created.files["helpers"].contains("Reusable computations"));
        assert!(paths
            .workspace_dir(&created.id)
            .join("brief/passport.json")
            .is_file());
        assert!(paths
            .workspace_dir(&created.id)
            .join("assets/images")
            .is_dir());

        let listed = list_projects(&paths).expect("list");
        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].name, "Quadratic");

        save_scenes(&paths, &created.id, "# updated\n").expect("save");
        let opened = open_project(&paths, &created.id).expect("open");
        assert_eq!(opened.files["scenes"], "# updated\n");

        delete_project(&paths, &created.id).expect("delete");
        assert!(list_projects(&paths).unwrap().is_empty());
        let _ = fs::remove_dir_all(&paths.data_root);
    }

    #[test]
    fn open_migrates_legacy_assets_python_to_helpers() {
        let paths = temp_paths();
        paths.ensure().expect("ensure");
        let created = create_project(&paths, "Legacy".to_string()).expect("create");
        let workspace = paths.workspace_dir(&created.id);
        fs::remove_file(workspace.join("helpers.py")).expect("remove helpers");
        fs::write(workspace.join("assets.py"), "LEGACY_VALUE = 42\n").expect("legacy file");
        fs::write(
            workspace.join("scenes.py"),
            "from .assets import LEGACY_VALUE\n",
        )
        .expect("legacy scenes import");

        let opened = open_project(&paths, &created.id).expect("open");
        assert_eq!(opened.files["helpers"], "LEGACY_VALUE = 42\n");
        assert_eq!(
            opened.files["scenes"],
            "from .helpers import LEGACY_VALUE\n"
        );
        assert!(!workspace.join("assets.py").exists());
        let _ = fs::remove_dir_all(&paths.data_root);
    }

    #[test]
    fn open_repairs_imports_in_an_already_migrated_workspace() {
        let paths = temp_paths();
        paths.ensure().expect("ensure");
        let created = create_project(&paths, "Already migrated".to_string()).expect("create");
        let workspace = paths.workspace_dir(&created.id);
        fs::write(
            workspace.join("scenes.py"),
            "from assets import add_compare_row\n",
        )
        .expect("legacy scenes import");

        let opened = open_project(&paths, &created.id).expect("open");

        assert_eq!(
            opened.files["scenes"],
            "from helpers import add_compare_row\n"
        );
        let _ = fs::remove_dir_all(&paths.data_root);
    }

    #[test]
    fn structured_brief_and_source_assets_are_validated() {
        let paths = temp_paths();
        paths.ensure().expect("ensure");
        let created = create_project(&paths, "Assets".to_string()).expect("create");

        assert!(save_project_file(&paths, &created.id, "passport", "not json").is_err());
        save_project_file(&paths, &created.id, "passport", "{\"status\":\"draft\"}\n")
            .expect("valid passport");
        assert!(save_project_file(
            &paths,
            &created.id,
            "passport",
            "{\"production_path\":\"surprise_me\"}\n"
        )
        .is_err());
        assert!(save_project_file(
            &paths,
            &created.id,
            "timestamps",
            "{\"segments\":[{\"start\":4,\"end\":2,\"text\":\"backwards\"}]}\n"
        )
        .is_err());

        let source = paths.data_root.join("diagram.png");
        fs::write(&source, b"png fixture").expect("source asset");
        let imported =
            import_project_media(&paths, &created.id, "images", source.to_str().unwrap())
                .expect("import");
        assert_eq!(imported.name, "diagram.png");
        assert_eq!(
            list_project_media(&paths, &created.id, "images")
                .unwrap()
                .len(),
            1
        );
        delete_project_media(&paths, &created.id, "images", &imported.name).expect("delete");
        assert!(list_project_media(&paths, &created.id, "images")
            .unwrap()
            .is_empty());
        let _ = fs::remove_dir_all(&paths.data_root);
    }

    #[test]
    fn new_project_has_phase_aware_brief_artifacts() {
        let paths = temp_paths();
        paths.ensure().expect("ensure");
        let created = create_project(&paths, "Lifecycle".to_string()).expect("create");
        let passport: serde_json::Value =
            serde_json::from_str(&created.files["passport"]).expect("passport json");
        let roadmap: serde_json::Value =
            serde_json::from_str(&created.files["roadmap"]).expect("roadmap json");

        assert_eq!(passport["schema_version"], 2);
        assert!(passport["production_path"].is_null());
        assert_eq!(roadmap["schema_version"], 2);
        assert_eq!(roadmap["current_phase"], "description");
        assert_eq!(roadmap["phases"][0]["id"], "project_creation");
        assert_eq!(roadmap["phases"][1]["id"], "description");
        assert_eq!(roadmap["phases"][2]["id"], "passport");
        for key in [
            "tape_content",
            "orchestration",
            "tts_narration",
            "tts_style",
            "audio_description",
            "custom_narration",
            "transcript",
            "timestamps",
        ] {
            assert!(
                created.files.contains_key(key),
                "missing lifecycle file {key}"
            );
        }
        assert!(paths
            .workspace_dir(&created.id)
            .join("brief/tapes/main.md")
            .is_file());
        let _ = fs::remove_dir_all(&paths.data_root);
    }

    #[test]
    fn open_migrates_legacy_brief_without_losing_source_documents() {
        let paths = temp_paths();
        paths.ensure().expect("ensure");
        let created = create_project(&paths, "Legacy brief".to_string()).expect("create");
        let workspace = paths.workspace_dir(&created.id);
        fs::remove_file(workspace.join("brief/tapes/main.md")).expect("remove new tape");
        fs::remove_file(workspace.join("brief/tts-narration.md")).expect("remove new narration");
        fs::write(workspace.join("brief/tape.md"), "# My legacy tape\n").expect("legacy tape");
        fs::write(
            workspace.join("brief/narration.md"),
            "# My legacy narration\n",
        )
        .expect("legacy narration");
        fs::write(
            workspace.join("brief/passport.json"),
            r#"{"title":"Legacy brief","status":"discovery","readiness":{"status":"needs_input","missing_fields":[]}}"#,
        )
        .expect("legacy passport");
        fs::write(
            workspace.join("brief/roadmap.json"),
            r#"{"current_phase":"concept","phases":[{"id":"concept"},{"id":"production"},{"id":"review"}]}"#,
        )
        .expect("legacy roadmap");

        let opened = open_project(&paths, &created.id).expect("open migrated");
        assert_eq!(opened.files["tape_content"], "# My legacy tape\n");
        assert_eq!(opened.files["tts_narration"], "# My legacy narration\n");
        let passport: serde_json::Value =
            serde_json::from_str(&opened.files["passport"]).expect("passport");
        let roadmap: serde_json::Value =
            serde_json::from_str(&opened.files["roadmap"]).expect("roadmap");
        assert_eq!(passport["schema_version"], 2);
        assert!(passport["production_path"].is_null());
        assert_eq!(roadmap["current_phase"], "description");
        assert_eq!(roadmap["legacy_roadmap"]["current_phase"], "concept");
        let _ = fs::remove_dir_all(&paths.data_root);
    }

    #[test]
    fn multiple_tape_content_files_roundtrip() {
        let paths = temp_paths();
        paths.ensure().expect("ensure");
        let created = create_project(&paths, "Multiple tapes".to_string()).expect("create");
        create_tape_content(&paths, &created.id, "comparison", "Comparison")
            .expect("create second tape");
        save_tape_content(
            &paths,
            &created.id,
            "comparison",
            "# Tape content — Comparison\n\n## beat-example\n",
        )
        .expect("save second tape");
        assert!(create_tape_content(&paths, &created.id, "../escape", "Escape").is_err());

        let reopened = open_project(&paths, &created.id).expect("reopen");
        assert!(reopened.tapes.contains_key("main"));
        assert_eq!(
            reopened.tapes["comparison"],
            "# Tape content — Comparison\n\n## beat-example\n"
        );
        let _ = fs::remove_dir_all(&paths.data_root);
    }
}
