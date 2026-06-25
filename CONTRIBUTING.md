# Contributing to Matemium

Thank you for helping improve Matemium.

**Product direction:** Monorepo with three deployable layers — see [`STRUCTURE.md`](STRUCTURE.md) and [`desktop-architecture.md`](desktop-architecture.md). Users author **`scenes.py`** per project with **AI chat** assistance. Cloud handles auth + chat only; all Manim renders run in a **PyInstaller sidecar** on the user's machine.

| Layer | Path |
|-------|------|
| Engine | `canvas/`, `matemium/`, `projects/` |
| Server | `server/` |
| Desktop | `desktop/` (Tauri — all OS targets) |

## Development setup

```bash
git clone <your-fork-url>
cd math
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

System dependencies for Manim renders:

- FFmpeg
- LaTeX (e.g. `texlive-full` or a minimal TeX install with `standalone`, `preview`, `amsmath`)

## Running tests

```bash
pytest                    # unit tests (default; skips slow renders)
pytest -m slow            # optional full Manim smoke render
```

## Architecture rules

1. **Engine stays generic** — no lesson-specific APIs on `CanvasBuilder`. Put topic helpers in `projects/<name>/helpers.py`.
2. **Sheet model** — content on the XY plane at `z=0`; camera scrolls on Y.
3. **Test scenes validate abstractions** — demo projects should exercise engine features, not patch core for one lesson.
4. **Desktop authoring is code** — AI edits `scenes.py`, not Sheet DSL JSON. New engine features must be reachable via `CanvasBuilder`.
5. **Section fences** — prefer `# ---DIV: Title---` + `part_*` functions in templates and examples.

See [`desktop-architecture.md`](desktop-architecture.md) (product boundaries), [`architecture.md`](architecture.md) (engine + §8 desktop rules), and [`project-spec.md`](project-spec.md) before large changes.

**Desktop boundary rule:** TypeScript UI ↔ Rust (Tauri) ↔ Python sidecar only. No cross-language imports across layers. Internal `SheetDSL` must remain JSON-serializable for debugging; it is not the product authoring format.

**Cross-platform builds:** TS/Rust are shared; PyInstaller sidecars are **not** — build `matemium-sidecar` on each target OS (CI matrix). Never hardcode path separators; use `PathBuf` / `os.path.join`. Details: [`desktop/targets/README.md`](desktop/targets/README.md).

## Pull request checklist

- [ ] Tests pass locally (`pytest`)
- [ ] New engine features include unit tests where practical
- [ ] Public API changes are noted in `CHANGELOG.md`
- [ ] Lesson-only logic is not added to `canvas/`

## Commit style

Use clear, imperative subjects: `Add viewport-safe zoom cap`, `Fix inspect path densify for 2-keyframe paths`.

## Questions

Open a GitHub issue for design questions before large refactors.