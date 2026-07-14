pub mod assets;
pub mod cloud;
pub mod commands;
mod media_preview;
mod outputs;
mod projects;
mod protocol;
mod sidecar;
mod state;
pub mod workspace;

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

            let paths = AppPaths::resolve().map_err(|e| -> Box<dyn std::error::Error> {
                e.into()
            })?;
            paths.ensure().map_err(|e| -> Box<dyn std::error::Error> {
                e.into()
            })?;

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
            });

            app.manage(state::AppState { paths, sidecar, assets });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::project_list,
            commands::project_create,
            commands::project_open,
            commands::project_save,
            commands::project_save_assets,
            commands::project_delete,
            commands::sidecar_ping,
            commands::sidecar_configure_assets,
            commands::get_asset_status,
            commands::start_asset_download,
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
            commands::sidecar_render,
            commands::sidecar_get_preview_data,
            commands::sidecar_cancel,
            commands::auth_login,
            commands::auth_session,
            commands::cloud_chat,
            commands::cloud_get_profile,
            commands::cloud_generate_audio,
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