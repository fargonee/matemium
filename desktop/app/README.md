# Matemium Desktop — TypeScript Frontend

Vite + React + Monaco editor for the Tauri shell.

## Features (MVP shipping)

- Project list — create, open, delete
- Project sidebar — navigable curated project structure for Script, Helpers, Brief, Assets, and Renders
- Monaco Python editor (`scenes.py` + `helpers.py`) with lint markers
- Section outline from `# ---DIV:` comments
- Toolbar — Save, Lint, Check, Render (quality selection)
- Scene picker from `sidecar_list_scenes`
- Output log + sidecar event stream + progress panel
- MP4 preview via `convertFileSrc`
- AI chat panel with Apply edit / diff support
- Settings — server URL, API token, auth (stub or real Supabase/Google)
- Render modal, bottom dock tabs (progress, terminal, outputs)

## Workspace sidebar target

When a project is open, the left sidebar should primarily navigate the project contents, not just list projects. It should present the curated production map:

```
Current Project
├── Script
│   └── scenes.py
├── Helpers
│   └── helpers.py
├── Brief
│   ├── Passport
│   ├── Description
│   ├── Tape
│   ├── Roadmap
│   └── Narration
├── Assets
│   ├── Images
│   ├── Video
│   └── Audio
└── Renders
    ├── Latest
    └── History
```

Each item opens its natural surface: code editor for Script/Helpers, structured Passport editor, AI-owned read-only Roadmap, Markdown/script editors for Tape/Narration/Description, asset browser for Assets, and output history for Renders. The sidebar shows selection, dirty state, validation badges, and collapsed/expanded folders.

## Dev

First install dependencies (once):

```bash
cd desktop/app && npm install
```

Then either:

```bash
# Standalone frontend only
cd desktop/app && npm run dev
```

or (recommended for full app):

```bash
cd desktop && cargo tauri dev
```

(The `cargo tauri dev` command will automatically start Vite for you via `beforeDevCommand`.)

## Build

```bash
npm run build   # outputs to dist/ — consumed by Tauri
```

Protocol: all engine work via Tauri `invoke()` — see [`src/api/tauri.ts`](src/api/tauri.ts).
