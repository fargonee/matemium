# Shared Contracts

Cross-layer schemas and protocol references. **No runtime code** — only contracts both desktop and server (or engine and desktop) agree on.

| Path | Consumers |
|------|-----------|
| [`schemas/project.schema.json`](schemas/project.schema.json) | Desktop workspace `project.json` |
| [`schemas/chat-completion.schema.json`](schemas/chat-completion.schema.json) | Server API ↔ desktop client |
| [`protocols/sidecar-ipc.md`](protocols/sidecar-ipc.md) | Desktop Rust ↔ engine sidecar |
| [`prompts/scene-authoring-system.txt`](prompts/scene-authoring-system.txt) | v1 chat system prompt |
| [`prompts/agent-system.txt`](prompts/agent-system.txt) | v2 autonomous agent system prompt |
| [`templates/scenes.py`](templates/scenes.py) | New project `scenes.py` template |

Target desktop project templates should cover `scenes.py`, `helpers.py`, `brief/passport.json`, `brief/description.md`, `brief/tape.md`, `brief/roadmap.json`, `brief/narration.md`, and empty `assets/` folders. `assets` means real project media or app-managed runtime downloads, not Python helper code.

Engine Python types remain authoritative for `SheetDSL` (internal IR). Do not duplicate the full DSL schema here until a JSON authoring path returns.
