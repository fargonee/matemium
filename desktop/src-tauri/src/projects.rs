use std::fs;
use std::path::{Component, Path};
use std::time::SystemTime;

use chrono::Utc;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::workspace::{read_json_file, write_json, AppPaths};

const SCENES_TEMPLATE: &str = include_str!("../../../shared/templates/scenes.py");
const ASSETS_TEMPLATE: &str = include_str!("../../../shared/templates/assets.py");

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

fn is_rendered_mp4(path: &Path) -> bool {
    path.extension().and_then(|ext| ext.to_str()) == Some("mp4")
        && !path.components().any(|part| {
            matches!(part, Component::Normal(name) if name == "partial_movie_files")
        })
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
    pub scenes_path: String,
    pub scenes_content: String,
    pub assets_path: String,
    pub assets_content: String,
    pub project_json: serde_json::Value,
    pub renders_dir: String,
}

pub fn list_projects(paths: &AppPaths) -> Result<Vec<ProjectSummary>, String> {
    if !paths.workspaces_root.exists() {
        return Ok(Vec::new());
    }

    let mut projects = Vec::new();
    for entry in fs::read_dir(&paths.workspaces_root)
        .map_err(|e| format!("read workspaces: {e}"))?
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
    fs::create_dir_all(paths.renders_dir(&id))
        .map_err(|e| format!("create renders dir: {e}"))?;

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
    fs::write(paths.assets_path(&id), ASSETS_TEMPLATE)
        .map_err(|e| format!("write assets.py: {e}"))?;

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
    let scenes_content = fs::read_to_string(&scenes_path)
        .map_err(|e| format!("read scenes.py: {e}"))?;
    let assets_path = paths.assets_path(project_id);
    let assets_content = if assets_path.is_file() {
        fs::read_to_string(&assets_path).map_err(|e| format!("read assets.py: {e}"))?
    } else {
        String::new()
    };
    let project_json = read_json_file(&project_json_path)?;

    Ok(ProjectOpen {
        id: meta.id,
        name: meta.name,
        description: meta.description,
        scene_class: meta.scene_class,
        orientation: meta.orientation,
        scenes_path: scenes_path.display().to_string(),
        scenes_content,
        assets_path: assets_path.display().to_string(),
        assets_content,
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

pub fn save_assets(paths: &AppPaths, project_id: &str, content: &str) -> Result<(), String> {
    let workspace = paths.workspace_dir(project_id);
    if !workspace.is_dir() {
        return Err(format!("project not found: {project_id}"));
    }

    fs::write(paths.assets_path(project_id), content)
        .map_err(|e| format!("write assets.py: {e}"))?;
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
        }
    }

    #[test]
    fn create_open_delete_project_roundtrip() {
        let paths = temp_paths();
        paths.ensure().expect("ensure");
        let created = create_project(&paths, "Quadratic".to_string()).expect("create");
        assert_eq!(created.name, "Quadratic");
        assert!(created.scenes_content.contains("CanvasBuilder"));

        let listed = list_projects(&paths).expect("list");
        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].name, "Quadratic");

        save_scenes(&paths, &created.id, "# updated\n").expect("save");
        let opened = open_project(&paths, &created.id).expect("open");
        assert_eq!(opened.scenes_content, "# updated\n");

        delete_project(&paths, &created.id).expect("delete");
        assert!(list_projects(&paths).unwrap().is_empty());
        let _ = fs::remove_dir_all(&paths.data_root);
    }
}