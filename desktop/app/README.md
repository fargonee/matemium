# Matemium Desktop — TypeScript Frontend

Vite + React + Monaco editor for the Tauri shell.

## Features (MVP shipping)

- Project list — create, open, delete
- Phase-aware project sidebar — shows only the shared and selected-path artifacts that are relevant now
- Monaco Python editor (`scenes.py` + `helpers.py`) with lint markers
- Section outline from `# ---DIV:` comments
- Toolbar — Save, Lint, Check, Render (quality selection)
- Scene picker from `sidecar_list_scenes`
- Output log + sidecar event stream + progress panel
- MP4 preview via `convertFileSrc`
- Project-manager chat with Description/Passport interviews, recommended option polls, explicit production-path selection, and proactive artifact/Roadmap ownership
- Managed tape-content files, TTS/custom-audio generation, custom-audio transcription, approval gates, and quality-preserving final audio assembly
- Settings — server URL, API token, auth (stub or real Supabase/Google)
- Render modal, bottom dock tabs (progress, terminal, outputs)

## Workspace sidebar lifecycle

When a project is open, the left sidebar primarily navigates the active production path. Before the path decision it shows Description, Passport, and Roadmap. Afterward it progressively exposes the relevant branch:

```
Current Project
├── Brief
│   ├── Description
│   ├── Passport + production path
│   ├── Tapes/*.md
│   ├── Orchestration
│   ├── Selected-path audio artifacts
│   └── Roadmap
├── Authoring
│   ├── scenes.py
│   └── helpers.py
├── Assets
│   ├── Images
│   ├── Video
│   └── Audio
└── Renders
    ├── Latest
    └── History
```

The exact branch and gate ordering are normative in [the AI-led production lifecycle](../../product-production-lifecycle.md). The Roadmap records the current phase and evidence. Ordinary users can work through AI chat and approval controls; raw Markdown, JSON, timestamps, and Python remain available as advanced surfaces.

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
