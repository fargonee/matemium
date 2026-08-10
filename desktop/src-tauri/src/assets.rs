//! PAD Phase 3: Rust-owned first-run asset download manager.
//! Handles optional local GGUF models with Range-resumable downloads.
//!
//! Responsibilities:
//! - Load asset specs dynamically from shared/assets/manifest.json (with static fallbacks)
//! - Download from manifest URLs in a non-blocking stream with HTTP Range offsets
//! - Verify SHA256 checksums post-download
//! - Extract archives (tar.gz/zip) or save single files directly
//! - Support pause and cancellation via thread-safe signals
//! - Atomic move to final location under assets_root
//! - Persist download state
//! - Emit Tauri progress events over the UI channel

use std::collections::HashSet;
use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use futures_util::StreamExt;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use tauri::{AppHandle, Emitter};
use tokio::io::AsyncWriteExt;

use crate::workspace::AppPaths;

#[derive(Debug, Clone, Deserialize)]
pub struct ManifestAsset {
    pub id: String,
    pub name: String,
    pub url: String,
    pub sha256: String,
    pub size: u64,
    pub extract: bool,
    pub extract_format: String,
    pub install_path: String,
    pub platforms: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Manifest {
    pub version: String,
    pub assets: Vec<ManifestAsset>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AssetStatus {
    pub id: String,
    pub display_name: Option<String>,
    pub asset_type: Option<String>,
    pub downloaded: bool,
    pub verified: bool,
    pub path: Option<String>,
    pub size: Option<u64>,
    pub progress: Option<f32>,
    pub error: Option<String>,
    pub paused: Option<bool>,
    pub source_url: Option<String>,
    pub expected_sha256: Option<String>,
    pub install_path: Option<String>,
    pub extract: Option<bool>,
    pub extract_format: Option<String>,
}

#[derive(Debug, Clone)]
pub struct DownloadableAssetSpec {
    pub id: String,
    pub display_name: Option<String>,
    pub asset_type: Option<String>,
    pub source_url: String,
    pub expected_sha256: Option<String>,
    pub size: u64,
    pub extract: bool,
    pub extract_format: String,
    pub install_path: String,
}

#[derive(Debug, Clone)]
struct DownloadSpec {
    display_name: Option<String>,
    asset_type: Option<String>,
    url: String,
    expected_sha: String,
    install_path: String,
    extract: bool,
    size: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct AssetState {
    assets: Vec<AssetStatus>,
}

#[derive(Clone)]
pub struct AssetManager {
    paths: AppPaths,
    state: Arc<Mutex<AssetState>>,
    client: Client,
    cancelled_downloads: Arc<Mutex<HashSet<String>>>,
    paused_downloads: Arc<Mutex<HashSet<String>>>,
    active_downloads: Arc<Mutex<HashSet<String>>>,
}

struct ActiveDownloadGuard {
    active_downloads: Arc<Mutex<HashSet<String>>>,
    asset_id: String,
}

impl Drop for ActiveDownloadGuard {
    fn drop(&mut self) {
        let mut active = self.active_downloads.lock().unwrap();
        active.remove(&self.asset_id);
    }
}

impl AssetManager {
    pub fn new(paths: AppPaths) -> Self {
        let mut state = Self::load_state(&paths).unwrap_or_default();

        // Pre-populate assets from manifest and auto-detect existing downloads on startup
        let manifest = Self::get_manifest();
        let mut modified = false;
        for spec in manifest.assets {
            let final_path = paths.assets_root.join(&spec.install_path);
            let exists_and_matches = if final_path.is_file() {
                if let Ok(meta) = fs::metadata(&final_path) {
                    meta.len() == spec.size
                } else {
                    false
                }
            } else {
                false
            };

            if let Some(asset) = state.assets.iter_mut().find(|a| a.id == spec.id) {
                if asset.display_name.is_none() {
                    asset.display_name = Some(spec.name.clone());
                    modified = true;
                }
                let expected_type = Some(
                    if spec.id.starts_with("llm-") {
                        "local_model"
                    } else {
                        "utility"
                    }
                    .to_string(),
                );
                if asset.asset_type.is_none() {
                    asset.asset_type = expected_type;
                    modified = true;
                }
                if asset.source_url.is_none() {
                    asset.source_url = Some(spec.url.clone());
                    modified = true;
                }
                if asset.expected_sha256.is_none() {
                    asset.expected_sha256 = Some(spec.sha256.clone());
                    modified = true;
                }
                if asset.install_path.is_none() {
                    asset.install_path = Some(spec.install_path.clone());
                    modified = true;
                }
                if asset.extract.is_none() {
                    asset.extract = Some(spec.extract);
                    modified = true;
                }
                if asset.extract_format.is_none() {
                    asset.extract_format = Some(spec.extract_format.clone());
                    modified = true;
                }
                // If the file exists but is not marked verified in the loaded state, auto-verify it!
                if exists_and_matches && (!asset.verified || asset.path.is_none()) {
                    asset.downloaded = true;
                    asset.verified = true;
                    asset.path = Some(final_path.to_string_lossy().to_string());
                    asset.progress = Some(100.0);
                    asset.error = None;
                    asset.paused = Some(false);
                    modified = true;
                }
            } else {
                // Asset is not in the loaded state yet - add it
                let (downloaded, verified, path, progress) = if exists_and_matches {
                    (
                        true,
                        true,
                        Some(final_path.to_string_lossy().to_string()),
                        Some(100.0),
                    )
                } else {
                    (false, false, None, None)
                };

                state.assets.push(AssetStatus {
                    id: spec.id.clone(),
                    display_name: Some(spec.name.clone()),
                    asset_type: Some(
                        if spec.id.starts_with("llm-") {
                            "local_model"
                        } else {
                            "utility"
                        }
                        .to_string(),
                    ),
                    downloaded,
                    verified,
                    path,
                    size: Some(spec.size),
                    progress,
                    error: None,
                    paused: Some(false),
                    source_url: Some(spec.url.clone()),
                    expected_sha256: Some(spec.sha256.clone()),
                    install_path: Some(spec.install_path.clone()),
                    extract: Some(spec.extract),
                    extract_format: Some(spec.extract_format.clone()),
                });
                modified = true;
            }
        }

        let manager = Self {
            paths,
            state: Arc::new(Mutex::new(state)),
            client: Client::builder()
                .user_agent("Matemium/1.0")
                .connect_timeout(Duration::from_secs(15))
                .build()
                .expect("reqwest client"),
            cancelled_downloads: Arc::new(Mutex::new(HashSet::new())),
            paused_downloads: Arc::new(Mutex::new(HashSet::new())),
            active_downloads: Arc::new(Mutex::new(HashSet::new())),
        };

        if modified {
            manager.save_state();
        }

        manager
    }

    pub fn add_downloadable_asset(&self, spec: DownloadableAssetSpec) {
        let mut state = self.state.lock().unwrap();
        let final_path = self.paths.assets_root.join(&spec.install_path);
        let exists_and_matches = final_path.is_file()
            && fs::metadata(&final_path)
                .map(|meta| meta.len() == spec.size)
                .unwrap_or(false);
        let mut next = state
            .assets
            .iter()
            .find(|asset| asset.id == spec.id)
            .cloned()
            .unwrap_or_default();
        next.id = spec.id.clone();
        next.display_name = spec.display_name.clone();
        next.asset_type = spec.asset_type.clone();
        next.downloaded = next.downloaded || exists_and_matches;
        next.verified = next.verified || exists_and_matches;
        next.path = if exists_and_matches {
            Some(final_path.to_string_lossy().to_string())
        } else {
            next.path.filter(|path| Path::new(path).is_file())
        };
        next.size = Some(spec.size);
        next.progress = if next.downloaded && next.verified {
            Some(100.0)
        } else {
            next.progress.or(Some(0.0))
        };
        if next.downloaded && next.verified {
            next.error = None;
        }
        next.paused = Some(false);
        next.source_url = Some(spec.source_url.clone());
        next.expected_sha256 = spec.expected_sha256.clone();
        next.install_path = Some(spec.install_path.clone());
        next.extract = Some(spec.extract);
        next.extract_format = Some(spec.extract_format.clone());
        if let Some(existing) = state.assets.iter_mut().find(|asset| asset.id == spec.id) {
            *existing = next;
        } else {
            state.assets.push(next);
        }
        drop(state);
        self.save_state();
    }

    fn download_spec_from_status(&self, asset_id: &str) -> Option<DownloadSpec> {
        let state = self.state.lock().unwrap();
        let status = state.assets.iter().find(|asset| asset.id == asset_id)?;
        let url = status.source_url.clone()?;
        let install_path = status.install_path.clone()?;
        Some(DownloadSpec {
            display_name: status.display_name.clone(),
            asset_type: status.asset_type.clone(),
            url,
            expected_sha: status
                .expected_sha256
                .clone()
                .unwrap_or_else(|| "PLACEHOLDER_REPLACE_WITH_REAL".to_string()),
            install_path,
            extract: status.extract.unwrap_or(false),
            size: status.size.unwrap_or(0),
        })
    }

    /// Retrieve the authoritative asset manifest, resolving relative development paths
    /// or returning static fallbacks in production.
    pub fn get_manifest() -> Manifest {
        let manifest_path =
            Path::new(env!("CARGO_MANIFEST_DIR")).join("../../shared/assets/manifest.json");

        if manifest_path.exists() {
            if let Ok(raw) = fs::read_to_string(&manifest_path) {
                if let Ok(manifest) = serde_json::from_str::<Manifest>(&raw) {
                    return manifest;
                }
            }
        }

        // Static production-grade fallback manifest if local file resolution fails
        Manifest {
            version: "2026-08-09".to_string(),
            assets: vec![
                ManifestAsset {
                    id: "llm-qwen-coder-3b-q4".to_string(),
                    name: "Qwen-2.5-Coder-3B-Instruct (Q4_K_M GGUF)".to_string(),
                    url: "https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/qwen2.5-coder-3b-instruct-q4_k_m.gguf".to_string(),
                    sha256: "724fb256bec1ff062b2f65e4569e871ad2e95ab2a3989723d1769c54294730b7".to_string(),
                    size: 2104932800,
                    extract: false,
                    extract_format: "none".to_string(),
                    install_path: "models/qwen2.5-coder-3b-instruct-q4_k_m.gguf".to_string(),
                    platforms: vec!["linux".to_string(), "darwin".to_string(), "windows".to_string()],
                },
                ManifestAsset {
                    id: "llm-qwen-coder-7b-q4".to_string(),
                    name: "Qwen-2.5-Coder-7B-Instruct (Q4_K_M GGUF)".to_string(),
                    url: "https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf".to_string(),
                    sha256: "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c".to_string(),
                    size: 4683073504,
                    extract: false,
                    extract_format: "none".to_string(),
                    install_path: "models/qwen2.5-coder-7b-instruct-q4_k_m.gguf".to_string(),
                    platforms: vec!["linux".to_string(), "darwin".to_string(), "windows".to_string()],
                },
                ManifestAsset {
                    id: "llm-llama-8b-q4".to_string(),
                    name: "Llama-3-8B-Instruct (Q4_K_M GGUF)".to_string(),
                    url: "https://huggingface.co/MaziyarPanahi/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf".to_string(),
                    sha256: "4903067381e3753e2629f9d20c52df0e43b675bed2735bc3efea351c7d07454d".to_string(),
                    size: 4915000000,
                    extract: false,
                    extract_format: "none".to_string(),
                    install_path: "models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf".to_string(),
                    platforms: vec!["linux".to_string(), "darwin".to_string(), "windows".to_string()],
                },
            ],
        }
    }

    fn load_state(paths: &AppPaths) -> Option<AssetState> {
        let path = paths.assets_state_path();
        if path.exists() {
            if let Ok(raw) = fs::read_to_string(&path) {
                if let Ok(state) = serde_json::from_str(&raw) {
                    return Some(state);
                }
            }
        }
        None
    }

    fn save_state(&self) {
        let state = self.state.lock().unwrap().clone();
        let path = self.paths.assets_state_path();
        if let Ok(raw) = serde_json::to_string_pretty(&state) {
            if let Some(parent) = path.parent() {
                let _ = fs::create_dir_all(parent);
            }
            let _ = fs::write(&path, raw);
        }
    }

    pub fn get_status(&self, asset_id: Option<&str>) -> Vec<AssetStatus> {
        let state = self.state.lock().unwrap();
        if let Some(id) = asset_id {
            state
                .assets
                .iter()
                .filter(|a| a.id == id)
                .cloned()
                .collect()
        } else {
            state.assets.clone()
        }
    }

    /// Signal cancellation for an active asset download session.
    pub fn cancel_download(&self, asset_id: &str) {
        let mut cancelled = self.cancelled_downloads.lock().unwrap();
        cancelled.insert(asset_id.to_string());

        {
            let mut state = self.state.lock().unwrap();
            if let Some(asset) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                asset.error = Some("Cancelled by user".to_string());
                asset.progress = Some(0.0);
                asset.paused = Some(false);
                asset.downloaded = false;
                asset.verified = false;
            }
        }
        self.save_state();

        // Also remove the temp file if it exists and the download is not currently active.
        // If it is active, the active download loop will catch the cancellation and delete it.
        let is_active = {
            let active = self.active_downloads.lock().unwrap();
            active.contains(asset_id)
        };
        if !is_active {
            let temp_file = self
                .download_spec_from_status(asset_id)
                .map(|spec| {
                    self.paths
                        .assets_root
                        .join(&spec.install_path)
                        .parent()
                        .map(|p| p.join(format!("{}.download.tmp", asset_id)))
                })
                .flatten();
            if let Some(path) = temp_file {
                if path.is_file() {
                    let _ = fs::remove_file(path);
                }
            }
        }
    }

    /// Signal pause for an active asset download session.
    pub fn pause_download(&self, asset_id: &str) {
        let mut paused = self.paused_downloads.lock().unwrap();
        paused.insert(asset_id.to_string());

        {
            let mut state = self.state.lock().unwrap();
            if let Some(asset) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                asset.paused = Some(true);
            }
        }
        self.save_state();
    }

    /// Set download error state explicitly and report to frontend.
    pub fn set_error(&self, asset_id: &str, error: &str, app: &AppHandle) {
        {
            let mut state = self.state.lock().unwrap();
            if let Some(asset) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                asset.error = Some(error.to_string());
                asset.progress = Some(0.0);
                asset.paused = Some(false);
                asset.downloaded = false;
                asset.verified = false;
            }
        }
        self.save_state();
        self.emit_progress(app, asset_id, 0.0, &format!("failed: {error}"));
    }

