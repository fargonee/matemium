# Roadmap: Production Autonomous Agent Runtime

**Status:** Proposed migration plan

**Source of truth:** [`agentic_ai_goal.md`](agentic_ai_goal.md)

**Legacy baseline:** The XML/regex `ReActAgentRunner` and its tools are a prototype, not a completed production phase.

Checkboxes describe verified repository state. Do not mark an item complete merely because a mocked happy-path test exists.

## Phase 0 — Baseline and acceptance criteria

- [x] Inventory every autonomous entry point across server, desktop, sidecar, local runner, and MCP.
- [x] Document the legacy runner's known failure modes and compatibility requirements.
- [x] Define benchmark tasks and measurable release thresholds, including false-success rate.
- [x] Add runtime versioning so legacy and new runs are distinguishable in APIs and telemetry.
- [x] Decide durable checkpoint storage and retention policy.

**Exit gate:** Met by [`docs/agent/phase0-baseline.md`](docs/agent/phase0-baseline.md), the versioned files under `evals/agent/`, and ADR-001. Benchmark execution is deliberately deferred until the harness and pinned fixtures are implemented.

## Phase 1 — Typed domain model and state machine

- [x] Define `AgentRunState`, plan steps, acceptance criteria, changes, evidence, budgets, usage, and terminal outcomes.
- [x] Define legal lifecycle transitions and reject invalid transitions.
- [x] Implement checkpoint creation after each material event.
- [x] Implement resume with workspace-hash validation.
- [x] Add cancellation and terminal-reason contracts.
- [x] Test crash/restart, cancellation, invalid transitions, and concurrent user edits.

**Exit gate:** Met by the desktop-owned state/store in `desktop/src-tauri/src/agent_runs.rs`; see [`docs/agent/phase1-state-machine.md`](docs/agent/phase1-state-machine.md).

## Phase 2 — Structured model gateway

- [x] Define one internal model-response type for tool calls, plan revisions, progress, and finish proposals.
- [x] Implement provider-native JSON tool calling for supported cloud providers.
- [x] Implement a grammar/schema-constrained local-model adapter.
- [x] Support multiple non-conflicting tool calls and serialize writes.
- [x] Reject malformed responses through typed errors and bounded repair.
- [x] Preserve or summarize the full relevant conversation, not only the last user message.
- [x] Remove `<thought>`/`<tool_call>` XML as the production protocol.

**Exit gate:** Met by the recorded OpenAI-compatible family fixtures and local schema/grammar contract tests; see [`docs/agent/phase2-model-gateway.md`](docs/agent/phase2-model-gateway.md).

## Phase 3 — Tool platform and mutation journal

- [x] Standardize the typed tool-result envelope and stable error codes.
- [x] Adapt list/search/read tools with deterministic limits and truncation metadata.
- [x] Add precondition hashes to edits and record before/after hashes and changed ranges.
- [x] Enforce workspace and product file-boundary policy locally.
- [x] Separate syntax, lint, project check, compile, render, and visual-inspection tools.
- [x] Add snapshot/edit-journal rollback support.
- [x] Ensure exceptions cannot become unclassified success-like strings.
- [x] Add adversarial path, stale edit, ambiguous patch, and oversized-output tests.

**Exit gate:** Met by the desktop-owned tool platform and mutation journal; see [`docs/agent/phase3-tool-platform.md`](docs/agent/phase3-tool-platform.md).

## Phase 4 — Planner, executor, and policy engine

- [x] Generate explicit acceptance criteria and a short mutable plan.
- [x] Enforce inspect-before-edit in code rather than only in prompts.
- [x] Track active plan step and meaningful state changes.
- [x] Classify errors and select bounded recovery policies.
- [x] Detect repeated actions, unchanged observations, patch cycles, and rejected finish loops.
- [x] Enforce independent model-call, tool-call, token, cost, time, compile, and render budgets.
- [x] Implement `blocked` behavior for genuinely missing user input or capabilities.

**Exit gate:** Met by the LLM-independent fault-injection suite; see [`docs/agent/phase4-policy-engine.md`](docs/agent/phase4-policy-engine.md).

## Phase 5 — Verification and completion controller

- [x] Treat model completion as a finish proposal, never as terminal success.
- [x] Derive applicable completion gates from task type and acceptance criteria.
- [x] Require final inspection of changed files.
- [x] Require project checks and relevant tests.
- [x] Require render evidence for behavior-changing scene edits.
- [x] Require visual inspection for layout, animation, camera, geometry, and appearance tasks.
- [x] Produce a verification manifest used by the final response.
- [x] Prevent claims about checks that were not executed.

