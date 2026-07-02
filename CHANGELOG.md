# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-06-30

### Added
- 3D world structures (TapeObject, WorldTransform, keyframes, mixed placement) added.
- **Clarification (July 2026):** Tape is observed as a normal 3D object by default. Only explicit tape-scroll-mode (`TapeScroll`) activates internal sheet behaviors. See `3D-WORLD-DESCRIPTION.md` and `TODO-3d-tape-observation-enhancement.md`. Full realization of differentiated observation is still needed. Legacy tape behavior is preserved.
- Auto-registration of all built-in object kinds; registry dispatch is primary path (no more core if/elif patching for new viz).
- Enhanced Space3DDemo showcasing rotated tape, add_object, relative anchors, mixed camera keyframes (ObjectAnchor/TapeScroll/WorldPoint).
- Comprehensive Phase 10 tests for registration, resolution, DSL roundtrips, mixed builder, dispatch parity.
- Exports for Vector3/World* / Observation* in canvas top-level for easy authoring.

### Changed
- measure.py: extracted builders + _auto_register_builtins; measure_element delegates to kind "measure" when present.
- Builder, scene, DSL keep full backward compat (old add_* populate root_tape; legacy projects unaffected).
- Docs and shared templates reflect unified 3D + tape model as default.

### Fixed / Polished
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

[0.1.0]: https://github.com/matemium/matemium/releases/tag/v0.1.0