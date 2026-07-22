use std::io::{Read, Write};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use std::time::Duration;

use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
use chrono::{DateTime, Duration as ChronoDuration, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use tauri::{AppHandle, Manager, State};
use tauri_plugin_opener::OpenerExt;

use crate::cloud::{ChatCompletionRequest, ChatMessage, PublishRequest, PublishResponse};
use crate::media_preview::playback_path_for_media;
use crate::outputs::{
    clear_render_cache, delete_output, list_outputs, validate_output_path,
    validate_project_workspace_path, validate_render_output_dir, OutputPathScope,
};
use crate::projects::{
    create_project, delete_project, delete_project_media, import_project_media, list_project_media,
    list_projects, open_project, save_project_file, save_scenes, workspace_path,
};
use crate::state::{AppState, OpenRouterOAuthSession};
use crate::workspace::{ProviderModelSettings, Settings};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectCreateParams {
    pub name: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectIdParams {
    pub project_id: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentRunIdParams {
    pub run_id: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentRunEventsParams {
    pub run_id: String,
    pub after_sequence: Option<u64>,
    pub limit: Option<usize>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentRunCancelParams {
    pub run_id: String,
    pub reason: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentRunApprovalParams {
    pub run_id: String,
    pub action_id: String,
    pub approved: bool,
    pub note: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentRunInputParams {
    pub run_id: String,
    pub content: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct OpenRouterConnectionStatus {
    pub connected: bool,
    pub user_id: Option<String>,
    pub connected_at: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct OpenRouterConnectStart {
    pub auth_url: String,
    pub callback_url: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProviderModelsParams {
    pub provider: String,
    #[serde(default)]
    pub refresh: Option<bool>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectSaveParams {
    pub project_id: String,
    pub content: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectSaveFileParams {
    pub project_id: String,
    pub file: String,
    pub content: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectMediaParams {
    pub project_id: String,
    pub category: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectMediaImportParams {
    pub project_id: String,
    pub category: String,
    pub source: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectMediaDeleteParams {
    pub project_id: String,
    pub category: String,
    pub name: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SidecarCheckParams {
    pub project_id: String,
    pub scene: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SidecarRenderParams {
    pub project_id: String,
    pub scene: Option<String>,
    #[serde(default = "default_quality")]
    pub quality: String,
    #[serde(default = "default_orientation")]
    pub orientation: String,
    pub output_dir: Option<String>,
}

fn default_quality() -> String {
    "preview".to_string()
}

fn default_orientation() -> String {
    "portrait".to_string()
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AuthLoginParams {
    pub email: String,
    pub password: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AuthSessionParams {
    pub access_token: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CloudChatParams {
    pub messages: Vec<ChatMessage>,
    pub project_id: Option<String>,
    pub conversation_id: Option<String>,
    pub scenes_excerpt: Option<String>,
    // LLM selection flags (passed through to server for BYO/local provider choice)
    pub llm_provider: Option<String>,
    pub use_personal_llm: Option<bool>,
    pub model: Option<String>,
    pub use_autonomous_agent: Option<bool>,
    pub agent_runtime_version: Option<String>,
}

#[tauri::command]
pub async fn project_list(state: State<'_, AppState>) -> Result<Value, String> {
    let projects = list_projects(&state.paths)?;
    serde_json::to_value(projects).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn project_create(
    state: State<'_, AppState>,
    params: ProjectCreateParams,
) -> Result<Value, String> {
    let readiness = get_readiness(state.clone()).await?;
    if !readiness.fully_ready {
        return Err(format!("APP_NOT_READY: {}", readiness.message));
    }
    let project = create_project(&state.paths, params.name)?;
    serde_json::to_value(project).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn project_open(
    state: State<'_, AppState>,
    params: ProjectIdParams,
) -> Result<Value, String> {
    let project = open_project(&state.paths, &params.project_id)?;
    serde_json::to_value(project).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn project_save(
    state: State<'_, AppState>,
    params: ProjectSaveParams,
) -> Result<(), String> {
    let readiness = get_readiness(state.clone()).await?;
    if !readiness.fully_ready {
        return Err(format!("APP_NOT_READY: {}", readiness.message));
    }
    save_scenes(&state.paths, &params.project_id, &params.content)
}

#[tauri::command]
pub async fn project_save_file(
    state: State<'_, AppState>,
    params: ProjectSaveFileParams,
) -> Result<(), String> {
    save_project_file(
        &state.paths,
        &params.project_id,
        &params.file,
        &params.content,
    )
}

#[tauri::command]
pub async fn project_list_media(
    state: State<'_, AppState>,
    params: ProjectMediaParams,
) -> Result<Value, String> {
    serde_json::to_value(list_project_media(
        &state.paths,
        &params.project_id,
        &params.category,
    )?)
    .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn project_import_media(
    state: State<'_, AppState>,
    params: ProjectMediaImportParams,
) -> Result<Value, String> {
    serde_json::to_value(import_project_media(
        &state.paths,
        &params.project_id,
        &params.category,
        &params.source,
    )?)
    .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn project_delete_media(
    state: State<'_, AppState>,
    params: ProjectMediaDeleteParams,
) -> Result<(), String> {
    delete_project_media(
        &state.paths,
        &params.project_id,
        &params.category,
        &params.name,
    )
}

#[tauri::command]
pub async fn project_delete(
    state: State<'_, AppState>,
    params: ProjectIdParams,
) -> Result<(), String> {
    delete_project(&state.paths, &params.project_id)
}

#[tauri::command]
pub async fn sidecar_ping(state: State<'_, AppState>) -> Result<Value, String> {
    state.sidecar.request("ping", json!({})).await
}

/// Tell the sidecar where first-run assets (e.g. TinyTeX) live.
/// Called early by desktop before heavy engine commands (PAD Phase 2+).
#[tauri::command]
pub async fn sidecar_configure_assets(
    state: State<'_, AppState>,
    tinytex_dir: Option<String>,
) -> Result<Value, String> {
    let mut params = serde_json::Map::new();
    if let Some(dir) = tinytex_dir {
        params.insert("tinytex_dir".to_string(), json!(dir));
    }
    state
        .sidecar
        .request("configure_assets", Value::Object(params))
        .await
}

#[tauri::command]
pub async fn get_asset_status(
    state: State<'_, AppState>,
    asset_id: Option<String>,
) -> Result<Value, String> {
    let statuses = state.assets.get_status(asset_id.as_deref());
    serde_json::to_value(statuses).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn start_asset_download(
    state: State<'_, AppState>,
    app: AppHandle,
    asset_id: String,
) -> Result<(), String> {
    let assets = state.assets.clone();

    // Spawn non-blocking background task to handle connection stream and range resuming
    tokio::spawn(async move {
        let res = assets.start_download(app.clone(), &asset_id, None).await;

        match res {
            Ok(_) => {
                if asset_id == "tinytex-linux" {
                    if let Some(state) = app.try_state::<AppState>() {
                        if let Some(bin_dir) = assets.tinytex_bin_dir() {
                            let _ = state
                                .sidecar
                                .request(
                                    "configure_assets",
                                    json!({ "tinytex_dir": bin_dir.to_string_lossy().to_string() }),
                                )
                                .await;
                        }
                    }
                }
            }
            Err(e) => {
                // Safely update the persisted state with the error and notify the frontend
                assets.set_error(&asset_id, &e, &app);
            }
        }
    });

    Ok(())
}

#[tauri::command]
pub async fn pause_asset_download(
    state: State<'_, AppState>,
    asset_id: String,
) -> Result<(), String> {
    state.assets.pause_download(&asset_id);
    Ok(())
}

#[tauri::command]
pub async fn cancel_asset_download(
    state: State<'_, AppState>,
    asset_id: String,
) -> Result<(), String> {
    state.assets.cancel_download(&asset_id);
    Ok(())
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Readiness {
    pub phase: String,
    pub assets_ready: bool,
    pub engine_ready: bool,
    pub intelligence_ready: bool,
    pub fully_ready: bool,
    pub message: String,
    pub engine_phase: Option<String>,
}

#[tauri::command]
pub async fn get_readiness(state: State<'_, AppState>) -> Result<Readiness, String> {
    let asset_statuses = state.assets.get_status(None);
    let tinytex_ready = asset_statuses
        .iter()
        .any(|a| a.id == "tinytex-linux" && a.downloaded && a.verified)
        || state.assets.tinytex_bin_dir().is_some();

    let engine_status = state
        .sidecar
        .request("get_status", json!({}))
        .await
        .unwrap_or(json!({}));
    let engine_phase = engine_status
        .get("phase")
        .and_then(|v| v.as_str())
        .unwrap_or("CORE_READY")
        .to_string();
    let engine_ready = engine_phase == "ENGINE_READY" || engine_phase.contains("READY");
    let intelligence_ready = engine_status
        .get("intelligence_ready")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
        || engine_phase.contains("INTELLIGENCE_READY");

    let fully_ready = tinytex_ready && engine_ready;

    let (phase, message) = if !tinytex_ready {
        (
            "assets".to_string(),
            "Downloading Local Code Intelligence assets (TinyTeX)...".to_string(),
        )
    } else if !engine_ready {
        (
            "engine".to_string(),
            "Loading Manim / canvas engine...".to_string(),
        )
    } else {
        ("ready".to_string(), "Ready".to_string())
    };

    Ok(Readiness {
        phase,
        assets_ready: tinytex_ready,
        engine_ready,
        intelligence_ready,
        fully_ready,
        message,
        engine_phase: Some(engine_phase),
    })
}

#[tauri::command]
pub async fn sidecar_retrieve(
    state: State<'_, AppState>,
    project_id: String,
    query: String,
    top_k: Option<u32>,
    files: Option<Vec<String>>,
) -> Result<Value, String> {
    let workspace = workspace_path(&state.paths, &project_id)?;
    let index_files = files.unwrap_or_else(|| {
        vec![
            "scenes.py".to_string(),
            "helpers.py".to_string(),
            "brief/passport.json".to_string(),
            "brief/description.md".to_string(),
            "brief/tape.md".to_string(),
            "brief/roadmap.json".to_string(),
            "brief/narration.md".to_string(),
        ]
    });
    state
        .sidecar
        .request(
            "retrieve",
            json!({
                "workspace": workspace,
                "query": query,
                "top_k": top_k.unwrap_or(8),
                "files": index_files,
            }),
        )
        .await
}

#[tauri::command]
pub async fn sidecar_upload_reference(
    state: State<'_, AppState>,
    project_id: String,
    file_name: String,
    file_content_base64: Option<String>,
    file_content_text: Option<String>,
) -> Result<Value, String> {
    let workspace = workspace_path(&state.paths, &project_id)?;
    state
        .sidecar
        .request(
            "upload_reference",
            json!({
                "workspace": workspace,
                "file_name": file_name,
                "file_content_base64": file_content_base64,
                "file_content_text": file_content_text,
            }),
        )
        .await
}

#[tauri::command]
pub async fn sidecar_list_references(
    state: State<'_, AppState>,
    project_id: String,
) -> Result<Value, String> {
    let workspace = workspace_path(&state.paths, &project_id)?;
    state
        .sidecar
        .request(
            "list_references",
            json!({
                "workspace": workspace,
            }),
        )
        .await
}

#[tauri::command]
pub async fn sidecar_delete_reference(
    state: State<'_, AppState>,
    project_id: String,
    file_name: String,
) -> Result<Value, String> {
    let workspace = workspace_path(&state.paths, &project_id)?;
    state
        .sidecar
        .request(
            "delete_reference",
            json!({
                "workspace": workspace,
                "file_name": file_name,
            }),
        )
        .await
}

#[tauri::command]
pub async fn sidecar_get_reference_content(
    state: State<'_, AppState>,
    project_id: String,
    file_name: String,
) -> Result<Value, String> {
    let workspace = workspace_path(&state.paths, &project_id)?;
    state
        .sidecar
        .request(
            "get_reference_content",
            json!({
                "workspace": workspace,
                "file_name": file_name,
            }),
        )
        .await
}

#[tauri::command]
pub async fn sidecar_lint(
    state: State<'_, AppState>,
    params: ProjectIdParams,
) -> Result<Value, String> {
    let readiness = get_readiness(state.clone()).await?;
    if !readiness.fully_ready {
        return Err(format!("APP_NOT_READY: {}", readiness.message));
    }
    let workspace = workspace_path(&state.paths, &params.project_id)?;
    state
        .sidecar
        .request(
            "lint_project",
            json!({
                "workspace": workspace,
            }),
        )
        .await
}

#[tauri::command]
pub async fn sidecar_check(
    state: State<'_, AppState>,
    params: SidecarCheckParams,
) -> Result<Value, String> {
    let readiness = get_readiness(state.clone()).await?;
    if !readiness.fully_ready {
        return Err(format!("APP_NOT_READY: {}", readiness.message));
    }
    let workspace = workspace_path(&state.paths, &params.project_id)?;
    let mut ipc_params = json!({ "workspace": workspace });
    if let Some(scene) = params.scene {
        ipc_params["scene"] = json!(scene);
    }
    state.sidecar.request("check_project", ipc_params).await
}

#[tauri::command]
pub async fn sidecar_list_scenes(
    state: State<'_, AppState>,
    params: ProjectIdParams,
) -> Result<Value, String> {
    let workspace = workspace_path(&state.paths, &params.project_id)?;
    state
        .sidecar
        .request(
            "list_scenes",
            json!({
                "workspace": workspace,
            }),
        )
        .await
}

#[tauri::command]
pub async fn sidecar_render(
    state: State<'_, AppState>,
    params: SidecarRenderParams,
) -> Result<Value, String> {
    let readiness = get_readiness(state.clone()).await?;
    if !readiness.fully_ready {
        return Err(format!("APP_NOT_READY: {}", readiness.message));
    }
    let workspace = workspace_path(&state.paths, &params.project_id)?;
    let output_dir = if let Some(raw) = params.output_dir.as_deref() {
        validate_render_output_dir(raw)?
    } else {
        let dir = state.paths.renders_dir(&params.project_id);
        validate_render_output_dir(&dir.display().to_string())?
    };

    let mut ipc_params = json!({
        "workspace": workspace,
        "quality": params.quality,
        "orientation": params.orientation,
        "output_dir": output_dir.display().to_string(),
    });
    if let Some(scene) = params.scene {
        ipc_params["scene"] = json!(scene);
    }

    state.sidecar.request("render_project", ipc_params).await
}

#[tauri::command]
pub async fn sidecar_cancel(state: State<'_, AppState>) -> Result<(), String> {
    state.sidecar.cancel_active().await
}

#[tauri::command]
pub fn agent_run_list(state: State<'_, AppState>) -> Result<Value, String> {
    let runs = state
        .agent_runs
        .list_runs(100)
        .map_err(|error| error.to_string())?;
    serde_json::to_value(runs).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn agent_run_get(
    state: State<'_, AppState>,
    params: AgentRunIdParams,
) -> Result<Value, String> {
    let run = state
        .agent_runs
        .load_run(&params.run_id)
        .map_err(|error| error.to_string())?;
    serde_json::to_value(run).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn agent_run_events(
    state: State<'_, AppState>,
    params: AgentRunEventsParams,
) -> Result<Value, String> {
    let events = state
        .agent_runs
        .list_stream_events(
            &params.run_id,
            params.after_sequence.unwrap_or(0),
            params.limit.unwrap_or(200),
        )
        .map_err(|error| error.to_string())?;
    serde_json::to_value(events).map_err(|error| error.to_string())
}

#[tauri::command]
pub async fn agent_run_cancel(
    state: State<'_, AppState>,
    params: AgentRunCancelParams,
) -> Result<Value, String> {
    let run = state
        .agent_runs
        .load_run(&params.run_id)
        .map_err(|error| error.to_string())?;
    if run.status.is_terminal() {
        return Err("completed, failed, and cancelled runs cannot be cancelled again".into());
    }
    let workspace = state.paths.workspace_dir(&run.project_id);
    let reason = params
        .reason
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| "User requested cancellation".into());
    let cancelled = state
        .agent_runs
        .cancel(&params.run_id, &reason, &workspace)
        .map_err(|error| error.to_string())?;
    let _ = state.sidecar.cancel_active().await;
    state
        .agent_runs
        .append_stream_event(
            "run_cancelled",
            &params.run_id,
            &json!({"reason": reason, "budgets": cancelled.budgets, "usage": cancelled.usage}),
        )
        .map_err(|error| error.to_string())?;
    serde_json::to_value(cancelled).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn agent_run_resume(
    state: State<'_, AppState>,
    params: AgentRunIdParams,
) -> Result<Value, String> {
    let run = state
        .agent_runs
        .load_run(&params.run_id)
        .map_err(|error| error.to_string())?;
    if run.status.is_terminal() {
        return Err("completed, failed, and cancelled runs cannot be resumed".into());
    }
    let workspace = state.paths.workspace_dir(&run.project_id);
    let resumed = state
        .agent_runs
        .resume(&params.run_id, &workspace)
        .map_err(|error| error.to_string())?;
    state
        .agent_runs
        .append_stream_event(
            "run_resumed",
            &params.run_id,
            &json!({"status": resumed.status, "budgets": resumed.budgets, "usage": resumed.usage}),
        )
        .map_err(|error| error.to_string())?;
    serde_json::to_value(resumed).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn agent_run_approve(
    state: State<'_, AppState>,
    params: AgentRunApprovalParams,
) -> Result<Value, String> {
    if params.action_id.trim().is_empty() {
        return Err("action_id is required".into());
    }
    let events = state
        .agent_runs
        .list_stream_events(&params.run_id, 0, 500)
        .map_err(|error| error.to_string())?;
    let requested = events.iter().any(|event| {
        event.event_type == "approval_requested"
            && event.payload.get("action_id").and_then(Value::as_str)
                == Some(params.action_id.as_str())
    });
    if !requested {
        return Err("no matching approval request exists for this run".into());
    }
    let event = state
        .agent_runs
        .append_stream_event(
            "approval_recorded",
            &params.run_id,
            &json!({"action_id": params.action_id, "approved": params.approved, "note": params.note}),
        )
        .map_err(|error| error.to_string())?;
    serde_json::to_value(event).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn agent_run_provide_input(
    state: State<'_, AppState>,
    params: AgentRunInputParams,
) -> Result<Value, String> {
    if params.content.trim().is_empty() || params.content.len() > 16 * 1024 {
        return Err("input must contain 1-16384 bytes".into());
    }
    let run = state
        .agent_runs
        .load_run(&params.run_id)
        .map_err(|error| error.to_string())?;
    if run.status != crate::agent_runs::RunStatus::Blocked {
        return Err("input can only resume a blocked run".into());
    }
    let workspace = state.paths.workspace_dir(&run.project_id);
    let updated = state
        .agent_runs
        .transition(
            &params.run_id,
            crate::agent_runs::RunStatus::Planning,
            None,
            &workspace,
        )
        .map_err(|error| error.to_string())?;
    let input_memory = crate::agent_context::ContextMemoryItem::new(
        &params.run_id,
        updated.sequence,
        crate::agent_context::ContextItemKind::Fact,
        crate::agent_context::ContextResolution::Resolved,
        "user_input",
        "User supplied the information required to continue the blocked run.",
        json!({"content": params.content.clone()}),
        true,
    )
    .map_err(|error| error.to_string())?;
    state
        .agent_runs
        .add_context_item(&input_memory)
        .map_err(|error| error.to_string())?;
    state
        .agent_runs
        .append_stream_event(
            "input_received",
            &params.run_id,
            &json!({"content": params.content, "status": updated.status}),
        )
        .map_err(|error| error.to_string())?;
    serde_json::to_value(updated).map_err(|error| error.to_string())
}

#[tauri::command]
pub async fn sidecar_get_preview_data(
    state: State<'_, AppState>,
    params: ProjectIdParams,
) -> Result<Value, String> {
    let readiness = get_readiness(state.clone()).await?;
    if !readiness.fully_ready {
        return Err(format!("APP_NOT_READY: {}", readiness.message));
    }
    let workspace = workspace_path(&state.paths, &params.project_id)?;
    state
        .sidecar
        .request("get_preview_data", json!({ "workspace": workspace }))
        .await
}

/// Shared body for the `auth_login` Tauri command (testable without the runtime).
pub async fn auth_login_inner(
    paths: &crate::workspace::AppPaths,
    email: &str,
    password: &str,
) -> Result<String, String> {
    let settings = paths.load_settings()?;
    crate::cloud::login(&settings, email, password).await
}

#[tauri::command]
pub async fn auth_login(
    state: State<'_, AppState>,
    params: AuthLoginParams,
) -> Result<Value, String> {
    let token = auth_login_inner(&state.paths, &params.email, &params.password).await?;
    serde_json::to_value(serde_json::json!({ "accessToken": token })).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn auth_session(
    state: State<'_, AppState>,
    params: AuthSessionParams,
) -> Result<Value, String> {
    let settings = state.paths.load_settings()?;
    let token = crate::cloud::login_with_session(&settings, &params.access_token).await?;
    serde_json::to_value(serde_json::json!({ "accessToken": token })).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn cloud_chat(
    state: State<'_, AppState>,
    params: CloudChatParams,
) -> Result<Value, String> {
    let readiness = get_readiness(state.clone()).await?;
    if !readiness.fully_ready {
        return Err(format!("APP_NOT_READY: {}", readiness.message));
    }
    let settings = state.paths.load_settings()?;

    let use_local_llm = settings.use_local_llm.unwrap_or(false);
    let use_autonomous_agent = params
        .use_autonomous_agent
        .or(settings.use_autonomous_agent)
        .unwrap_or(false);
    let should_use_agent = use_autonomous_agent
        && params.project_id.is_some()
        && looks_like_workspace_task_request(&params.messages);

    if should_use_agent {
        if use_local_llm {
            // This also respawns and reconfigures the sidecar after an OOM/crash,
            // so the next prompt still uses the model selected in Settings.
            sync_sidecar_llm_config(&state).await?;
        }
        let workspace = params
            .project_id
            .as_ref()
            .map(|project_id| workspace_path(&state.paths, project_id))
            .transpose()?;
        let sidecar_params = serde_json::json!({
            "messages": params.messages,
            "scenes_excerpt": params.scenes_excerpt.unwrap_or_default(),
            "workspace": workspace,
            "model": params.model.clone().or_else(|| settings.external_llm_model.clone()),
            "llm_provider": params.llm_provider.clone().or_else(|| settings.llm_provider.clone()),
            "openrouter_api_key": settings.openrouter_api_key,
            "openai_api_key": settings.openai_api_key,
            "groq_api_key": settings.groq_api_key,
            "xai_api_key": settings.xai_api_key,
            "use_personal_llm": params.use_personal_llm.or(settings.use_personal_llm),
            "use_local_llm": use_local_llm,
            "use_autonomous_agent": true,
            "agent_runtime_version": "aider-v1",
        });
        return state.sidecar.request("local_chat", sidecar_params).await;
    }

    if use_local_llm {
        // This also respawns and reconfigures the sidecar after an OOM/crash,
        // so the next prompt still uses the model selected in Settings.
        sync_sidecar_llm_config(&state).await?;
        let sidecar_params = serde_json::json!({
            "messages": params.messages,
            "scenes_excerpt": params.scenes_excerpt.unwrap_or_default(),
            "model": params.model,
            "use_local_llm": true,
        });
        return state.sidecar.request("local_chat", sidecar_params).await;
    }

    let request = ChatCompletionRequest {
        messages: params.messages,
        project_id: params.project_id,
        conversation_id: params.conversation_id,
        scenes_excerpt: params.scenes_excerpt,
        llm_provider: params.llm_provider,
        use_personal_llm: params.use_personal_llm,
        model: params.model,
        use_autonomous_agent: params.use_autonomous_agent,
        agent_runtime_version: params.agent_runtime_version,
    };
    if is_openrouter_free_request(&settings, &request) {
        if let Some(until) = active_free_disabled_until(&settings) {
            return Err(format!(
                "OpenRouter free model quota is exhausted until {}.",
                until.to_rfc3339()
            ));
        }
    }
    let response = match crate::cloud::external_provider_chat(&settings, request).await {
        Ok(response) => response,
        Err(error) if error.starts_with("OPENROUTER_FREE_RATE_LIMITED:") => {
            let retry_secs = error
                .trim_start_matches("OPENROUTER_FREE_RATE_LIMITED:")
                .parse::<i64>()
                .unwrap_or(0);
            let until = if retry_secs > 0 {
                Utc::now() + ChronoDuration::seconds(retry_secs)
            } else {
                next_utc_midnight()
            };
            let mut next_settings = settings.clone();
            next_settings.openrouter_free_disabled_until = Some(until.to_rfc3339());
            state.paths.save_settings(&next_settings)?;
            return Err(format!(
                "OpenRouter free model quota is exhausted until {}.",
                until.to_rfc3339()
            ));
        }
        Err(error) => return Err(error),
    };
    serde_json::to_value(response).map_err(|e| format!("serialize chat response: {e}"))
}

#[tauri::command]
pub async fn provider_models_list(
    state: State<'_, AppState>,
    params: ProviderModelsParams,
) -> Result<Value, String> {
    let provider = params.provider.trim().to_lowercase();
    if provider.is_empty() {
        return Err("Provider is required.".to_string());
    }

    let mut settings = state.paths.load_settings()?;
    if !params.refresh.unwrap_or(false) {
        if let Some(existing) = settings.provider_models.get(&provider) {
            if !existing.catalog.is_empty() {
                return serde_json::to_value(&existing.catalog)
                    .map_err(|e| format!("serialize cached provider models: {e}"));
            }
        }
    }

    let models = crate::cloud::list_provider_models(&settings, &provider).await?;
    let previous = settings
        .provider_models
        .get(&provider)
        .cloned()
        .unwrap_or_default();
    settings.provider_models.insert(
        provider,
        ProviderModelSettings {
            pinned: previous.pinned,
            catalog: models.clone(),
            fetched_at: Some(Utc::now().to_rfc3339()),
        },
    );
    state.paths.save_settings(&settings)?;
    serde_json::to_value(models).map_err(|e| format!("serialize provider models: {e}"))
}

fn is_openrouter_free_request(settings: &Settings, request: &ChatCompletionRequest) -> bool {
    settings
        .llm_provider
        .as_deref()
        .unwrap_or("openrouter")
        .eq_ignore_ascii_case("openrouter")
        && request
            .model
            .as_deref()
            .or(settings.external_llm_model.as_deref())
            .unwrap_or("openai/gpt-4o-mini")
            == "openrouter/free"
}

fn active_free_disabled_until(settings: &Settings) -> Option<DateTime<Utc>> {
    let raw = settings.openrouter_free_disabled_until.as_deref()?;
    let until = DateTime::parse_from_rfc3339(raw).ok()?.with_timezone(&Utc);
    (until > Utc::now()).then_some(until)
}

fn next_utc_midnight() -> DateTime<Utc> {
    let now = Utc::now();
    let tomorrow = now
        .date_naive()
        .succ_opt()
        .unwrap_or_else(|| now.date_naive());
    tomorrow
        .and_hms_opt(0, 0, 0)
        .map(|value| value.and_utc())
        .unwrap_or_else(|| now + ChronoDuration::hours(24))
}

fn looks_like_workspace_task_request(messages: &[ChatMessage]) -> bool {
    let prompt = messages
        .iter()
        .rev()
        .find(|message| message.role == "user")
        .map(|message| message.content.to_lowercase())
        .unwrap_or_default();
    let workspace_terms = [
        "edit",
        "change",
        "fix",
        "update",
        "modify",
        "refactor",
        "implement",
        "add",
        "remove",
        "delete",
        "create",
        "write",
        "patch",
        "apply",
        "make",
        "build",
        "scenes.py",
        "helpers.py",
        "brief",
    ];
    workspace_terms.iter().any(|term| prompt.contains(term))
}

fn openrouter_code_challenge(verifier: &str) -> String {
    let hash = Sha256::digest(verifier.as_bytes());
    URL_SAFE_NO_PAD.encode(hash)
}

fn query_param(query: &str, name: &str) -> Option<String> {
    for pair in query.split('&') {
        let mut parts = pair.splitn(2, '=');
        let key = parts.next().unwrap_or_default();
        if key != name {
            continue;
        }
        let raw = parts.next().unwrap_or_default();
        return Some(
            urlencoding::decode(raw)
                .map(|value| value.into_owned())
                .unwrap_or_else(|_| raw.to_string()),
        );
    }
    None
}

fn wait_for_openrouter_callback(
    listener: TcpListener,
    cancel: Arc<AtomicBool>,
) -> Result<String, String> {
    listener
        .set_nonblocking(true)
        .map_err(|e| format!("configure OAuth listener: {e}"))?;
    let started = std::time::Instant::now();
    loop {
        if cancel.load(Ordering::Relaxed) {
            return Err("OpenRouter connection cancelled.".to_string());
        }
        if started.elapsed() > Duration::from_secs(180) {
            return Err("OpenRouter connection timed out.".to_string());
        }
        match listener.accept() {
            Ok((mut stream, _)) => {
                let mut buffer = [0_u8; 4096];
                let n = stream
                    .read(&mut buffer)
                    .map_err(|e| format!("read OAuth callback: {e}"))?;
                let request = String::from_utf8_lossy(&buffer[..n]);
                let first_line = request.lines().next().unwrap_or_default();
                let path = first_line.split_whitespace().nth(1).unwrap_or_default();
                let query = path.split_once('?').map(|(_, q)| q).unwrap_or_default();
                let status_body = if query_param(query, "code").is_some() {
                    "OpenRouter is connected. You can return to Matemium."
                } else {
                    "OpenRouter did not return an authorization code. Return to Matemium and try again."
                };
                let response = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    status_body.len(),
                    status_body
                );
                let _ = stream.write_all(response.as_bytes());

                if let Some(error) = query_param(query, "error") {
                    return Err(format!("OpenRouter authorization failed: {error}"));
                }
                return query_param(query, "code")
                    .ok_or_else(|| "OpenRouter callback did not include a code.".to_string());
            }
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                std::thread::sleep(Duration::from_millis(100));
            }
            Err(error) => return Err(format!("accept OAuth callback: {error}")),
        }
    }
}

#[tauri::command]
pub async fn openrouter_prepare_connect(
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<OpenRouterConnectStart, String> {
    let listener = TcpListener::bind("127.0.0.1:0")
        .map_err(|e| format!("start local OAuth callback listener: {e}"))?;
    let port = listener
        .local_addr()
        .map_err(|e| format!("read OAuth listener address: {e}"))?
        .port();
    let callback_url = format!("http://127.0.0.1:{port}/openrouter/callback");
    let verifier = format!(
        "{}{}",
        uuid::Uuid::new_v4().as_simple(),
        uuid::Uuid::new_v4().as_simple()
    );
    let challenge = openrouter_code_challenge(&verifier);
    let auth_url = format!(
        "https://openrouter.ai/auth?callback_url={}&code_challenge={}&code_challenge_method=S256&key_label={}&http_referer={}&x_open_router_title={}&x_open_router_categories={}",
        urlencoding::encode(&callback_url),
        urlencoding::encode(&challenge),
        urlencoding::encode("Matemium"),
        urlencoding::encode("https://matemium.app"),
        urlencoding::encode("Matemium"),
        urlencoding::encode("education,local-app"),
    );
    let cancel = Arc::new(AtomicBool::new(false));

    {
        let mut pending = state
            .openrouter_oauth_session
            .lock()
            .map_err(|_| "OpenRouter OAuth state poisoned".to_string())?;
        if let Some(previous) = pending.take() {
            previous.cancel.store(true, Ordering::Relaxed);
        }
        *pending = Some(OpenRouterOAuthSession {
            listener,
            verifier,
            cancel,
        });
    }

    app.opener()
        .open_url(auth_url.clone(), None::<&str>)
        .map_err(|e| format!("open OpenRouter auth URL: {e}"))?;

    Ok(OpenRouterConnectStart {
        auth_url,
        callback_url,
    })
}

#[tauri::command]
pub async fn openrouter_complete_connect(
    state: State<'_, AppState>,
) -> Result<OpenRouterConnectionStatus, String> {
    let session = {
        let mut pending = state
            .openrouter_oauth_session
            .lock()
            .map_err(|_| "OpenRouter OAuth state poisoned".to_string())?;
        pending
            .take()
            .ok_or_else(|| "No OpenRouter connection is pending.".to_string())?
    };
    {
        let mut active = state
            .openrouter_oauth_active_cancel
            .lock()
            .map_err(|_| "OpenRouter OAuth cancel state poisoned".to_string())?;
        *active = Some(session.cancel.clone());
    }

    let listener = session.listener;
    let verifier = session.verifier;
    let cancel = session.cancel;
    let wait_result = tauri::async_runtime::spawn_blocking(move || {
        wait_for_openrouter_callback(listener, cancel)
    })
    .await
    .map_err(|e| format!("OAuth listener task failed: {e}"));
    {
        let mut active = state
            .openrouter_oauth_active_cancel
            .lock()
            .map_err(|_| "OpenRouter OAuth cancel state poisoned".to_string())?;
        *active = None;
    }
    let code = wait_result??;

    let key_response = crate::cloud::exchange_openrouter_code(&code, &verifier).await?;
    let mut settings = state.paths.load_settings()?;
    settings.llm_provider = Some("openrouter".to_string());
    settings.use_personal_llm = Some(true);
    settings.use_local_llm = Some(false);
    settings.openrouter_api_key = Some(key_response.key);
    settings.openrouter_user_id = key_response.user_id;
    settings.openrouter_connected_at = Some(Utc::now().to_rfc3339());
    state.paths.save_settings(&settings)?;

    Ok(OpenRouterConnectionStatus {
        connected: true,
        user_id: settings.openrouter_user_id,
        connected_at: settings.openrouter_connected_at,
    })
}

#[tauri::command]
pub async fn openrouter_cancel_connect(state: State<'_, AppState>) -> Result<(), String> {
    {
        let mut pending = state
            .openrouter_oauth_session
            .lock()
            .map_err(|_| "OpenRouter OAuth state poisoned".to_string())?;
        if let Some(session) = pending.take() {
            session.cancel.store(true, Ordering::Relaxed);
        }
    }
    {
        let mut active = state
            .openrouter_oauth_active_cancel
            .lock()
            .map_err(|_| "OpenRouter OAuth cancel state poisoned".to_string())?;
        if let Some(cancel) = active.take() {
            cancel.store(true, Ordering::Relaxed);
        }
    }
    Ok(())
}

#[tauri::command]
pub async fn openrouter_disconnect(
    state: State<'_, AppState>,
) -> Result<OpenRouterConnectionStatus, String> {
    let mut settings = state.paths.load_settings()?;
    settings.openrouter_api_key = None;
    settings.openrouter_user_id = None;
    settings.openrouter_connected_at = None;
    state.paths.save_settings(&settings)?;
    Ok(OpenRouterConnectionStatus {
        connected: false,
        user_id: None,
        connected_at: None,
    })
}

#[tauri::command]
pub async fn settings_get(state: State<'_, AppState>) -> Result<Value, String> {
    let settings = state.paths.load_settings()?;
    serde_json::to_value(settings).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn publish_animation(
    state: State<'_, AppState>,
    project_id: String,
    title: String,
    description: Option<String>,
    tags: Option<Vec<String>>,
    scene: Option<String>,
    duration: Option<f64>,
) -> Result<PublishResponse, String> {
    let readiness = get_readiness(state.clone()).await?;
    if !readiness.fully_ready {
        return Err(format!("APP_NOT_READY: {}", readiness.message));
    }

    // For thin publish, we send metadata only. The video is local; YT upload is separate.
    let request = PublishRequest {
        title,
        description,
        tags: tags.unwrap_or_default(),
        scene_class: scene,
        duration,
    };

    crate::cloud::publish_to_gallery(&state.paths.load_settings()?, request).await
}

#[tauri::command]
pub async fn list_gallery(
    state: State<'_, AppState>,
    search: Option<String>,
) -> Result<Value, String> {
    // Public, no auth needed for list. Uses server settings for URL.
    let settings = state.paths.load_settings()?;
    crate::cloud::list_gallery(&settings, search.as_deref()).await
}

async fn sync_sidecar_llm_config(state: &State<'_, AppState>) -> Result<(), String> {
    let settings = state.paths.load_settings()?;
    let use_local_llm = settings.use_local_llm.unwrap_or(false);
    let mut model_path = "".to_string();

    if use_local_llm {
        if let Some(ref model_id) = settings.local_llm_model {
            let statuses = state.assets.get_status(Some(model_id));
            if let Some(status) = statuses.first() {
                if status.verified {
                    if let Some(ref path) = status.path {
                        model_path = path.clone();
                    }
                }
            }
        }
    }

    let params = serde_json::json!({
        "use_local_llm": use_local_llm,
        "model_path": model_path,
    });

    let _ = state.sidecar.request("update_llm_config", params).await;
    Ok(())
}

#[tauri::command]
pub async fn settings_set(state: State<'_, AppState>, settings: Settings) -> Result<(), String> {
    state.paths.save_settings(&settings)?;
    let _ = sync_sidecar_llm_config(&state).await;
    Ok(())
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct VideoPreviewParams {
    pub path: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct OutputPathParams {
    pub project_id: String,
    pub path: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ClearCacheParams {
    pub project_id: String,
    pub kind: String,
}

// Commands for LLM features (provider profile, audio support)
// These use the secure server-side key resolution

#[tauri::command]
pub async fn cloud_get_profile(state: State<'_, AppState>) -> Result<Value, String> {
    let settings = state.paths.load_settings()?;
    crate::cloud::get_profile(&settings).await
}

#[tauri::command]
pub async fn cloud_generate_audio(
    state: State<'_, AppState>,
    params: CloudAudioParams,
) -> Result<Value, String> {
    let settings = state.paths.load_settings()?;
    let request = crate::cloud::AudioSpeechRequest {
        text: params.text,
        voice: params.voice,
        model: None,
        tts_provider: params.tts_provider,
        use_personal_llm: params.use_personal_llm,
    };
    let bytes = crate::cloud::generate_audio(&settings, request).await?;
    // Return base64 for easy frontend handling (consistent with previews)
    // Using base64 crate compat
    let encoded = base64::encode(bytes);
    Ok(serde_json::json!({ "dataBase64": encoded, "mimeType": "audio/mpeg" }))
}

// LLM profile fetch (provider key status)
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EmptyParams {}

// New for audio generation (TTS)
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CloudAudioParams {
    pub text: String,
    pub voice: Option<String>,
    pub tts_provider: Option<String>,
    pub use_personal_llm: Option<bool>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RevealOutputParams {
    pub project_id: String,
    pub path: Option<String>,
}

fn media_mime_type(path: &Path) -> Option<&'static str> {
    let ext = path.extension()?.to_str()?.to_ascii_lowercase();
    match ext.as_str() {
        "mp4" | "m4v" => Some("video/mp4"),
        "webm" => Some("video/webm"),
        "mov" => Some("video/quicktime"),
        "png" => Some("image/png"),
        "jpg" | "jpeg" => Some("image/jpeg"),
        "gif" => Some("image/gif"),
        "webp" => Some("image/webp"),
        "svg" => Some("image/svg+xml"),
        "bmp" => Some("image/bmp"),
        "avif" => Some("image/avif"),
        _ => None,
    }
}

pub fn validate_media_preview_path(
    paths: &crate::workspace::AppPaths,
    raw: &str,
) -> Result<PathBuf, String> {
    let candidate = PathBuf::from(raw);
    if !candidate.is_absolute() {
        return Err("media path must be absolute".to_string());
    }

    let path = candidate
        .canonicalize()
        .map_err(|e| format!("resolve media path: {e}"))?;
    let root = paths
        .data_root
        .canonicalize()
        .map_err(|e| format!("resolve data root: {e}"))?;

    if !path.starts_with(&root) {
        return Err("media path is outside the Matemium data directory".to_string());
    }
    if media_mime_type(&path).is_none() {
        return Err("unsupported media file type".to_string());
    }
    if !path.is_file() {
        return Err(format!("media file not found: {}", path.display()));
    }
    Ok(path)
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MediaPreviewResult {
    pub data_base64: String,
    pub mime_type: String,
}

fn resolve_playback_path(
    paths: &crate::workspace::AppPaths,
    raw: &str,
) -> Result<(PathBuf, String), String> {
    let source = validate_media_preview_path(paths, raw)?;
    let mime_type = media_mime_type(&source)
        .ok_or_else(|| "unsupported media file type".to_string())?
        .to_string();
    let playback = playback_path_for_media(paths, &source, &mime_type)?;
    Ok((playback, mime_type))
}

fn read_media_preview_bytes(
    paths: &crate::workspace::AppPaths,
    raw: &str,
) -> Result<MediaPreviewResult, String> {
    use base64::{engine::general_purpose::STANDARD, Engine as _};

    let (playback, mime_type) = resolve_playback_path(paths, raw)?;
    let bytes =
        std::fs::read(&playback).map_err(|e| format!("read media {}: {e}", playback.display()))?;
    Ok(MediaPreviewResult {
        data_base64: STANDARD.encode(bytes),
        mime_type,
    })
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CanonicalMediaPath {
    pub path: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MediaFileInfo {
    pub path: String,
    pub playback_path: String,
    pub size_bytes: u64,
    pub mime_type: String,
}

#[tauri::command]
pub fn canonicalize_media_preview_path(
    state: State<'_, AppState>,
    params: VideoPreviewParams,
) -> Result<CanonicalMediaPath, String> {
    let path = validate_media_preview_path(&state.paths, &params.path)?;
    Ok(CanonicalMediaPath {
        path: path.display().to_string(),
    })
}

#[tauri::command]
pub fn media_file_info(
    state: State<'_, AppState>,
    params: VideoPreviewParams,
) -> Result<MediaFileInfo, String> {
    let source = validate_media_preview_path(&state.paths, &params.path)?;
    let mime_type = media_mime_type(&source)
        .ok_or_else(|| "unsupported media file type".to_string())?
        .to_string();
    let playback = playback_path_for_media(&state.paths, &source, &mime_type)?;
    let size_bytes = std::fs::metadata(&playback)
        .map_err(|e| format!("stat media {}: {e}", playback.display()))?
        .len();
    Ok(MediaFileInfo {
        path: source.display().to_string(),
        playback_path: playback.display().to_string(),
        size_bytes,
        mime_type,
    })
}

#[tauri::command]
pub fn read_media_preview_binary(
    state: State<'_, AppState>,
    params: VideoPreviewParams,
) -> Result<Vec<u8>, String> {
    let (playback, _) = resolve_playback_path(&state.paths, &params.path)?;
    std::fs::read(&playback).map_err(|e| format!("read media {}: {e}", playback.display()))
}

#[tauri::command]
pub fn read_media_preview(
    state: State<'_, AppState>,
    params: VideoPreviewParams,
) -> Result<MediaPreviewResult, String> {
    read_media_preview_bytes(&state.paths, &params.path)
}

#[tauri::command]
pub fn read_video_preview(
    state: State<'_, AppState>,
    params: VideoPreviewParams,
) -> Result<String, String> {
    Ok(read_media_preview_bytes(&state.paths, &params.path)?.data_base64)
}

#[tauri::command]
pub async fn project_list_outputs(
    state: State<'_, AppState>,
    params: ProjectIdParams,
) -> Result<Value, String> {
    let result = list_outputs(&state.paths, &params.project_id)?;
    serde_json::to_value(result).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn project_delete_output(
    state: State<'_, AppState>,
    params: OutputPathParams,
) -> Result<(), String> {
    delete_output(&state.paths, &params.project_id, &params.path)
}

#[tauri::command]
pub async fn project_clear_render_cache(
    state: State<'_, AppState>,
    params: ClearCacheParams,
) -> Result<Value, String> {
    let freed = clear_render_cache(&state.paths, &params.project_id, &params.kind)?;
    serde_json::to_value(json!({ "freedBytes": freed })).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn project_reveal_output(
    app: AppHandle,
    state: State<'_, AppState>,
    params: RevealOutputParams,
) -> Result<(), String> {
    let path = if let Some(raw) = params.path {
        validate_project_workspace_path(&state.paths, &params.project_id, &raw)?
    } else {
        state.paths.renders_dir(&params.project_id)
    };

    if !path.exists() {
        return Err(format!("path not found: {}", path.display()));
    }

    app.opener()
        .reveal_item_in_dir(path.display().to_string())
        .map_err(|e| format!("reveal in file manager: {e}"))
}

#[tauri::command]
pub async fn project_open_output(
    app: AppHandle,
    state: State<'_, AppState>,
    params: OutputPathParams,
) -> Result<(), String> {
    let path = validate_output_path(
        &state.paths,
        &params.project_id,
        &params.path,
        OutputPathScope::Deletable,
    )?;
    if !path.is_file() {
        return Err(format!("not a file: {}", path.display()));
    }

    app.opener()
        .open_path(path.display().to_string(), None::<&str>)
        .map_err(|e| format!("open file: {e}"))
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Conversation {
    pub id: String,
    pub title: String,
    pub created_at: String,
    pub messages: Vec<ChatMessage>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ConversationListParams {
    pub project_id: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ConversationSaveParams {
    pub project_id: String,
    pub conversation: Conversation,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ConversationDeleteParams {
    pub project_id: String,
    pub conversation_id: String,
}

#[tauri::command]
pub async fn conversation_list(
    state: State<'_, AppState>,
    params: ConversationListParams,
) -> Result<Value, String> {
    let path = state.paths.conversations_path(&params.project_id);
    if !path.exists() {
        return Ok(serde_json::Value::Array(vec![]));
    }
    let data = std::fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read conversations file: {}", e))?;
    let list: Vec<Conversation> = serde_json::from_str(&data).unwrap_or_else(|_| vec![]);
    serde_json::to_value(list).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn conversation_save(
    state: State<'_, AppState>,
    params: ConversationSaveParams,
) -> Result<(), String> {
    let path = state.paths.conversations_path(&params.project_id);
    let mut list: Vec<Conversation> = if path.exists() {
        let data = std::fs::read_to_string(&path)
            .map_err(|e| format!("Failed to read conversations file: {}", e))?;
        serde_json::from_str(&data).unwrap_or_else(|_| vec![])
    } else {
        vec![]
    };

    // Find and update or append
    let mut found = false;
    for c in list.iter_mut() {
        if c.id == params.conversation.id {
            *c = params.conversation.clone();
            found = true;
            break;
        }
    }
    if !found {
        list.push(params.conversation);
    }

    let data = serde_json::to_string_pretty(&list)
        .map_err(|e| format!("Failed to serialize conversations: {}", e))?;
    std::fs::write(&path, data)
        .map_err(|e| format!("Failed to write conversations file: {}", e))?;
    Ok(())
}

#[tauri::command]
pub async fn conversation_delete(
    state: State<'_, AppState>,
    params: ConversationDeleteParams,
) -> Result<(), String> {
    let path = state.paths.conversations_path(&params.project_id);
    if !path.exists() {
        return Ok(());
    }
    let data = std::fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read conversations: {}", e))?;
    let mut list: Vec<Conversation> = serde_json::from_str(&data).unwrap_or_else(|_| vec![]);

    list.retain(|c| c.id != params.conversation_id);

    let data = serde_json::to_string_pretty(&list)
        .map_err(|e| format!("Failed to serialize conversations: {}", e))?;
    std::fs::write(&path, data).map_err(|e| format!("Failed to write conversations: {}", e))?;
    Ok(())
}

#[cfg(test)]
mod video_preview_tests {
    use super::*;
    use crate::workspace::AppPaths;
    use std::fs;

    #[test]
    fn validate_video_preview_path_accepts_workspace_mp4() {
        let paths = AppPaths::resolve().expect("paths");
        paths.ensure().expect("ensure");
        let project_id = "preview-test-project";
        let renders = paths.renders_dir(project_id);
        fs::create_dir_all(&renders).expect("renders dir");
        let video = renders.join("Demo.mp4");
        fs::write(&video, b"fake-mp4").expect("write video");

        let resolved = validate_media_preview_path(&paths, &video.display().to_string())
            .expect("valid preview path");
        assert_eq!(resolved, video.canonicalize().expect("canonical"));
    }

    #[test]
    fn validate_media_preview_path_rejects_outside_data_root() {
        let paths = AppPaths::resolve().expect("paths");
        let err =
            validate_media_preview_path(&paths, "/etc/passwd").expect_err("outside data root");
        assert!(err.contains("outside"));
    }
}
