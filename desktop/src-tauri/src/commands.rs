use std::path::{Path, PathBuf};

use base64;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tauri::{AppHandle, State};
use tauri_plugin_opener::OpenerExt;

use crate::cloud::{ChatCompletionRequest, ChatMessage, PublishRequest, PublishResponse};
use crate::media_preview::playback_path_for_media;
use crate::outputs::{
    clear_render_cache, delete_output, list_outputs, validate_output_path,
    validate_project_workspace_path, validate_render_output_dir, OutputPathScope,
};
use crate::workspace::Settings;
use crate::projects::{
    create_project, delete_project, list_projects, open_project, save_assets, save_scenes,
    workspace_path,
};
use crate::state::AppState;

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
pub struct ProjectSaveParams {
    pub project_id: String,
    pub content: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectSaveAssetsParams {
    pub project_id: String,
    pub content: String,
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
    pub scenes_excerpt: Option<String>,
    // LLM selection flags (passed through to server for BYO vs platform)
    pub llm_provider: Option<String>,
    pub use_personal_llm: Option<bool>,
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
pub async fn project_save_assets(
    state: State<'_, AppState>,
    params: ProjectSaveAssetsParams,
) -> Result<(), String> {
    save_assets(&state.paths, &params.project_id, &params.content)
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
    state.sidecar.request("configure_assets", Value::Object(params)).await
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
    // In real use, after download we can call configure + notify sidecar
    state.assets.start_download(app.clone(), &asset_id, None).await?;

    // After successful TinyTeX download, auto-configure sidecar if possible
    if asset_id == "tinytex-linux" {
        if let Some(bin_dir) = state.assets.tinytex_bin_dir() {
            let _ = state.sidecar.request(
                "configure_assets",
                json!({ "tinytex_dir": bin_dir.to_string_lossy().to_string() }),
            ).await;
        }
    }
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

    let engine_status = state.sidecar.request("get_status", json!({})).await.unwrap_or(json!({}));
    let engine_phase = engine_status.get("phase").and_then(|v| v.as_str()).unwrap_or("CORE_READY").to_string();
    let engine_ready = engine_phase == "ENGINE_READY" || engine_phase.contains("READY");
    let intelligence_ready = engine_status.get("intelligence_ready").and_then(|v| v.as_bool()).unwrap_or(false)
        || engine_phase.contains("INTELLIGENCE_READY");

    let fully_ready = tinytex_ready && engine_ready;

    let (phase, message) = if !tinytex_ready {
        ("assets".to_string(), "Downloading Local Code Intelligence assets (TinyTeX)...".to_string())
    } else if !engine_ready {
        ("engine".to_string(), "Loading Manim / canvas engine...".to_string())
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
) -> Result<Value, String> {
    let workspace = workspace_path(&state.paths, &project_id)?;
    state.sidecar.request("retrieve", json!({
        "workspace": workspace,
        "query": query,
        "top_k": top_k.unwrap_or(8),
        "files": ["scenes.py", "assets.py"],
    })).await
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
        .request(
            "get_preview_data",
            json!({ "workspace": workspace }),
        )
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
    serde_json::to_value(serde_json::json!({ "accessToken": token }))
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn auth_session(
    state: State<'_, AppState>,
    params: AuthSessionParams,
) -> Result<Value, String> {
    let settings = state.paths.load_settings()?;
    let token = crate::cloud::login_with_session(&settings, &params.access_token).await?;
    serde_json::to_value(serde_json::json!({ "accessToken": token }))
        .map_err(|e| e.to_string())
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
    let request = ChatCompletionRequest {
        messages: params.messages,
        project_id: params.project_id,
        scenes_excerpt: params.scenes_excerpt,
        llm_provider: params.llm_provider,
        use_personal_llm: params.use_personal_llm,
    };
    crate::cloud::chat_raw(&settings, request).await
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
pub async fn list_gallery(state: State<'_, AppState>, search: Option<String>) -> Result<Value, String> {
    // Public, no auth needed for list. Uses server settings for URL.
    let settings = state.paths.load_settings()?;
    crate::cloud::list_gallery(&settings, search.as_deref()).await
}

#[tauri::command]
pub async fn settings_set(
    state: State<'_, AppState>,
    settings: Settings,
) -> Result<(), String> {
    state.paths.save_settings(&settings)
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

// Commands for new LLM features (profile for credits, audio support)
// These use the secure server-side key resolution

#[tauri::command]
pub async fn cloud_get_profile(
    state: State<'_, AppState>,
) -> Result<Value, String> {
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

// New for LLM profile fetch (credits, key status)
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

fn read_media_preview_bytes(paths: &crate::workspace::AppPaths, raw: &str) -> Result<MediaPreviewResult, String> {
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
    serde_json::to_value(json!({ "freedBytes": freed }))
        .map_err(|e| e.to_string())
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
        let err = validate_media_preview_path(&paths, "/etc/passwd")
            .expect_err("outside data root");
        assert!(err.contains("outside"));
    }
}