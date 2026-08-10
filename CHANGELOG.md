# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-08-09

### Added
- Isolated camera-facing secondary tapes with automatic world → tape,
  tape → tape, and tape → world curtain transitions.
- A serializable `TapeScroll` target and working `scroll_tape()` authoring
  sugar for explicit tape selection/local scrolling.
- Desktop preview payloads now include every tape and element ownership; the
  manim-web replay uses exclusive world/tape curtain contexts.
- Stable explicit IDs and complete transform bookkeeping for registered free
  objects created by `add_object()`.
- A cinematic orbital flagship proving a persistent project-local 3D kind,
  multiple analytical tapes, an embedded tape solid, semantic vectors,
  deterministic regime morphs, and camera paths in one production.
- Generic `DataPath`, `DataPlot`, and `Diagram` visual kinds backed by sampled,
  JSON-compatible data.
- Stable semantic-part addressing for compound visuals:
  `path`, `axes`, `series:<id>`, `marker:<id>`, `node:<id>`,
  `edge:<id>`, and `edge-label:<id>`.
- `StateTransition` for synchronized allowlisted visual-property patches and
  `ElementMorph` for registered-pipeline content/geometry replacement.
- Registered-kind content validators and semantic-part declarations, strict
  pre-render validation, and structured project-check diagnostics.
- Eleven deterministic first-pass flagship projects across subjects.
- Source-aligned `AUTHORING_API.md` and public docs for generic visuals/actions.
- Corrected authoring docs to distinguish camera-facing tapes from transformed
  free-world objects.
- 3D world structures (TapeObject, WorldTransform, keyframes, mixed placement) added.
- **Presentation clarification (July 2026):** tapes are isolated camera-facing
  layouts rather than world objects. `TapeScroll` is available for explicit
  selection, and legacy root-tape movement remains available through
  `CameraMove`.
- Auto-registration of all built-in object kinds; registry dispatch is primary path (no more core if/elif patching for new viz).
- Enhanced spatial examples showcasing `add_object`, relative anchors, and
  mixed world/tape camera actions.
- Comprehensive Phase 10 tests for registration, resolution, DSL roundtrips, mixed builder, dispatch parity.
- Exports for Vector3/World* / Observation* in canvas top-level for easy authoring.

### Changed
- measure.py: extracted builders + _auto_register_builtins; measure_element delegates to kind "measure" when present.
- Builder, scene, DSL keep full backward compat (old add_* populate root_tape; legacy projects unaffected).
- Docs and shared templates reflect unified 3D + tape model as default.
- Root timeline elements with identity world transforms now retain tape-flow
  placement.
- Agent guidance now reflects cross-subject authoring and accurate method return
  types.

### Fixed / Polished
- Tape/world and tape/tape switches now hard-isolate managed contexts, including
  tapes whose first reveal is a flex group. Transitions use opacity-only fades
  around an instantaneous camera cut, so world and tape camera poses are never
  visibly interpolated.
- Smooth inspect paths preserve the first authored shot and use continuous
  linear timing across generated spline subsegments, removing repeated
  stop-start easing.
- Existing sheet videos continue to author and render identically; 3D features are opt-in extensions.
- Registry cutover ensures extensibility for future custom object kinds in both sheet and 3D contexts.

### Documentation (Phase 7)
- Added short section + example to `canvas/README.md`.
- Verified and updated agent prompts / shared prompts for clarified 3D + tape model (no old assumptions hard-coded).
- Added Phase 7 completion note here. Full TODO tracking in `TODO-3d-tape-observation-enhancement.md`.

## Phase 10: Full Migration, Examples, Tests & Cutover
- 3D world model (XZ ground / Y up) declared canonical.
- Projects/demos continue to work via shims; Space3DDemo and shared template demonstrate mixed authoring.
- All core types auto-registered; legacy direct type chains minimized.
- Comprehensive tests + docs + changelog updated.

## [0.2.0] - 2026-06-30

### Added

- Full Tauri v2 desktop application (Linux .deb/.AppImage) with Monaco Python editor, section outline (`# ---DIV:`), AI chat panel, project workspaces (`scenes.py` + `assets.py` support), render pipeline with progress, MP4 preview.
- Production auth (Supabase, Google sign-in via `/v1/auth/session`), admin console routes, billing via Lemon Squeezy (checkout/portal/webhooks synced to profiles).
- GitHub Actions: engine CI, zero-downtime backend deploy (Northflank), frontend deploy (Cloudflare Pages) with safe rollback on health failure.
- Desktop icons/logos updated to official branding.
- AI agent infrastructure: Python coordinator/critic/writer/patch engine (Search/Replace), Whisper timing, guard/watermarking, sidecar-backed self-correction compile loop; agent system prompts.
- Additional sidecar IPC: `lint_project`, `check_project`, `render_project`, `list_scenes`, `compile_preview`, `estimate_duration`, `export_sheet`, `cut_reels` + streamed `render_progress` events.
- Legal docs (Privacy, Terms) and contact email updates.

### Changed / Fixed

- Desktop build workflows, sidecar integration, auth flows (admin login, Google), CI test isolation and deduping.
- Server: full production wiring for auth/billing (stub still supported for dev); separate deploy triggers.
- Engine sidecar now primary for desktop; CLI remains for dev harness.
- Multiple deployment and frontend zero-downtime enhancements.

### Desktop / Product status (as of 2026-06)

- Linux desktop ships with bundled sidecar.
- Cross-platform: Windows/macOS binaries pending full CI matrix (Linux complete).
- v1 chat + initial two-file + chat-to-patch support in UI; full autonomous agent tool loop in progress.

## [0.1.0] - 2026-06-22

### Added

- Open-source packaging: `pyproject.toml`, `pip install -e .`, `matemium` console script
- Render quality profiles: `preview`, `draft`, `low`, `medium`, `high`, `final`
- Unit test suite and GitHub Actions CI
- MIT license, contributing guide, changelog
- Bundled project template for `matemium new` when workspace has no `projects/_template/`
- Workspace discovery via `MATEMIUM_ROOT` or current directory

### Changed

- `matemium render` quality flag now wires Manim `quality` and `frame_rate` settings

[Unreleased]: https://github.com/fargonee/matemium/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/fargonee/matemium/compare/v0.1.1...v0.3.0
[0.1.0]: https://github.com/fargonee/matemium/releases/tag/v0.1.0
