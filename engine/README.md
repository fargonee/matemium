# Engine Layer

The **local compilation engine** — Manim-based layout-to-animation compiler packaged as a PyInstaller sidecar for the desktop app.

## Packages (at repository root)

| Path | Role |
|------|------|
| [`canvas/`](../canvas/) | Compiler core — DSL, `CanvasBuilder`, `CanvasScene`, generic visuals/actions, camera, layout |
| [`matemium/`](../matemium/) | CLI (`matemium`) + desktop sidecar (`matemium-sidecar`, `matemium/ipc/`) |
| [`projects/`](../projects/) | Dev harness — one folder per test scene; mirrors desktop `scenes.py` model |

## Install (development)

```bash
# from repository root
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
./matemium.sh demo
```

## Sidecar (production path)

The desktop app does not shell out to `matemium` CLI. It spawns the frozen binary:

```bash
python -m matemium.sidecar          # dev
matemium-sidecar                    # after pip install
```

Protocol: [`matemium/ipc/PROTOCOL.md`](../matemium/ipc/PROTOCOL.md)

PyInstaller spec: [`desktop/packaging/matemium-sidecar.spec`](../desktop/packaging/matemium-sidecar.spec)

## Boundaries

- Engine code **must not** import from `server/` or `desktop/`.
- `SheetDSL` JSON IPC is for **dev/tests**; desktop authors via **`scenes.py`** + implemented project commands including `lint_project`, `check_project`, and `render_project`.
- Topic-specific logic stays in `projects/<name>/helpers.py`, not in `canvas/`.
- Cross-subject core visuals are `DataPath`, `DataPlot`, and `Diagram`; timeline state uses `StateTransition` and `ElementMorph`.
- `CanvasScene` validates structural DSL strictly before render by default.
- The automatic root tape is the mature default. Additional tapes and
  free-world camera composition are experimental.
- Do not use or document `scroll_tape()` as working until a real `TapeScroll`
  DSL target is implemented.

## Specs

- [`architecture.md`](../architecture.md) — engine design + §8 desktop constraints
- [`canvas/USAGE.md`](../canvas/USAGE.md) — authoring API
- [`AUTHORING_API.md`](../AUTHORING_API.md) — current signatures, schemas, semantic parts, and validation
