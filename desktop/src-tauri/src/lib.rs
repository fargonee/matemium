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
            app.manage(state::AppState { paths, sidecar });
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
            commands::sidecar_lint,
            commands::sidecar_check,
            commands::sidecar_list_scenes,
            commands::sidecar_render,
            commands::sidecar_cancel,
            commands::auth_login,
            commands::cloud_chat,
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