# Agent Phase 7: Accounting, Events, and User Control

**Implemented:** 2026-07-18

Phase 7 makes autonomous runs observable and controllable without exposing secrets or private reasoning.

## Per-call accounting

Every structured provider call now returns and records:

- provider and model;
- provider request ID;
- source mode (`byo_external` or `local`);
- input and output tokens;
- latency in milliseconds;
- provider cost;
- calculated user/provider cost estimate when available;
- timestamp and run/call IDs.

`server/matemium_server/services/llm.py::complete_structured_agent` records each provider invocation for telemetry and reconciliation. It does not defer a multi-turn run into one opaque record. BYO calls return usage metadata but never deduct Matemium credits because Matemium no longer sells credits.

The desktop persists matching `agent_model_calls` rows. `AgentAccounting::reconcile` compares their call count, tokens, and estimated provider cost against durable `AgentRunState.usage`. BYO and local records are rejected if they claim Matemium credit charges.

## Versioned event stream

Progress events use schema version 1 and contain:

- event and run IDs;
- independent monotonically increasing stream sequence;
- typed event name;
- bounded, redacted payload;
- timestamp.

The typed catalog covers run/state/plan changes, action start/result, verification, usage, budgets, checkpoints, approval, required input, resume, and every terminal state.

Stream events use `agent_stream_events`, separate from state-checkpoint events, because multiple progress events may occur between checkpoints.

## Privacy and bounds

Payload sanitization:

- redacts API keys, authorization values, passwords, secrets, access tokens, and refresh tokens recursively;
- limits strings to 2 KiB;
- limits arrays to 50 items;
- replaces payloads exceeding 16 KiB with a bounded reload instruction.

Raw evidence is retrieved through Phase 6 by ID rather than streamed without limits.

Legacy `<thought>` callbacks are converted to a generic progress update. Their content is neither streamed nor shown as a UI feature.

## User-control commands

The Tauri control plane now exposes:

- `agent_run_list`
- `agent_run_get`
- `agent_run_events`
- `agent_run_cancel`
- `agent_run_resume`
- `agent_run_approve`
- `agent_run_provide_input`

Cancellation persists `cancelled`, emits a terminal event, and cancels active sidecar work. Resume revalidates workspace hashes through Phase 1. Approval requires a matching prior approval-request event. Input is accepted only for blocked runs, is bounded to 16 KiB, is persisted as pinned context, and returns the run to planning.

## Desktop UI contract

`desktop/app/src/components/AgentRunsPanel.tsx` provides:

- run history and selection;
- distinct completed, blocked, failed, cancelled, verifying, and recovering labels;
- cancellation and resume controls;
- blocked-input form;
- approve/deny controls for pending approvals;
- concise event ledger.

The TypeScript API exposes typed run states, events, and all control commands.

## Verification

Rust tests verify:

- per-call reconciliation;
- mixed BYO external and local accounting;
- rejection of any Matemium credit charges;
- ordered stream sequences;
- event schema versioning;
- recursive secret redaction and output bounds;
- typed progress, evidence, budget, and terminal event coverage;
- durable run history.

Python tests verify provider calls are recorded exactly once, BYO calls never deduct credits, events are bounded/redacted/versioned, and legacy private reasoning is removed.

The desktop TypeScript project compiles successfully with the run-history and control UI contracts.
