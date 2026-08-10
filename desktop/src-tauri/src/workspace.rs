use std::collections::HashMap;
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
    /// Durable state and bounded artifacts for autonomous agent runs.
    pub agent_root: PathBuf,
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
    // LLM mode: external BYO provider keys or local models.
    #[serde(default)]
    pub use_personal_llm: Option<bool>,
    #[serde(default)]
    pub llm_provider: Option<String>,
    #[serde(default)]
    pub openrouter_api_key: Option<String>,
    #[serde(default)]
    pub openrouter_user_id: Option<String>,
    #[serde(default)]
    pub openrouter_connected_at: Option<String>,
    #[serde(default)]
    pub openrouter_free_disabled_until: Option<String>,
    #[serde(default)]
    pub openai_api_key: Option<String>,
    #[serde(default)]
    pub openai_connected_at: Option<String>,
    #[serde(default)]
    pub groq_api_key: Option<String>,
    #[serde(default)]
    pub groq_connected_at: Option<String>,
    #[serde(default)]
    pub xai_api_key: Option<String>,
    #[serde(default)]
    pub xai_connected_at: Option<String>,
    #[serde(default)]
    pub cerebras_api_key: Option<String>,
    #[serde(default)]
    pub cerebras_connected_at: Option<String>,
    #[serde(default)]
    pub github_api_key: Option<String>,
    #[serde(default)]
    pub github_connected_at: Option<String>,
    #[serde(default)]
    pub mistral_api_key: Option<String>,
    #[serde(default)]
    pub mistral_connected_at: Option<String>,
    #[serde(default)]
    pub gemini_api_key: Option<String>,
    #[serde(default)]
    pub gemini_connected_at: Option<String>,
    #[serde(default)]
    pub use_local_llm: Option<bool>,
    #[serde(default)]
    pub local_llm_model: Option<String>,
    #[serde(default)]
    pub external_llm_model: Option<String>,
    #[serde(default)]
    pub provider_models: HashMap<String, ProviderModelSettings>,
    #[serde(default)]
    pub reasoning_level: Option<String>,
    #[serde(default = "default_autonomous_agent")]
    pub use_autonomous_agent: Option<bool>,
    #[serde(default)]
    pub agent_runtime_version: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct ProviderModelSettings {
    #[serde(default)]
    pub pinned: Vec<String>,
    #[serde(default)]
    pub catalog: Vec<ProviderModel>,
    #[serde(default)]
    pub fetched_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProviderModel {
    pub id: String,
    pub name: String,
    pub provider: String,
    #[serde(default)]
    pub context_length: Option<u64>,
    #[serde(default)]
    pub pricing_label: Option<String>,
    #[serde(default)]
    pub badges: Vec<String>,
}

pub fn configured_server_url() -> String {
    let json_str = include_str!("../../app/src/config.json");
    let v: serde_json::Value = serde_json::from_str(json_str).expect("invalid config.json");
    v["serverUrl"]
        .as_str()
        .expect("missing serverUrl in config.json")
        .to_string()
}

fn default_server_url() -> String {
    configured_server_url()
}

fn migrate_legacy_server_url(settings: &mut Settings) -> bool {
    let current = settings.server_url.trim().trim_end_matches('/');
    let configured = configured_server_url();
    if current == configured.trim_end_matches('/') {
        return false;
    }
    if matches!(
        current,
        "http://127.0.0.1:8080" | "http://localhost:8080"
    ) {
        settings.server_url = configured;
        return true;
    }
    false
}

fn default_bottom_dock_default() -> String {
    "progress".to_string()
}

fn default_autonomous_agent() -> Option<bool> {
    Some(true)
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            server_url: default_server_url(),
            api_token: None,
            bottom_dock_default: default_bottom_dock_default(),
            use_personal_llm: Some(true),
            llm_provider: Some("openrouter".to_string()),
            openrouter_api_key: None,
            openrouter_user_id: None,
            openrouter_connected_at: None,
            openrouter_free_disabled_until: None,
            openai_api_key: None,
            openai_connected_at: None,
            groq_api_key: None,
            groq_connected_at: None,
            xai_api_key: None,
            xai_connected_at: None,
            cerebras_api_key: None,
            cerebras_connected_at: None,
            github_api_key: None,
            github_connected_at: None,
            mistral_api_key: None,
            mistral_connected_at: None,
            gemini_api_key: None,
            gemini_connected_at: None,
            use_local_llm: Some(false),
            local_llm_model: Some("llm-qwen-coder-3b-q4".to_string()),
            external_llm_model: Some("openai/gpt-4o-mini".to_string()),
            provider_models: HashMap::new(),
            reasoning_level: Some("low".to_string()),
            use_autonomous_agent: Some(true),
            agent_runtime_version: Some("aider-v1".to_string()),
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
        let agent_root = data_root.join("agent");

        Ok(Self {
            workspaces_root: data_root.join("workspaces"),
            settings_path: config_dir.join("settings.json"),
            data_root,
            config_dir,
            assets_root,
            agent_root,
        })
    }

    pub fn ensure(&self) -> Result<(), String> {
        for dir in [
            &self.data_root,
            &self.workspaces_root,
            &self.config_dir,
            &self.assets_root,
            &self.agent_root,
        ] {
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

    pub fn helpers_path(&self, project_id: &str) -> PathBuf {
        self.workspace_dir(project_id).join("helpers.py")
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

    pub fn agent_runs_db_path(&self) -> PathBuf {
        self.agent_root.join("agent-runs.sqlite3")
    }

    pub fn agent_run_artifacts_dir(&self, run_id: &str) -> PathBuf {
        self.agent_root.join("runs").join(run_id)
    }

    pub fn load_settings(&self) -> Result<Settings, String> {
        if !self.settings_path.exists() {
            return Ok(Settings::default());
        }
        let raw =
            fs::read_to_string(&self.settings_path).map_err(|e| format!("read settings: {e}"))?;
        let mut settings: Settings =
            serde_json::from_str(&raw).map_err(|e| format!("parse settings: {e}"))?;
        if migrate_legacy_server_url(&mut settings) {
            self.save_settings(&settings)?;
        }
        Ok(settings)
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
    let raw = fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
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

    #[test]
    fn migrates_legacy_local_auth_server_to_configured_cloud() {
        let mut settings = Settings {
            server_url: "http://127.0.0.1:8080".to_string(),
            ..Settings::default()
        };
        assert!(migrate_legacy_server_url(&mut settings));
        assert_eq!(settings.server_url, configured_server_url());
    }

    #[test]
    fn preserves_non_legacy_custom_server() {
        let mut settings = Settings {
            server_url: "http://127.0.0.1:9080".to_string(),
            ..Settings::default()
        };
        assert!(!migrate_legacy_server_url(&mut settings));
        assert_eq!(settings.server_url, "http://127.0.0.1:9080");
    }
}
