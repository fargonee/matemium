use crate::assets::AssetManager;
use crate::sidecar::SidecarManager;
use crate::workspace::AppPaths;

pub struct AppState {
    pub paths: AppPaths,
    pub sidecar: SidecarManager,
    pub assets: AssetManager,
}