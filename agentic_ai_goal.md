# Specification: Matemium Autonomous Agent Runtime

**Status:** Target architecture; not yet fully implemented

**Last updated:** 2026-07-18

**Audience:** Desktop, sidecar, cloud-router, local-model, and agent-runtime contributors

This document is the normative specification for Matemium's autonomous authoring agent. The agent must be a bounded, observable, stateful task executor—not a prompt wrapped in an unstructured ReAct loop.

## 1. Product objective

Given one user objective, the agent should inspect the active Matemium workspace, form and revise a plan, make safe edits, validate the result using project-aware checks, recover from ordinary failures, and finish only when it has evidence that the objective is satisfied.

Autonomy means choosing the next useful action within an explicit policy and budget. It does not mean unrestricted filesystem or shell access.

For whole-project production, the runtime executes the phase and artifact contract in [`product-production-lifecycle.md`](product-production-lifecycle.md). Runtime task state and the user-facing production Roadmap are related but distinct: a single lifecycle phase may require multiple resumable agent runs, and a successful run must not falsely advance an unapproved or unverified production phase.

## 2. Required properties

The production runtime must provide:

1. Provider-native structured tool calling, with a schema-constrained compatibility adapter for local models.
2. Persistent run state: objective, plan, facts, actions, changes, diagnostics, verification evidence, budgets, and terminal outcome.
3. Explicit lifecycle states and legal transitions instead of treating “no tool call” as success.
4. Typed tool results and machine-readable errors.
5. Enforced completion gates backed by verification evidence.
6. Context compaction and structured working memory.
7. Loop, stall, timeout, cancellation, and budget controls.
8. Per-provider-call token and cost accounting.
9. Resumable runs and an auditable event stream.
10. End-to-end evaluation on realistic Matemium authoring and repair tasks.

## 3. Runtime model

The runtime is a state machine. Planner, executor, and verifier are logical responsibilities; they may share one model, use different prompts, or use different models.

```text
RECEIVED -> UNDERSTANDING -> PLANNING -> EXECUTING -> VERIFYING
                             ^             |             |
                             |             v             v
                             +---------- RECOVERING    COMPLETED
                                               |
                                    BLOCKED / FAILED / CANCELLED
```

Legal terminal outcomes are:

- `completed`: all applicable completion gates passed.
- `blocked`: user input or unavailable external capability is required.
- `failed`: the runtime exhausted recovery or budget with a concrete failure.
- `cancelled`: cancellation was requested and acknowledged.

An assistant message without tool calls is only a proposal to finish. The orchestrator must transition to `VERIFYING`; only the verifier may authorize `completed`.

## 4. Persistent run state

Every run must have a durable `AgentRunState` equivalent to:

```json
{
  "run_id": "uuid",
  "project_id": "string",
  "objective": "normalized user objective",
  "status": "planning",
  "plan": [{"id": "step-1", "text": "...", "status": "pending"}],
  "facts": [],
  "files_inspected": [],
  "changes": [],
  "diagnostics": [],
  "verification": [],
  "budgets": {"model_calls": 20, "tool_calls": 40, "tokens": 100000, "wall_seconds": 900},
  "usage": {"model_calls": 0, "tool_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0},
  "last_progress_at": "timestamp",
  "terminal_reason": null
}
```

State must be checkpointed after every model response, tool result, plan revision, and transition. Restarting the app must not silently convert a running task into a completed or lost task.

## 5. Structured model protocol

Cloud providers should receive native JSON-schema tool definitions and return native tool calls. The runtime must support multiple tool calls when the provider supports them, while executing conflicting writes serially.

Local models may use a grammar-constrained envelope, but the adapter must normalize it to the same internal types. Regex-extracted XML such as `<thought>` and `<tool_call>` is not a production protocol.

The model emits only:

- user-facing progress summaries;
- zero or more typed tool calls;
- a plan revision;
- a finish proposal containing claimed outcomes and requested verification.

Private chain-of-thought must not be required, stored, billed as a UI feature, or streamed. The UI receives concise action rationales and evidence instead.

## 6. Tool contract

Tools are allow-listed, workspace-scoped capabilities. Each tool returns a common envelope:

```json
{
  "status": "success | retryable_error | blocked | fatal_error",
  "code": "STABLE_MACHINE_CODE",
  "summary": "short human-readable result",
  "data": {},
  "evidence": [],
  "retry_hint": null,
  "truncated": false
}
```

Minimum authoring tool groups:

- Discovery: list workspace, search symbols/text, read bounded file slices, inspect project metadata.
- Editing: apply validated patches with precondition hashes; create only product-approved files.
- Validation: lint, import/check project, compile/render preview, inspect diagnostics.
- Visual verification: inspect rendered frames or derived scene metadata when visual correctness is part of the objective.
- Run control: request user input, report blockers, and checkpoint progress.

Tool requirements:

- Paths must resolve inside the active workspace and follow the product's file-boundary policy.
- Read and search outputs must have deterministic limits and report truncation.
- Mutations must record before/after hashes and changed ranges.
- Patch application must fail on missing or ambiguous preconditions.
- Tool exceptions must never be flattened into unclassified prose.
- Arbitrary shell access is excluded from the normal authoring agent.

## 7. Planning and execution policy

The agent must create a short, revisable plan for every mutation task. It may skip a formal plan only for a read-only response requiring at most one tool action.