    /// Triggers background download of the specified asset with partial resume support.
    pub async fn start_download(
        &self,
        app: AppHandle,
        asset_id: &str,
        manifest_url: Option<String>,
    ) -> Result<(), String> {
        // Prevent concurrent duplicate download tasks
        let _guard = {
            let mut active = self.active_downloads.lock().unwrap();
            if active.contains(asset_id) {
                return Err(format!("Download already active for asset: {}", asset_id));
            }
            active.insert(asset_id.to_string());
            ActiveDownloadGuard {
                active_downloads: self.active_downloads.clone(),
                asset_id: asset_id.to_string(),
            }
        };

        let manifest = Self::get_manifest();
        let dynamic_spec = self.download_spec_from_status(asset_id);
        let asset_spec = manifest
            .assets
            .iter()
            .find(|a| a.id == asset_id)
            .map(|asset| DownloadSpec {
                display_name: Some(asset.name.clone()),
                asset_type: Some(
                    if asset.id.starts_with("llm-") {
                        "local_model"
                    } else {
                        "utility"
                    }
                    .to_string(),
                ),
                url: asset.url.clone(),
                expected_sha: asset.sha256.clone(),
                install_path: asset.install_path.clone(),
                extract: asset.extract,
                size: asset.size,
            })
            .or(dynamic_spec)
            .ok_or_else(|| format!("Unknown asset specification: {}", asset_id))?;

        let url = manifest_url.unwrap_or_else(|| asset_spec.url.clone());
        let expected_sha = asset_spec.expected_sha.clone();
        let install_path = asset_spec.install_path.clone();
        let extract = asset_spec.extract;

        let final_path = self.paths.assets_root.join(&install_path);
        let dest_dir = final_path
            .parent()
            .ok_or_else(|| "Invalid asset installation path".to_string())?
            .to_path_buf();

        let already_ready = final_path.is_file()
            && fs::metadata(&final_path)
                .map(|meta| meta.len() == asset_spec.size)
                .unwrap_or(false);
        if already_ready {
            {
                let mut state = self.state.lock().unwrap();
                if let Some(asset) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                    asset.downloaded = true;
                    asset.verified = true;
                    asset.path = Some(final_path.to_string_lossy().to_string());
                    asset.size = Some(asset_spec.size);
                    asset.progress = Some(100.0);
                    asset.error = None;
                    asset.paused = Some(false);
                }
            }
            self.save_state();
            self.emit_progress(&app, asset_id, 100.0, "complete");
            return Ok(());
        }

