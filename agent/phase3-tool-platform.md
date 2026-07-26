# Agent Phase 3: Typed Tool Platform and Mutation Journal

**Implemented:** 2026-07-18

**Mutation authority:** Desktop/Tauri

Phase 3 implements safe local discovery and editing primitives for `state-machine-v2`. The platform does not expose arbitrary shell execution or unrestricted paths.

## Common result envelope

Every public tool operation returns `ToolResult`:

```json
{
  "status": "success | retryable_error | blocked | fatal_error",
  "code": "STABLE_MACHINE_CODE",
  "summary": "bounded human-readable summary",
  "data": {},
  "evidence": [],
  "retry_hint": null,
  "truncated": false
}
```

I/O failures, invalid arguments, policy violations, stale state, patch mismatches, ambiguity, journal failure, and rollback conflict have distinct codes. Rust errors are converted at the public tool boundary and cannot be mistaken for successful prose.

## Discovery tools

`desktop/src-tauri/src/agent_tools.rs` provides:

- `list_workspace`: lists only approved product files.
- `read_file_slice`: requires a bounded 1-based range and returns content-hash evidence.
- `search_workspace`: performs bounded literal search across approved files.

`ToolLimits` independently caps list entries, read lines, read bytes, search matches, and searched bytes. Results set `truncated` and `OUTPUT_TRUNCATED` whenever a limit affects the observation.

## Workspace policy

Read access is restricted to:

- `project.json`
- `scenes.py`
- `assets.py`

Mutation access is restricted to `scenes.py` and `assets.py`. Absolute paths, traversal components, nested paths, unapproved files, and symlinks resolving outside the workspace are blocked before access.

## Hash-guarded patches

`apply_patch` requires:

1. an approved mutation path;
2. the SHA-256 observed during a prior read;
3. non-empty exact search text;
4. exactly one match;
5. a localized patch rather than full-file replacement.

Successful results include before/after hashes, mutation ID, and changed line range. A stale hash never applies. Missing and ambiguous search blocks return separate retryable codes.

## Mutation journal and snapshots

The Phase 1 SQLite database now includes `agent_mutations`. Each mutation records:

- mutation and run IDs;
- approved relative path;
- before and after SHA-256;
- verified snapshot path;
- changed start/end lines;
- creation time and rollback state.

The original bytes are saved beneath the per-run artifact directory before replacement. The updated file is written through a same-directory temporary file. If mutation-record insertion fails, the platform restores the original bytes and removes the uncommitted snapshot.

Rollback verifies:

- the mutation belongs to the active run;
- it has not already been rolled back;
- current content still matches the mutation's after-hash;
- snapshot content matches the before-hash.

This prevents rollback from overwriting later user or agent work.

## Validation capability separation

Phase 3 defines distinct non-mutating capabilities and evidence types for:

| Capability | Executor | Evidence |
|---|---|---|
| Syntax check | Sidecar | Syntax diagnostics |
| Lint | Sidecar | Lint diagnostics |
| Project check | Sidecar | Project diagnostics |
| Compile preview | Sidecar | Compile manifest |
| Render | Sidecar | Render manifest |
| Visual inspection | Desktop | Visual-inspection record |

This prevents the earlier `run_compiler` ambiguity from treating syntax checks, rendering, and visual correctness as equivalent. The policy and verification phases will select and enforce these capabilities.

## Verification

`desktop/src-tauri/tests/agent_tools_platform.rs` covers:

- deterministic truncation reporting;
- absolute path, traversal, nested path, and unapproved-file attacks;
- symlink escape;
- stale precondition rejection;
- ambiguous patch rejection;
- mutation hashes, changed ranges, journal rows, and snapshots;
- successful rollback;
- refusal to overwrite newer edits during rollback;
- distinct validation capability definitions.

The existing Phase 1 state tests also pass against the extended database schema.
