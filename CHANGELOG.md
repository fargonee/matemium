# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-06-26

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