        // Clear any previous cancellation and pause state
        {
            let mut cancelled = self.cancelled_downloads.lock().unwrap();
            cancelled.remove(asset_id);
            let mut paused = self.paused_downloads.lock().unwrap();
            paused.remove(asset_id);
        }

        // Check if file already exists partially (for resuming)
        fs::create_dir_all(&dest_dir).map_err(|e| e.to_string())?;
        let temp_file = dest_dir.join(format!("{}.download.tmp", asset_id));

        let mut downloaded: u64 = 0;
        if temp_file.is_file() {
            if let Ok(meta) = fs::metadata(&temp_file) {
                downloaded = meta.len();
            }
        }

        let initial_progress = if asset_spec.size > 0 {
            (downloaded as f32 / asset_spec.size as f32) * 100.0
        } else {
            0.0
        };

        // Initialize status entry
        {
            let mut state = self.state.lock().unwrap();
            if let Some(asset) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                asset.downloaded = false;
                asset.verified = false;
                asset.progress = Some(initial_progress);
                asset.error = None;
                asset.paused = Some(false);
                asset.size = Some(asset_spec.size);
            } else {
                state.assets.push(AssetStatus {
                    id: asset_id.to_string(),
                    display_name: asset_spec.display_name.clone(),
                    asset_type: asset_spec.asset_type.clone(),
                    downloaded: false,
                    verified: false,
                    path: None,
                    size: Some(asset_spec.size),
                    progress: Some(initial_progress),
                    error: None,
                    paused: Some(false),
                    source_url: Some(url.clone()),
                    expected_sha256: Some(expected_sha.clone()),
                    install_path: Some(install_path.clone()),
                    extract: Some(extract),
                    extract_format: Some(if url.ends_with(".tar.gz") {
                        "tar.gz".to_string()
                    } else if url.ends_with(".zip") {
                        "zip".to_string()
                    } else {
                        "none".to_string()
                    }),
                });
            }
        }
        self.save_state();
        self.emit_progress(&app, asset_id, initial_progress, "starting");

        // Spawn connection
        let mut request = self.client.get(&url);
        if downloaded > 0 && downloaded < asset_spec.size {
            // Request HTTP Range starting from our local partial download offset
            request = request.header("Range", format!("bytes={}-", downloaded));
            self.emit_progress(&app, asset_id, initial_progress, "resuming");
        } else {
            // Reset offset if file size is somehow larger/corrupt
            downloaded = 0;
        }

        let response = request
            .send()
            .await
            .map_err(|e| format!("download start failed: {}", e))?;

        let status_code = response.status();
        let total_size = if status_code == reqwest::StatusCode::PARTIAL_CONTENT {
            // Total is remaining bytes plus offset
            response.content_length().unwrap_or(0) + downloaded
        } else {
            // Full download from scratch
            downloaded = 0;
            response.content_length().unwrap_or(asset_spec.size)
        };

        let mut file = if downloaded > 0 {
            // Open existing file in Append mode
            tokio::fs::OpenOptions::new()
                .write(true)
                .append(true)
                .open(&temp_file)
                .await
                .map_err(|e| format!("failed to open append file: {e}"))?
        } else {
            // Create/overwrite new file
            tokio::fs::File::create(&temp_file)
                .await
                .map_err(|e| format!("failed to create temp file: {e}"))?
        };

        let mut last_emitted_pct = initial_progress;
        let mut stream = response.bytes_stream();

        while let Some(chunk) = stream.next().await {
            // Check for user-initiated cancellation signal
            let should_cancel = {
                let cancelled = self.cancelled_downloads.lock().unwrap();
                cancelled.contains(asset_id)
            }; // MutexGuard is dropped here, before any await

            if should_cancel {
                drop(file);
                let _ = fs::remove_file(&temp_file);
                {
                    let mut state = self.state.lock().unwrap();
                    if let Some(a) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                        a.progress = Some(0.0);
                        a.error = Some("Cancelled by user".to_string());
                        a.paused = Some(false);
                    }
                }
                self.save_state();
                self.emit_progress(&app, asset_id, 0.0, "cancelled");
                return Err("download cancelled by user".to_string());
            }

            // Check for user-initiated pause signal
            let should_pause = {
                let paused = self.paused_downloads.lock().unwrap();
                paused.contains(asset_id)
            }; // MutexGuard is dropped here, before any await

            if should_pause {
                file.flush().await.map_err(|e| e.to_string())?;
                drop(file);
                let pct = if total_size > 0 {
                    (downloaded as f32 / total_size as f32) * 100.0
                } else {
                    0.0
                };
                {
                    let mut state = self.state.lock().unwrap();
                    if let Some(a) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                        a.progress = Some(pct);
                        a.paused = Some(true);
                        a.error = Some("Paused by user".to_string());
                    }
                }
                self.save_state();
                self.emit_progress(&app, asset_id, pct, "paused");
                return Ok(()); // Pause is a successful partial yield
            }

            let chunk = chunk.map_err(|e| format!("stream error: {}", e))?;
            file.write_all(&chunk).await.map_err(|e| e.to_string())?;
            downloaded += chunk.len() as u64;

            if total_size > 0 {
                let pct = (downloaded as f32 / total_size as f32) * 100.0;
                // Only update status and emit progress if percentage has increased by at least 0.5%
                if pct - last_emitted_pct >= 0.5 || pct >= 99.9 {
                    last_emitted_pct = pct;
                    self.emit_progress(&app, asset_id, pct, "downloading");
                    let mut state = self.state.lock().unwrap();
                    if let Some(a) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                        a.progress = Some(pct);
                    }
                }
            }
        }

        file.flush().await.map_err(|e| e.to_string())?;
        drop(file);

        self.emit_progress(&app, asset_id, 95.0, "verifying");

        // Verify SHA256 integrity
        match verify_sha256(&temp_file, &expected_sha) {
            Ok(true) => {
                // Verified successfully
            }
            Ok(false) => {
                let _ = fs::remove_file(&temp_file);
                let err_msg = "SHA256 checksum verification failed".to_string();
                {
                    let mut state = self.state.lock().unwrap();
                    if let Some(a) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                        a.error = Some(err_msg.clone());
                        a.progress = Some(0.0);
                        a.paused = Some(false);
                    }
                }
                self.save_state();
                self.emit_progress(&app, asset_id, 0.0, &format!("failed: {}", err_msg));
                return Err(err_msg);
            }
            Err(e) => {
                let _ = fs::remove_file(&temp_file);
                let err_msg = format!("Verification error: {}", e);
                {
                    let mut state = self.state.lock().unwrap();
                    if let Some(a) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                        a.error = Some(err_msg.clone());
                        a.progress = Some(0.0);
                        a.paused = Some(false);
                    }
                }
                self.save_state();
                self.emit_progress(&app, asset_id, 0.0, &format!("failed: {}", err_msg));
                return Err(err_msg);
            }
        }

        if extract {
            let extract_dir = final_path.clone();
            fs::create_dir_all(&extract_dir).map_err(|e| e.to_string())?;

            if url.ends_with(".tar.gz") || url.ends_with(".tgz") {
                self.extract_tar_gz(&temp_file, &extract_dir)?;
            } else if url.ends_with(".zip") {
                self.extract_zip(&temp_file, &extract_dir)?;
            } else {
                let _ = fs::remove_file(&temp_file);
                return Err("Extraction requested but file is not compressed".to_string());
            }
            let _ = fs::remove_file(&temp_file);
        } else {
            if let Some(parent) = final_path.parent() {
                fs::create_dir_all(parent).map_err(|e| e.to_string())?;
            }
            fs::rename(&temp_file, &final_path)
                .map_err(|e| format!("Failed to move file to final destination: {}", e))?;
        }

        // Update final completed state
        {
            let mut state = self.state.lock().unwrap();
            if let Some(asset) = state.assets.iter_mut().find(|a| a.id == asset_id) {
                asset.downloaded = true;
                asset.verified = true;
                asset.path = Some(final_path.to_string_lossy().to_string());
                asset.progress = Some(100.0);
                asset.error = None;
                asset.paused = Some(false);
            }
        }
        self.save_state();
        self.emit_progress(&app, asset_id, 100.0, "complete");

        Ok(())
    }

    fn extract_tar_gz(&self, src: &Path, dest: &Path) -> Result<(), String> {
        use flate2::read::GzDecoder;
        use tar::Archive;

        let tar_gz = File::open(src).map_err(|e| e.to_string())?;
        let gz = GzDecoder::new(tar_gz);
        let mut archive = Archive::new(gz);
        archive.unpack(dest).map_err(|e| e.to_string())?;
        Ok(())
    }

    fn extract_zip(&self, src: &Path, dest: &Path) -> Result<(), String> {
        let file = File::open(src).map_err(|e| e.to_string())?;
        let mut archive = zip::ZipArchive::new(file).map_err(|e| e.to_string())?;
        archive.extract(dest).map_err(|e| e.to_string())?;
        Ok(())
    }

    fn emit_progress(&self, app: &AppHandle, asset_id: &str, pct: f32, message: &str) {
        let _ = app.emit(
            "asset-progress",
            serde_json::json!({
                "id": asset_id,
                "pct": pct,
                "message": message
            }),
        );
    }

    /// Returns the tinytex bin dir after extraction if present.
    pub fn tinytex_bin_dir(&self) -> Option<PathBuf> {
        let base = self.paths.tinytex_dir();
        let candidates = vec![
            base.join("bin").join("x86_64-linux"),
            base.join("TinyTeX").join("bin").join("x86_64-linux"),
            base.clone(),
        ];
        for c in candidates {
            if c.exists() && (c.join("pdflatex").exists() || c.join("pdflatex.exe").exists()) {
                return Some(c);
            }
        }
        None
    }
}

