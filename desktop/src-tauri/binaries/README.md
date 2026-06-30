# Tauri externalBin — matemium-sidecar

Populated by `./desktop/scripts/build-sidecar.sh` (Phase 2).

**Not committed to git** (see root `.gitignore`).

In CI (light verify jobs) a tiny placeholder shell script is created on-the-fly so that `cargo check` / `tauri-build` can validate the declared `externalBin` resource without requiring the real (large) PyInstaller binary.

The real binary (with the platform triple suffix) is generated during full builds and overwrites any placeholder.

Expected platform artifacts (generated during CI builds or local platform builds):

```
matemium-sidecar-x86_64-unknown-linux-gnu
matemium-sidecar-x86_64-pc-windows-msvc.exe
matemium-sidecar-x86_64-apple-darwin
matemium-sidecar-aarch64-apple-darwin
```

Build on each target platform; PyInstaller does not cross-compile.