Before editing, the runtime must have evidence that the relevant file or symbol was inspected. After an edit, the plan must identify the validation action. Failed observations should revise the plan rather than merely append more conversation.

The orchestrator owns policy enforcement. Prompt instructions alone are insufficient for requirements such as “inspect before edit” and “validate after edit.”

## 8. Completion gates

Completion is authorized only when all applicable gates pass:

1. The objective has explicit acceptance criteria, inferred conservatively when the user did not provide them.
2. Every changed file is recorded and its final content is available to verification.
3. Syntax/import/project checks pass.
4. Relevant tests or compiler checks pass.
5. A render succeeds when the task changes rendered behavior.
6. Visual evidence is inspected when layout, animation, camera, geometry, or appearance is material.
7. No unresolved fatal diagnostic remains.
8. The final response accurately reports checks that ran, checks that did not run, and remaining limitations.

A compile pass alone is necessary for many authoring tasks but is not proof of visual or semantic correctness.

## 9. Recovery, stalls, and budgets

Recovery policy must classify errors before retrying. Invalid arguments, stale patches, compiler diagnostics, provider failures, and unavailable dependencies require different actions.

The runtime must detect lack of progress using at least:

- repeated equivalent tool calls;
- repeated observations with no state change;
- repeated patch failures on the same target;
- plan steps cycling between the same statuses;
- model finish proposals rejected by the same gate.

Default policy should allow a small number of targeted recoveries per failure signature, then transition to `blocked` or `failed` with evidence. Budgets apply independently to model calls, tool calls, tokens, cost, elapsed time, compile retries, and render retries.

Cancellation must stop scheduling new actions, attempt to cancel active render/model work, checkpoint state, and emit `cancelled`.

## 10. Context and memory

The prompt context is assembled from structured state, not an ever-growing transcript. It should contain:

- objective and acceptance criteria;
- current plan and active step;
- relevant inspected excerpts;
- compact facts and symbol summaries;
- current changed-file summaries;
- latest diagnostics and verification evidence;
- remaining budgets.

Older observations are compacted into factual summaries with source references. Raw outputs remain in the audit log and can be reloaded. Summaries must not replace unresolved diagnostics or exact text needed for a pending patch.

Conversation history preceding the latest user message must be preserved or deliberately summarized; production routes must not silently reduce the objective to the last message.

## 11. Accounting and observability

Usage is recorded for every provider call, including input/output tokens, provider, model, latency, request ID, source mode (`byo_external` or `local`), and calculated/estimated provider cost when available. A multi-turn run must not be accounted as a single opaque call, and Matemium must not deduct credits.

The event stream uses versioned, typed events such as:

- `run_started`, `state_changed`, `plan_updated`;
- `action_started`, `action_completed`;
- `verification_started`, `verification_completed`;
- `usage_recorded`, `checkpoint_saved`;
- `input_required`, `run_completed`, `run_failed`, `run_cancelled`.

Events must not expose secrets, private reasoning, full credentials, or unbounded file/compiler output.

## 12. Security and user control

The runtime must preserve the desktop/sidecar trust boundary. The cloud routes model traffic but does not directly mutate local files or render projects. Local execution validates every proposed action.

Destructive, out-of-scope, or policy-sensitive actions require an explicit approval class. Changes should be recoverable through snapshots or an edit journal. Resuming a run must revalidate workspace hashes so stale plans cannot overwrite newer user edits.

## 13. Delegation

Sub-agents are optional, isolated child runs—not unrestricted recursive agents. Delegation is justified only for a bounded task whose compressed result reduces parent context, such as API research or independent visual review.

Each child receives a scoped objective, read/write capability set, and budget. It returns a typed result with evidence. Parent and child writes must not race; the parent remains responsible for final verification and completion.

## 14. Evaluation and release gates

Unit tests for parsers and mocked loops are insufficient. The evaluation suite must include realistic scenarios:

- create a valid scene from an ambiguous request;
- modify an existing scene without damaging unrelated sections;
- recover from syntax, import, LaTeX, and stale-patch errors;
- detect a compile-successful but visually incorrect result;
- handle user edits made during a paused run;
- compact long runs without losing unresolved facts;
- cancel and resume;
- stop repeated ineffective actions;
- account correctly for every model call;
- behave consistently across cloud and supported local models.

Release requires measured thresholds for task success, false-success rate, destructive-edit rate, mean model/tool calls, cost, cancellation latency, and recovery success. False completion is a critical failure.

## 15. Migration constraints

Existing filesystem and compiler helpers may be adapted behind typed contracts. The current `ReActAgentRunner`, XML parser, and prompt-only enforcement are prototype components and must not define the production architecture.

Migration should preserve the classic chat mode until the new runtime passes evaluation gates. The autonomous-mode toggle must identify the runtime version, and unfinished legacy runs must never be presented as verified successes.

## 16. Source-of-truth documents

- This file defines autonomous runtime behavior and guarantees.
- [`product-production-lifecycle.md`](product-production-lifecycle.md) defines the normative idea-to-product phases, production-path branches, and artifact dependencies.
- [`ai-agent-architecture.md`](ai-agent-architecture.md) defines product boundaries and tool placement.
- [`TODO-react-agentic-ai-transition.md`](TODO-react-agentic-ai-transition.md) tracks migration work and must not claim completion without the corresponding release gate.
- [`matemium/ipc/PROTOCOL.md`](matemium/ipc/PROTOCOL.md) defines sidecar transport contracts.
