use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use serde_json::{json, Value};
use tauri::{AppHandle, Emitter};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;
use tokio::sync::oneshot;

use crate::protocol::{build_request, parse_line, response_error_message, InboundMessage};
use crate::workspace::AppPaths;

const SIDECAR_NAME: &str = "matemium-sidecar";
const SIDECAR_EVENT: &str = "sidecar-event";

struct SidecarInner {
    child: Option<CommandChild>,
    pending: HashMap<String, oneshot::Sender<Result<Value, String>>>,
    /// Incomplete NDJSON line carried across stdout chunks.
    stdout_buffer: String,
}

pub struct SidecarManager {
    app: AppHandle,
    paths: AppPaths,
    inner: Arc<Mutex<SidecarInner>>,
}

impl SidecarManager {
    pub fn new(app: AppHandle, paths: AppPaths) -> Self {
        Self {
            app,
            paths,
            inner: Arc::new(Mutex::new(SidecarInner {
                child: None,
                pending: HashMap::new(),
                stdout_buffer: String::new(),
            })),
        }
    }

    pub async fn request(&self, command: &str, params: Value) -> Result<Value, String> {
        self.ensure_running().await?;

        let request_id = uuid::Uuid::new_v4().to_string();
        let (tx, rx) = oneshot::channel();

        {
            let mut inner = self
                .inner
                .lock()
                .map_err(|_| "sidecar state poisoned".to_string())?;
            inner.pending.insert(request_id.clone(), tx);
        }

        let line = build_request(&request_id, command, params);
        if let Err(err) = self.write_stdin(line.as_bytes()) {
            let mut inner = self
                .inner
                .lock()
                .map_err(|_| "sidecar state poisoned".to_string())?;
            inner.pending.remove(&request_id);
            return Err(err);
        }

        match rx.await {
            Ok(result) => result,
            Err(_) => Err("sidecar closed before response".to_string()),
        }
    }

    /// Kill the sidecar process and fail any in-flight IPC requests (e.g. user cancel during render).
    pub async fn cancel_active(&self) -> Result<(), String> {
        let child = {
            let mut inner = self
                .inner
                .lock()
                .map_err(|_| "sidecar state poisoned".to_string())?;
            let pending: Vec<_> = inner.pending.drain().collect();
            for (_, sender) in pending {
                let _ = sender.send(Err("cancelled by user".to_string()));
            }
            inner.child.take()
        };

        if let Some(child) = child {
            child
                .kill()
                .map_err(|e| format!("kill sidecar: {e}"))?;
        }
        Ok(())
    }

    pub async fn shutdown(&self) {
        let _ = self
            .request("shutdown", json!({}))
            .await
            .map(|value| log::info!("sidecar shutdown: {value}"));

        let child = {
            let mut inner = match self.inner.lock() {
                Ok(inner) => inner,
                Err(_) => return,
            };
            inner.pending.clear();
            inner.child.take()
        };

        if let Some(child) = child {
            let _ = child.kill();
        }
    }

    async fn ensure_running(&self) -> Result<(), String> {
        let needs_spawn = {
            let inner = self
                .inner
                .lock()
                .map_err(|_| "sidecar state poisoned".to_string())?;
            inner.child.is_none()
        };

        if needs_spawn {
            self.spawn()?;
        }
        Ok(())
    }

    fn spawn(&self) -> Result<(), String> {
        let mut locked = self
            .inner
            .lock()
            .map_err(|_| "sidecar state poisoned".to_string())?;
        if locked.child.is_some() {
            return Ok(());
        }

        let matemium_root = self.paths.data_root.to_string_lossy().to_string();
        let (mut rx, child) = if let Some(python) = dev_python_sidecar() {
            log::info!("sidecar: using repo .venv python (dev)");
            let source_root = python.parent().and_then(|p| p.parent()).map(|p| p.to_string_lossy().to_string()).unwrap_or_default();
            self.app
                .shell()
                .command(python)
                .args(["-u", "-m", "matemium.sidecar"])
                .current_dir(&self.paths.data_root)
                .env("MATEMIUM_ROOT", matemium_root)
                .env("PYTHONPATH", source_root)
                .env("PYTHONUNBUFFERED", "1")
                .spawn()
                .map_err(|e| format!("spawn python sidecar: {e}"))?
        } else {
            log::info!("sidecar: using bundled PyInstaller binary");
            self.app
                .shell()
                .sidecar(SIDECAR_NAME)
                .map_err(|e| format!("resolve sidecar binary: {e}"))?
                .current_dir(&self.paths.data_root)
                .env("MATEMIUM_ROOT", matemium_root)
                .env("PYTHONUNBUFFERED", "1")
                .spawn()
                .map_err(|e| format!("spawn sidecar: {e}"))?
        };

        let app = self.app.clone();
        let inner = Arc::clone(&self.inner);

        tauri::async_runtime::spawn(async move {
            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(bytes) => {
                        let chunk = String::from_utf8_lossy(&bytes);
                        dispatch_stdout_chunk(&app, &inner, &chunk);
                    }
                    CommandEvent::Stderr(bytes) => {
                        let line = String::from_utf8_lossy(&bytes);
                        log::warn!("sidecar stderr: {line}");
                    }
                    CommandEvent::Terminated(payload) => {
                        log::info!("sidecar terminated: {payload:?}");
                        if let Ok(mut guard) = inner.lock() {
                            guard.child = None;
                            let pending: Vec<_> = guard.pending.drain().collect();
                            drop(guard);
                            for (_, sender) in pending {
                                let _ = sender.send(Err("sidecar process terminated".to_string()));
                            }
                        }
                        break;
                    }
                    CommandEvent::Error(message) => {
                        log::error!("sidecar error: {message}");
                    }
                    _ => {}
                }
            }
        });

        locked.stdout_buffer.clear();
        locked.child = Some(child);
        Ok(())
    }

    fn write_stdin(&self, bytes: &[u8]) -> Result<(), String> {
        let mut inner = self
            .inner
            .lock()
            .map_err(|_| "sidecar state poisoned".to_string())?;
        let child = inner
            .child
            .as_mut()
            .ok_or_else(|| "sidecar is not running".to_string())?;
        child
            .write(bytes)
            .map_err(|e| format!("write sidecar stdin: {e}"))
    }
}