**Exit gate:** Met by deterministic false-success tests covering compile-successful semantic and visual failures; see [`docs/agent/phase5-verification-controller.md`](docs/agent/phase5-verification-controller.md).

## Phase 6 — Context engine and durable memory

- [x] Build prompts from structured run state and the active plan step.
- [x] Compact resolved observations into source-linked factual summaries.
- [x] Keep unresolved diagnostics and exact pending patch text losslessly available.
- [x] Reload raw evidence on demand without placing the full transcript in every request.
- [x] Measure context growth and fact retention on long tasks.

**Exit gate:** Met by deterministic 1,000-observation growth and retention tests; see [`docs/agent/phase6-context-memory.md`](docs/agent/phase6-context-memory.md).

## Phase 7 — Accounting, streaming, and user control

- [x] Record usage, latency, model, provider, request ID, and cost for every model call.
- [x] Record provider usage per call/run without charging BYO usage or deducting Matemium credits.
- [x] Define versioned SSE/IPC event schemas.
- [x] Stream concise rationales, actions, results, evidence, and budgets—not private chain-of-thought.
- [x] Add cancel, resume, approval, blocked-input, and run-history UI states.
- [x] Bound and redact streamed tool output.

**Exit gate:** Met by per-call reconciliation tests, versioned event tests, and the compiled typed terminal-state UI; see [`docs/agent/phase7-accounting-events-controls.md`](docs/agent/phase7-accounting-events-controls.md).

## Phase 8 — Optional scoped delegation

- [x] Define child-run capability, budget, and result contracts.
- [x] Prevent parent/child write races.
- [x] Return compressed, source-linked child evidence.
- [x] Keep final verification and completion authority in the parent.
- [ ] Benchmark delegation against the single-agent baseline before enabling it (Phase 9 execution; delegation remains disabled meanwhile).

**Exit gate:** The scoped delegation implementation is complete, but operational enablement remains gated on a passing Phase 9 model benchmark. The comparison contract and default-off behavior are tested; see [`docs/agent/phase8-scoped-delegation.md`](docs/agent/phase8-scoped-delegation.md) and `evals/agent/phase8-delegation-gate.json`.

## Phase 9 — End-to-end evaluation and rollout

- [ ] Run cloud and local models on the approved benchmark suite.
- [x] Measure task success, false success, destructive edits, recovery, calls, tokens, cost, and latency.
- [x] Add cancellation, resume, offline, provider-failure, and user-concurrent-edit scenarios.
- [ ] Run security and prompt-injection tests against workspace content and tool outputs (catalog and deterministic boundary tests exist; end-to-end profiles remain).
- [ ] Shadow the new runtime before allowing mutations for production users.
- [ ] Roll out behind a versioned feature flag with a legacy fallback (fail-closed controller is implemented; production integration remains).
- [ ] Publish operational dashboards and rollback criteria (machine-readable metrics and criteria exist; deployed dashboard remains).

**Exit gate:** Implementation is available in `matemium.agent.evaluation`, `matemium.agent.rollout`, and `evals/agent/`; operational evidence remains open. See [`docs/agent/phase9-evaluation-rollout.md`](docs/agent/phase9-evaluation-rollout.md). All thresholds must pass and rollback must be exercised before v2 mutations are enabled.

## Legacy components: disposition

| Component | Current role | Migration decision |
|---|---|---|
| `matemium/agent/react_runner.py` | XML/regex prototype loop | Replace with state-machine runtime; retain temporarily for compatibility tests |
| `matemium/agent/tools/*` | Prototype filesystem/compiler tools | Adapt behind typed envelopes and mutation journal |
| `shared/prompts/react-agent-system.txt` | Prompt-enforced ReAct behavior | Replace with role-specific prompts using structured protocol |
| `/chat/completions` autonomous branch | Non-streaming legacy entry point | Route through versioned runtime and preserve conversation context |
| `/chat/stream` | Legacy event stream | Migrate to versioned run events, cancellation, and resume |
| `LifecycleCoordinator` | Fixed pipeline | Reuse project-domain operations where helpful; do not make it the autonomy state machine |

## Definition of done

The migration is complete only when the new runtime satisfies the exit gate for every required phase, the end-to-end benchmark meets its thresholds, accounting reconciles, cancellation/resume work, and the system cannot report `completed` without a verification manifest.
