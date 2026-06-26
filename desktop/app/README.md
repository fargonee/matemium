# Matemium Desktop — TypeScript Frontend

Vite + React + Monaco editor for the Tauri shell.

## Features (MVP shipping)

- Project list — create, open, delete
- Monaco Python editor (scenes.py + assets.py) with lint markers
- Section outline from `# ---DIV:` comments
- Toolbar — Save, Lint, Check, Render (quality selection)
- Scene picker from `sidecar_list_scenes`
- Output log + sidecar event stream + progress panel
- MP4 preview via `convertFileSrc`
- AI chat panel with Apply edit / diff support
- Settings — server URL, API token, auth (stub or real Supabase/Google)
- Render modal, bottom dock tabs (progress, terminal, outputs)

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