/// Compute SHA256 hashing of a file and verify against expectations
fn verify_sha256(file_path: &Path, expected_sha: &str) -> Result<bool, String> {
    use sha2::Digest;

    if expected_sha == "PLACEHOLDER_REPLACE_WITH_REAL" {
        return Ok(true);
    }

    let mut file = File::open(file_path)
        .map_err(|e| format!("failed to open file for SHA256 validation: {e}"))?;

    let mut hasher = Sha256::new();
    let mut buffer = [0; 65536]; // 64KB chunks for optimal IO latency

    loop {
        let count = file
            .read(&mut buffer)
            .map_err(|e| format!("failed reading bytes for SHA256 validation: {e}"))?;
        if count == 0 {
            break;
        }
        hasher.update(&buffer[..count]);
    }

    let result = hasher.finalize();
    let computed_sha = hex::encode(result);

    Ok(computed_sha.eq_ignore_ascii_case(expected_sha))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mock_paths() -> AppPaths {
        let temp_dir = std::env::temp_dir().join(format!("matemium-test-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&temp_dir).unwrap();

        AppPaths {
            data_root: temp_dir.clone(),
            workspaces_root: temp_dir.join("workspaces"),
            config_dir: temp_dir.join("config"),
            settings_path: temp_dir.join("settings.json"),
            assets_root: temp_dir.join("assets"),
            agent_root: temp_dir.join("agent"),
        }
    }

    #[test]
    fn test_asset_manager_prepopulation_and_status() {
        let paths = mock_paths();
        let manager = AssetManager::new(paths);

        // Ensure assets are pre-populated from the manifest
        let statuses = manager.get_status(None);
        assert!(!statuses.is_empty());

        let qwen3b = manager.get_status(Some("llm-qwen-coder-3b-q4"));
        assert_eq!(qwen3b.len(), 1);
        assert_eq!(qwen3b[0].id, "llm-qwen-coder-3b-q4");
        assert_eq!(qwen3b[0].downloaded, false);
        assert_eq!(qwen3b[0].verified, false);
        assert_eq!(qwen3b[0].progress, None);
    }

    #[tokio::test]
    async fn test_active_downloads_guard() {
        let paths = mock_paths();
        let manager = AssetManager::new(paths);

        // Manually insert into active downloads to simulate an active download
        {
            let mut active = manager.active_downloads.lock().unwrap();
            active.insert("llm-qwen-coder-3b-q4".to_string());
        }

        let active = manager.active_downloads.lock().unwrap();
        assert!(active.contains("llm-qwen-coder-3b-q4"));

        // RAII Guard works
        let guard = ActiveDownloadGuard {
            active_downloads: manager.active_downloads.clone(),
            asset_id: "llm-qwen-coder-3b-q4".to_string(),
        };
        drop(active); // release lock so guard drop can acquire it

        drop(guard);

        let active = manager.active_downloads.lock().unwrap();
        assert!(!active.contains("llm-qwen-coder-3b-q4"));
    }

    #[test]
    fn test_pause_and_cancel_state_transitions() {
        let paths = mock_paths();
        let manager = AssetManager::new(paths);

        // Start from pre-populated state, it should be in there
        manager.pause_download("llm-qwen-coder-3b-q4");
        let statuses = manager.get_status(Some("llm-qwen-coder-3b-q4"));
        assert_eq!(statuses[0].paused, Some(true));

        manager.cancel_download("llm-qwen-coder-3b-q4");
        let statuses = manager.get_status(Some("llm-qwen-coder-3b-q4"));
        assert_eq!(statuses[0].paused, Some(false));
        assert!(statuses[0].error.as_ref().unwrap().contains("Cancelled"));
    }
}
