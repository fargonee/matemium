# ADR-001: Local SQLite Agent Checkpoints and Append-Only Events

**Status:** Accepted for target implementation

**Date:** 2026-07-18

## Context

Agent runs need crash recovery, cancellation, auditability, usage reconciliation, and protection against stale workspace edits. The desktop owns local mutations and may operate offline. The cloud remains a thin model router and must not become the authority for local project state.

## Decision

Store authoritative run checkpoints in a desktop-managed SQLite database under the existing Matemium application-data root:

```text
<Matemium app data>/agent/agent-runs.sqlite3
```

Use two logical records:

- `agent_runs`: the latest validated `AgentRunState`, runtime version, project ID, status, sequence number, workspace fingerprint, timestamps, and terminal reason.
- `agent_events`: append-only, monotonically sequenced typed events containing bounded/redacted payloads and provider usage records.

Large raw artifacts—rendered media, compiler logs, snapshots, and file evidence—remain files under an app-managed per-run artifact directory. SQLite stores their relative paths, hashes, media types, sizes, and retention class.

Checkpoint writes occur transactionally after each model response, tool result, plan revision, usage record, and state transition. Resume verifies the current project/file hashes against the checkpoint before allowing mutations. A mismatch transitions to blocked reconciliation; it does not overwrite newer user work.

## Ownership and synchronization

- Desktop/Tauri owns the database, retention, and migrations.
- Sidecar operations return typed results to the desktop; the sidecar is not the durable run authority.
- Cloud services may store provider-usage telemetry keyed by run/call ID, but not the authoritative local plan or mutation state.
- Only one writer may hold a run lease. Read-only observers may consume events.

## Retention

- Completed, failed, blocked, and cancelled run metadata/events: 30 days by default.
- Large render/log/snapshot artifacts: 7 days by default unless attached to a saved project output.
- Active and resumable runs are exempt from age deletion.
- Users can delete run history immediately from settings.
- Secrets, API keys, private chain-of-thought, and unbounded prompt/tool payloads are never checkpointed.

Retention values must be configurable and surfaced to users before production rollout.

## Consequences

SQLite provides atomic local recovery and simple ordered event queries without requiring network access. The implementation must add schema migrations, corruption handling, artifact garbage collection, run leases, redaction tests, and explicit export/delete behavior.

## Alternatives rejected

- JSON file per run: weak atomicity and awkward event queries/migrations.
- Cloud-only storage: violates offline/local-authority boundaries and complicates privacy.
- Sidecar-owned database: couples durable control state to a process intended to remain replaceable and lazily loaded.
- In-memory state: cannot meet resume, audit, or reconciliation requirements.