fn dev_python_sidecar() -> Option<PathBuf> {
    if !cfg!(debug_assertions) {
        return None;
    }
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    // Support normal layout and worktrees (math / math-preview)
    for levels in 1..=6u32 {
        let p = manifest.join("../".repeat(levels as usize)).join(".venv/bin/python");
        if p.is_file() {
            return Some(p);
        }
    }
    None
}

fn take_complete_stdout_lines(buffer: &mut String, chunk: &str) -> Vec<String> {
    buffer.push_str(chunk);
    let mut complete = Vec::new();
    while let Some(pos) = buffer.find('\n') {
        let line = buffer.drain(..=pos).collect::<String>();
        complete.push(line.trim_end_matches(['\r', '\n']).to_string());
    }
    complete
}

fn dispatch_stdout_chunk(app: &AppHandle, inner: &Arc<Mutex<SidecarInner>>, chunk: &str) {
    let lines = {
        let mut guard = match inner.lock() {
            Ok(guard) => guard,
            Err(_) => return,
        };
        take_complete_stdout_lines(&mut guard.stdout_buffer, chunk)
    };

    for line in lines {
        dispatch_stdout_line(app, inner, &line);
    }
}

fn dispatch_stdout_line(app: &AppHandle, inner: &Arc<Mutex<SidecarInner>>, line: &str) {
    let Some(message) = parse_line(line) else {
        if !line.trim().is_empty() {
            log::debug!("sidecar non-protocol stdout: {line}");
        }
        return;
    };

    match message {
        InboundMessage::Response {
            id,
            ok,
            result,
            error,
        } => {
            let sender = {
                let mut guard = match inner.lock() {
                    Ok(guard) => guard,
                    Err(_) => return,
                };
                guard.pending.remove(&id)
            };

            if let Some(sender) = sender {
                let payload = if ok {
                    Ok(result.unwrap_or(Value::Null))
                } else {
                    Err(error
                        .as_ref()
                        .map(response_error_message)
                        .unwrap_or_else(|| "sidecar request failed".to_string()))
                };
                let _ = sender.send(payload);
            } else {
                log::warn!("sidecar response with unknown id: {id}");
            }
        }
        InboundMessage::Event { event, data } => {
            let payload = json!({
                "event": event,
                "data": data,
            });
            let _ = app.emit(SIDECAR_EVENT, payload);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::protocol::build_request;

    #[test]
    fn request_payload_has_newline() {
        let line = build_request("id-1", "ping", json!({}));
        assert!(line.ends_with('\n'));
    }

    #[test]
    fn stdout_chunk_splits_multiple_ndjson_lines() {
        let mut buffer = String::new();
        let chunk = concat!(
            r#"{"type":"event","event":"render_progress","data":{"pct":0.1}}"#,
            "\n",
            r#"{"type":"event","event":"render_progress","data":{"pct":0.2}}"#,
            "\n",
        );
        let lines = take_complete_stdout_lines(&mut buffer, chunk);
        assert_eq!(lines.len(), 2);
        assert!(buffer.is_empty());
        assert!(lines[0].contains("0.1"));
        assert!(lines[1].contains("0.2"));
    }

    #[test]
    fn stdout_chunk_carries_partial_line_across_reads() {
        let mut buffer = String::new();
        let first = take_complete_stdout_lines(&mut buffer, r#"{"type":"event""#);
        assert!(first.is_empty());
        assert!(!buffer.is_empty());
        let second = take_complete_stdout_lines(
            &mut buffer,
            concat!(r#","event":"render_progress","data":{}}"#, "\n"),
        );
        assert_eq!(second.len(), 1);
        assert!(buffer.is_empty());
    }
}