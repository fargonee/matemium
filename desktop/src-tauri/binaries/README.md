# Tauri externalBin — matemium-sidecar

Populated by `./desktop/scripts/build-sidecar.sh` (Phase 2).

**Not committed to git** (see root `.gitignore`).

In CI (light verify jobs) a tiny placeholder shell script is created on-the-fly so that `cargo check` / `tauri-build` can validate the declared `externalBin` resource without requiring the real (large) PyInstaller binary.

The real binary (with the platform triple suffix) is generated during full builds and overwrites any placeholder.

Expected Linux artifact:

```
matemium-sidecar-x86_64-unknown-linux-gnu
```

Build on each target platform; PyInstaller does not cross-compile.