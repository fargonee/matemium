pub mod agent_accounting;
pub mod agent_context;
pub mod agent_delegation;
pub mod agent_events;
pub mod agent_policy;
pub mod agent_runs;
pub mod agent_tools;
pub mod agent_verifier;
pub mod assets;
pub mod cloud;
pub mod commands;
pub mod local_models;
mod media_preview;
mod outputs;
mod projects;
mod protocol;
mod sidecar;
mod state;
pub mod workspace;

use std::sync::Mutex;
use tauri::{Manager, RunEvent};
use workspace::AppPaths;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let paths =
                AppPaths::resolve().map_err(|e| -> Box<dyn std::error::Error> { e.into() })?;
            paths
                .ensure()
                .map_err(|e| -> Box<dyn std::error::Error> { e.into() })?;

            let sidecar = sidecar::SidecarManager::new(app.handle().clone(), paths.clone());
            let assets = crate::assets::AssetManager::new(paths.clone());

            // Automatically synchronize LLM config to sidecar on startup!
            let sidecar_clone = sidecar.clone();
            let assets_clone = assets.clone();
            let paths_clone = paths.clone();
            tauri::async_runtime::spawn(async move {
                let settings = paths_clone.load_settings().unwrap_or_default();
                let use_local_llm = settings.use_local_llm.unwrap_or(false);
                let mut model_path = "".to_string();

                if use_local_llm {
                    if let Some(ref model_id) = settings.local_llm_model {
                        let statuses = assets_clone.get_status(Some(model_id));
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

                let _ = sidecar_clone.request("update_llm_config", params).await;
                if settings.use_autonomous_agent.unwrap_or(false) {
                    let result = sidecar_clone
                        .request("prepare_agent_runtime", serde_json::json!({}))
                        .await;
                    if let Err(error) = result {
                        log::warn!("agent runtime preparation failed: {error}");
                    }
                }
            });

            let agent_runs = crate::agent_runs::AgentRunStore::open(paths.agent_runs_db_path())
                .map_err(|e| -> Box<dyn std::error::Error> { e.into() })?;

            app.manage(state::AppState {
                paths,
                sidecar,
                assets,
                agent_runs,
                openrouter_oauth_session: Mutex::new(None),
                openrouter_oauth_active_cancel: Mutex::new(None),
                auth_browser_cancel: Mutex::new(None),
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::project_list,
            commands::example_list,
            commands::example_open_source,
            commands::example_create_copy,
            commands::project_create,
            commands::project_open,
            commands::project_save,
            commands::project_save_file,
            commands::project_create_tape,
            commands::project_save_tape,
            commands::project_list_media,
            commands::project_import_media,
            commands::project_delete_media,
            commands::project_delete,
            commands::project_export_archive,
            commands::project_import_archive,
            commands::sidecar_ping,
            commands::sidecar_configure_assets,
            commands::get_asset_status,
            commands::start_asset_download,
            commands::local_model_catalog_list,
            commands::local_model_install,
            commands::pause_asset_download,
            commands::cancel_asset_download,
            commands::get_readiness,
            commands::sidecar_retrieve,
            commands::sidecar_upload_reference,
            commands::sidecar_list_references,
            commands::sidecar_delete_reference,
            commands::sidecar_get_reference_content,
            commands::publish_animation,
            commands::list_gallery,
            commands::sidecar_lint,
            commands::sidecar_check,
            commands::sidecar_list_scenes,
            commands::sidecar_list_tapes,
            commands::sidecar_export_tape,
            commands::sidecar_render,
            commands::sidecar_get_preview_data,
            commands::sidecar_cancel,
            commands::agent_run_list,
            commands::agent_run_get,
            commands::agent_run_events,
            commands::agent_run_cancel,
            commands::agent_run_resume,
            commands::agent_run_approve,
            commands::agent_run_provide_input,
            commands::auth_login,
            commands::auth_session,
            commands::auth_browser_login,
            commands::auth_browser_login_cancel,
            commands::openrouter_prepare_connect,
            commands::openrouter_complete_connect,
            commands::openrouter_cancel_connect,
            commands::openrouter_disconnect,
            commands::cloud_chat,
            commands::provider_models_list,
            commands::cloud_get_profile,
            commands::cloud_generate_audio,
            commands::project_mux_audio,
            commands::project_transcribe_audio,
            commands::project_approve_audio,
            commands::conversation_list,
            commands::conversation_save,
            commands::conversation_delete,
            commands::settings_get,
            commands::settings_set,
            commands::canonicalize_media_preview_path,
            commands::media_file_info,
            commands::read_media_preview_binary,
            commands::read_media_preview,
            commands::read_video_preview,
            commands::project_list_outputs,
            commands::project_delete_output,
            commands::project_clear_render_cache,
            commands::project_reveal_output,
            commands::project_open_output,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if matches!(event, RunEvent::Exit) {
                if let Some(state) = app_handle.try_state::<state::AppState>() {
                    tauri::async_runtime::block_on(state.sidecar.shutdown());
                }
            }
        });
}
