use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

const APP_NAME: &str = "matemium";

#[derive(Debug, Clone)]
pub struct AppPaths {
    pub data_root: PathBuf,
    pub workspaces_root: PathBuf,
    pub config_dir: PathBuf,
    pub settings_path: PathBuf,
    /// Root for first-run assets (TinyTeX, embeddings, etc.)
    pub assets_root: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Settings {
    #[serde(default = "default_server_url")]
    pub server_url: String,
    #[serde(default)]
    pub api_token: Option<String>,
    #[serde(default = "default_bottom_dock_default")]
    pub bottom_dock_default: String,
    // LLM mode: personal (BYO keys from web profile) vs platform credits
    #[serde(default)]
    pub use_personal_llm: Option<bool>,
    #[serde(default)]
    pub llm_provider: Option<String>,
    #[serde(default)]
    pub use_local_llm: Option<bool>,
    #[serde(default)]
    pub local_llm_model: Option<String>,
    #[serde(default)]
    pub external_llm_model: Option<String>,
    #[serde(default)]
    pub reasoning_level: Option<String>,
}

fn default_server_url() -> String {
    let json_str = include_str!("../../app/src/config.json");
    let v: serde_json::Value = serde_json::from_str(json_str).expect("invalid config.json");
    v["serverUrl"].as_str().expect("missing serverUrl in config.json").to_string()
}

fn default_bottom_dock_default() -> String {
    "progress".to_string()
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            server_url: default_server_url(),
            api_token: None,
            bottom_dock_default: default_bottom_dock_default(),
            use_personal_llm: Some(false),
            llm_provider: Some("openai".to_string()),
            use_local_llm: Some(false),
            local_llm_model: Some("llm-qwen-coder-3b-q4".to_string()),
            external_llm_model: Some("gpt-4o-mini".to_string()),
            reasoning_level: Some("low".to_string()),
        }
    }
}

impl AppPaths {
    pub fn resolve() -> Result<Self, String> {
        let data_root = dirs::data_local_dir()
            .ok_or_else(|| "could not resolve local data directory".to_string())?
            .join(APP_NAME);
        let config_dir = dirs::config_dir()
            .ok_or_else(|| "could not resolve config directory".to_string())?
            .join(APP_NAME);

        let assets_root = data_root.join("assets");

        Ok(Self {
            workspaces_root: data_root.join("workspaces"),
            settings_path: config_dir.join("settings.json"),
            data_root,
            config_dir,
            assets_root,
        })
    }

    pub fn ensure(&self) -> Result<(), String> {
        for dir in [&self.data_root, &self.workspaces_root, &self.config_dir, &self.assets_root] {
            fs::create_dir_all(dir).map_err(|e| format!("create {}: {e}", dir.display()))?;
        }
        if !self.settings_path.exists() {
            let settings = Settings::default();
            write_json(&self.settings_path, &settings)?;
        }
        Ok(())
    }

    pub fn workspace_dir(&self, project_id: &str) -> PathBuf {
        self.workspaces_root.join(project_id)
    }

    pub fn scenes_path(&self, project_id: &str) -> PathBuf {
        self.workspace_dir(project_id).join("scenes.py")
    }

    pub fn assets_path(&self, project_id: &str) -> PathBuf {
        self.workspace_dir(project_id).join("assets.py")
    }

    pub fn project_json_path(&self, project_id: &str) -> PathBuf {
        self.workspace_dir(project_id).join("project.json")
    }

    pub fn conversations_path(&self, project_id: &str) -> PathBuf {
        self.workspace_dir(project_id).join("conversations.json")
    }

    pub fn renders_dir(&self, project_id: &str) -> PathBuf {
        self.workspace_dir(project_id).join("renders")
    }

    /// Stable Manim cache root (``<workspace>/media``), separate from preview exports.
    pub fn project_media_dir(&self, project_id: &str) -> PathBuf {
        self.workspace_dir(project_id).join("media")
    }

    /// Base dir for downloaded/extracted assets (e.g. tinytex/)
    pub fn assets_dir(&self) -> &PathBuf {
        &self.assets_root
    }

    /// TinyTeX install location (extracted)
    pub fn tinytex_dir(&self) -> PathBuf {
        self.assets_root.join("tinytex")
    }

    /// Path to the local asset state file
    pub fn assets_state_path(&self) -> PathBuf {
        self.assets_root.join("assets.json")
    }

    pub fn load_settings(&self) -> Result<Settings, String> {
        if !self.settings_path.exists() {
            return Ok(Settings::default());
        }
        let raw = fs::read_to_string(&self.settings_path)
            .map_err(|e| format!("read settings: {e}"))?;
        serde_json::from_str(&raw).map_err(|e| format!("parse settings: {e}"))
    }

    pub fn save_settings(&self, settings: &Settings) -> Result<(), String> {
        write_json(&self.settings_path, settings)
    }
}

pub fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    let raw = serde_json::to_string_pretty(value).map_err(|e| format!("serialize json: {e}"))?;
    fs::write(path, raw).map_err(|e| format!("write {}: {e}", path.display()))
}

pub fn read_json_file(path: &Path) -> Result<serde_json::Value, String> {
    let raw =
        fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    serde_json::from_str(&raw).map_err(|e| format!("parse {}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolve_paths_under_matemium_namespace() {
        let paths = AppPaths::resolve().expect("resolve");
        assert!(paths.data_root.ends_with("matemium"));
        assert!(paths.workspaces_root.ends_with("workspaces"));
        assert!(paths.settings_path.ends_with("matemium/settings.json"));
    }
}