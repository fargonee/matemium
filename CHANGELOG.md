# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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