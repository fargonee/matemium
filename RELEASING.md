# Releasing Matemium Desktop

The desktop release is built natively on Linux, Windows, Apple Silicon macOS,
and Intel macOS. A tag starts the platform builds; a separate publish workflow
collects their artifacts into one draft GitHub release. Keeping publication
separate prevents a partially built release from becoming public.

## Supported launch targets

| Platform | Artifact | Launch baseline | Rendering prerequisites |
| --- | --- | --- | --- |
| Linux x86_64 | `.deb`, `.AppImage` | Ubuntu 24.04 or compatible | Debian installs declare FFmpeg + TeX dependencies; AppImage users install FFmpeg and TeX Live |
| Windows x86_64 | NSIS `.exe`, `.msi` | Windows 10/11 | FFmpeg and MiKTeX |
| macOS Apple Silicon | `.dmg` | macOS 12+ | FFmpeg and MacTeX/BasicTeX |
| macOS Intel | `.dmg` | macOS 12+ | FFmpeg and MacTeX/BasicTeX |

The installers contain the Matemium UI, Rust shell, and native Python sidecar.
They do not contain FFmpeg, LaTeX, local language models, or provider API keys.

## One-time repository setup

- Protect `main`; require the core CI and desktop verification jobs.
- Add Apple signing/notarization secrets when available:
  `APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_ID`,
  `APPLE_PASSWORD`, and `APPLE_TEAM_ID`.
- Add Windows signing to the Windows workflow when a certificate or trusted
  signing account is available. Unsigned Windows builds work but trigger
  SmartScreen warnings.
- Confirm the production server URL in `desktop/app/src/config.json` and run a
  live `/health` check before tagging.

Without Apple credentials the workflow applies an ad-hoc signature. Users must
still approve the application in macOS Privacy & Security. A public macOS
launch should use Developer ID signing and notarization as soon as credentials
are available.

## Release procedure

1. Update all user-facing entries under `[Unreleased]` in `CHANGELOG.md` and
   move them into the intended version section.
2. Synchronize versions in `pyproject.toml`, `matemium/__version__.py`,
   `desktop/app/package.json`, `desktop/app/package-lock.json`,
   `desktop/src-tauri/Cargo.toml`, its lock file, and `tauri.conf.json`.
3. Run the local gate:

   ```bash
   python scripts/check_release.py v0.3.0
   pytest
   npm ci --prefix desktop/app
   npm run build --prefix desktop/app
   cargo test --manifest-path desktop/src-tauri/Cargo.toml
   ```

4. Commit and push the release preparation. Wait for required checks on
   `main`, then create and push an annotated tag:

   ```bash
   git tag -a v0.3.0 -m "Matemium 0.3.0"
   git push origin main
   git push origin v0.3.0
   ```

5. Wait for **Build Linux Desktop**, **Build Windows Desktop**, and both jobs
   in **Build macOS Desktop** to succeed for the tag.
6. Run **Publish Desktop Release** with `tag=v0.3.0`. It verifies that all
   native runs came from the tagged commit, checks required artifact types,
   writes `SHA256SUMS.txt`, and creates a draft release.
7. Download and smoke-test at least one clean machine per platform. Verify app
   launch, project creation, sidecar ping, a text-only render, a MathTex render,
   video playback, and uninstall/reinstall while preserving user workspaces.
8. Edit the draft release notes with known limitations, then publish it.

Never reuse or move a published version tag. Fix a bad release with a new patch
version and mark the affected release accordingly.

## Known launch limitations

- Windows packages are unsigned until project signing credentials are added.
- macOS artifacts are only notarized when Apple credentials are configured.
- Rendering requires host-installed FFmpeg and LaTeX outside the Debian package.
- Automatic application updates are not enabled; users install newer releases
  manually.
- Only x86_64 Linux/Windows builds are produced in the initial release.

