# Shared Contracts

Cross-layer schemas and protocol references. **No runtime code** — only contracts both desktop and server (or engine and desktop) agree on.

| Path | Consumers |
|------|-----------|
| [`schemas/project.schema.json`](schemas/project.schema.json) | Desktop workspace `project.json` |
| [`schemas/passport.schema.json`](schemas/passport.schema.json) | Phase-2 creative identity and production-path selection |
| [`schemas/roadmap.schema.json`](schemas/roadmap.schema.json) | AI-owned phase route, evidence, invalidation, and blockers |
| [`schemas/timestamps.schema.json`](schemas/timestamps.schema.json) | Verified custom-audio segment alignment |
| [`schemas/chat-completion.schema.json`](schemas/chat-completion.schema.json) | Server API ↔ desktop client |
| [`schemas/project-questions.schema.json`](schemas/project-questions.schema.json) | AI project-manager chat polls |
| [`schemas/project-preference-response.schema.json`](schemas/project-preference-response.schema.json) | Durable preference-answer events |
| [`protocols/sidecar-ipc.md`](protocols/sidecar-ipc.md) | Desktop Rust ↔ engine sidecar |
| [`prompts/scene-authoring-system.txt`](prompts/scene-authoring-system.txt) | v1 chat system prompt |
| [`prompts/agent-system.txt`](prompts/agent-system.txt) | v2 autonomous agent system prompt |
| [`prompts/project-manager-system.txt`](prompts/project-manager-system.txt) | Creative producer behavior and interview protocol |
| [`templates/scenes.py`](templates/scenes.py) | New project `scenes.py` template |

Target desktop project templates cover `scenes.py`, `helpers.py`, shared lifecycle artifacts (`brief/passport.json`, `brief/description.md`, `brief/tapes/main.md`, `brief/orchestration.md`, `brief/roadmap.json`), path-specific TTS/custom-audio artifacts, and empty `assets/` folders. The UI exposes path-specific files only after `production_path` is selected. `assets` means real project media or app-managed runtime downloads, not Python helper code. See [`docs/product-production-lifecycle.md`](../docs/product-production-lifecycle.md).

Engine Python types remain authoritative for `SheetDSL` (internal IR). Do not duplicate the full DSL schema here until a JSON authoring path returns.
