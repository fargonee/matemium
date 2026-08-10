use std::net::TcpListener;
use std::sync::{atomic::AtomicBool, Arc, Mutex};

use crate::agent_runs::AgentRunStore;
use crate::assets::AssetManager;
use crate::sidecar::SidecarManager;
use crate::workspace::AppPaths;

pub struct OpenRouterOAuthSession {
    pub listener: TcpListener,
    pub verifier: String,
    pub cancel: Arc<AtomicBool>,
}

pub struct AppState {
    pub paths: AppPaths,
    pub sidecar: SidecarManager,
    pub assets: AssetManager,
    pub agent_runs: AgentRunStore,
    pub openrouter_oauth_session: Mutex<Option<OpenRouterOAuthSession>>,
    pub openrouter_oauth_active_cancel: Mutex<Option<Arc<AtomicBool>>>,
    pub auth_browser_cancel: Mutex<Option<Arc<AtomicBool>>>,
}
