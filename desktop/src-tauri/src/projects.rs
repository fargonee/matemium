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
const ROADMAP_TEMPLATE: &str = include_str!("../../../shared/templates/roadmap.json");
const NARRATION_TEMPLATE: &str = include_str!("../../../shared/templates/narration.md");

const PROJECT_FILES: [(&str, &str); 7] = [
    ("scenes", "scenes.py"),
    ("helpers", "helpers.py"),
    ("passport", "brief/passport.json"),
    ("description", "brief/description.md"),
    ("tape", "brief/tape.md"),
    ("roadmap", "brief/roadmap.json"),
    ("narration", "brief/narration.md"),
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
    pub project_json: serde_json::Value,
    pub renders_dir: String,
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

fn ensure_workspace_structure(workspace: &Path, project_name: &str) -> Result<(), String> {
    let helpers = workspace.join("helpers.py");
    let legacy_assets = workspace.join("assets.py");
    if !helpers.exists() && legacy_assets.is_file() {
        fs::rename(&legacy_assets, &helpers)
            .map_err(|e| format!("migrate assets.py to helpers.py: {e}"))?;
    }

    ensure_file(&helpers, HELPERS_TEMPLATE)?;
    let passport = PASSPORT_TEMPLATE.replace("Untitled project", project_name);
    ensure_file(&workspace.join("brief/passport.json"), &passport)?;
    ensure_file(
        &workspace.join("brief/description.md"),
        DESCRIPTION_TEMPLATE,
    )?;
    ensure_file(&workspace.join("brief/tape.md"), TAPE_TEMPLATE)?;
    ensure_file(&workspace.join("brief/roadmap.json"), ROADMAP_TEMPLATE)?;
    ensure_file(&workspace.join("brief/narration.md"), NARRATION_TEMPLATE)?;
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

    Ok(ProjectOpen {
        id: meta.id,
        name: meta.name,
        description: meta.description,
        scene_class: meta.scene_class,
        orientation: meta.orientation,
        files,
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

    if matches!(file, "passport" | "roadmap") {
        serde_json::from_str::<serde_json::Value>(content)
            .map_err(|e| format!("invalid JSON for {file}: {e}"))?;
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

        let opened = open_project(&paths, &created.id).expect("open");
        assert_eq!(opened.files["helpers"], "LEGACY_VALUE = 42\n");
        assert!(!workspace.join("assets.py").exists());
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
}
