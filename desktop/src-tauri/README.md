# Matemium Desktop — Tauri v2 Shell

Rust orchestration layer. **Same Rust/TypeScript codebase** builds for Windows, macOS, and Linux — but the **PyInstaller sidecar must be built separately on each OS** (no cross-compile). See [`../targets/README.md`](../targets/README.md).

## Responsibilities

- Native window, menus, system tray
- **Project workspaces** — CRUD under app data dir (`PathBuf`; Linux `~/.local/share/matemium/workspaces/<id>/`, paths differ on Windows/macOS)
- Spawn/kill `matemium-sidecar` (`externalBin`)
- Bridge stdin/stdout NDJSON to TypeScript via Tauri events
- HTTP client to cloud chat API (`server/`)

## Sidecar binary

```bash
# from repository root
./desktop/scripts/build-sidecar.sh
# copies to src-tauri/binaries/matemium-sidecar-x86_64-unknown-linux-gnu
```

Configured in `tauri.conf.json`:

```json
{
  "bundle": {
    "externalBin": ["binaries/matemium-sidecar"],
    "linux": {
      "deb": {
        "depends": ["ffmpeg", "texlive-latex-extra", "texlive-fonts-extra", "texlive-science", "cm-super", "dvipng", "dvisvgm"]
      }
    }
  }
}
```

## Rust modules

| Module | Role |
|--------|------|
| `sidecar.rs` | Process spawn, stdin writer, stdout reader task |
| `protocol.rs` | Parse NDJSON; match responses; emit `sidecar-event` |
| `workspace.rs` | App data + config paths, `settings.json` |
| `projects.rs` | CRUD `project.json` + `scenes.py` |
| `commands.rs` | `invoke` handlers for TypeScript |
| `cloud.rs` | HTTP client to [`server/`](../../server/) |

## Tauri commands (Phase 4)

| Command | Description |
|---------|-------------|
| `project_list` | List workspaces with `project.json` |
| `project_create` | New UUID dir + template `scenes.py` (+ `assets.py` for agent) |
| `project_open` | Paths + `scenes.py` + `assets.py` content |
| `project_save` / `project_save_assets` | Write editor buffer(s) to disk |
| `project_delete` | Remove workspace dir |
| `sidecar_ping` | IPC `ping` |
| `sidecar_lint` | IPC `lint_project` |
| `sidecar_check` | IPC `check_project` |
| `sidecar_list_scenes` | IPC `list_scenes` |
| `sidecar_render` | IPC `render_project` |
| `sidecar_cancel` | Cancel running render job |
| `cloud_chat` | POST `/v1/chat/completions` |
| `auth_login` | POST `/v1/auth/token` (dev) or `/v1/auth/session` (Supabase / Google) |
| `settings_get` / `settings_set` | `~/.config/matemium/settings.json` |
| Outputs | `project_list_outputs`, delete, reveal, clear cache helpers |

Events: listen for `sidecar-event` (`{ event, data }`).

## Dev loop

```bash
./desktop/scripts/verify-phase4.sh
cd desktop/src-tauri
cargo tauri dev   # placeholder UI in ../app/dist
```

## Production build

```bash
./desktop/scripts/verify-phase3.sh
cd desktop/src-tauri && cargo tauri build
```

Artifacts: `target/release/bundle/deb/*.deb`, `target/release/bundle/appimage/*.AppImage`