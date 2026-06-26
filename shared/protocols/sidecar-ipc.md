# Sidecar IPC (reference)

Canonical spec: [`matemium/ipc/PROTOCOL.md`](../../matemium/ipc/PROTOCOL.md) (commands include project lint/check/render + legacy dsl + progress events)

Transport: newline-delimited JSON on the PyInstaller `matemium-sidecar` process stdin/stdout.

Desktop Rust (`desktop/src-tauri/`) owns process lifecycle. TypeScript never writes to the sidecar directly.