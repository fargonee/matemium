# Sidecar IPC (reference)

Canonical spec: [`matemium/ipc/PROTOCOL.md`](../../matemium/ipc/PROTOCOL.md)

Transport: newline-delimited JSON on the PyInstaller `matemium-sidecar` process stdin/stdout.

Desktop Rust (`desktop/src-tauri/`) owns process lifecycle. TypeScript never writes to the sidecar directly.