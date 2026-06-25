# Matemium Desktop — TypeScript Frontend

Vite + React + Monaco editor for the Tauri shell.

## Features (Phase 5 MVP)

- Project list — create, open, delete
- Monaco Python editor with lint markers
- Section outline from `# ---DIV:` comments
- Toolbar — Save, Lint, Check, Render (preview/low)
- Scene picker from `sidecar_list_scenes`
- Output log + sidecar event stream
- MP4 preview via `convertFileSrc`
- AI chat panel with Apply edit
- Settings — server URL, API token, dev login (`auth_login` → `/v1/auth/token`)

## Dev

```bash
cd desktop/app && npm install && npm run dev
# or full desktop loop:
cd desktop/src-tauri && cargo tauri dev
```

## Build

```bash
npm run build   # outputs to dist/ — consumed by Tauri
```

Protocol: all engine work via Tauri `invoke()` — see [`src/api/tauri.ts`](src/api/tauri.ts).