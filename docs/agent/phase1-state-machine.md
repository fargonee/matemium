# Agent Phase 1: Typed State and Durable Checkpoints

**Implemented:** 2026-07-18

**Control-plane owner:** Desktop/Tauri

Phase 1 implements the LLM-independent run foundation specified by [`agentic_ai_goal.md`](../../agentic_ai_goal.md) and ADR-001.

## Delivered contracts

The implementation lives in `desktop/src-tauri/src/agent_runs.rs` and provides:

- Typed `AgentRunState`, lifecycle status, plan steps, budgets, usage, evidence collections, timestamps, runtime identity, sequence, and terminal reason.
- A legal transition matrix for `received`, `understanding`, `planning`, `executing`, `verifying`, `recovering`, `completed`, `blocked`, `failed`, and `cancelled`.
- Required reasons for blocked, failed, and cancelled outcomes.
- Terminal-state protection: completed, failed, and cancelled runs cannot transition again.
- SQLite WAL storage at `<app data>/agent/agent-runs.sqlite3`.
- Transactional latest-state checkpoints and append-only, monotonically sequenced events.
- Optimistic sequence checks preventing stale/concurrent writers from overwriting newer checkpoints.
- Workspace fingerprints over `project.json`, `scenes.py`, and `assets.py`.
- Resume validation that persists a blocked reconciliation state if user files changed.
- Explicit cancellation persisted as a state transition and event.
- Database schema version validation.

The store is initialized and managed as part of Tauri `AppState`. `state-machine-v2` remains unavailable through the cloud selector until later phases connect planning, model calls, tools, and verification to this state layer.

## Database records

`agent_runs` stores the latest serialized state plus indexed identity, status, sequence, timestamps, and workspace fingerprint.

`agent_events` stores one bounded JSON event for each checkpoint sequence. The initial `run_created` event uses sequence zero. Both the state update and its event commit in one transaction.

Large artifacts remain outside SQLite as decided by ADR-001. `AppPaths::agent_run_artifacts_dir` provides their future per-run location.

## Concurrency and resume behavior

Every checkpoint supplies its expected sequence. If another writer has already advanced the run, the write fails with `AgentRunError::Conflict` and neither state nor event is partially committed.

On resume, the store recomputes the workspace fingerprint. A mismatch:

1. prevents execution from resuming;
2. persists `blocked` with a reconciliation reason when the run is nonterminal;
3. records a `workspace_conflict` event containing the expected and actual fingerprints;
4. returns `AgentRunError::WorkspaceChanged` to the caller.

## Verification

`desktop/src-tauri/tests/agent_runs_state.rs` covers:

- create → transition → checkpoint → process/store reopen → resume → complete;
- illegal transition rejection;
- required cancellation reason;
- optimistic concurrent checkpoint rejection;
- workspace changes made while a run is paused;
- cancellation checkpointing and terminal-state enforcement.

The tests do not invoke an LLM, satisfying the Phase 1 exit gate directly.
