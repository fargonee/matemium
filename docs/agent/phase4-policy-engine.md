# Agent Phase 4: Planner, Executor Policy, and Recovery

**Implemented:** 2026-07-18

**Policy authority:** Desktop/Tauri

Phase 4 makes planning and execution rules enforceable in code. Model prompts may explain the rules, but they cannot bypass them.

## Planning contract

`desktop/src-tauri/src/agent_policy.rs` provides conservative acceptance criteria derived from the objective and a short plan of at most eight unique, non-empty steps.

Default mutation plans contain:

1. inspect relevant workspace context;
2. apply the smallest safe change;
3. validate the objective with required evidence.

Visual, scene, animation, layout, camera, geometry, and label objectives automatically include preview-render and visual-evidence acceptance criteria.

The active step is stored in durable `AgentRunState.policy`. Advancing a plan completes exactly one step and activates the next. Recovery may replace the plan with a reasoned revision. Repeated identical revisions are fingerprinted and stopped.

## Pre-action enforcement

Before any action, the policy engine checks:

- run status is `executing` or `recovering`;
- a plan step is active;
- independent run budgets remain;
- mutations identify a target file;
- that target was successfully inspected earlier;
- compile and render retry budgets remain;
- the equivalent action has not repeated beyond policy limits.

Tool-call usage and compile/render attempts are incremented only after authorization.

## Observation handling

Observations are fingerprinted from the canonical action, typed status, stable code, and canonical structured data. Equivalent unchanged observations are stopped after three repetitions.

Successful observations update structured run state:

- reads add inspected files;
- mutations add change records;
- validation, compile, render, and visual checks add verification evidence.

Failures add diagnostics and are classified before recovery.

## Error and recovery policy

| Error class | Examples | Default recovery |
|---|---|---|
| Invalid arguments | Invalid schema/arguments | Fresh inspection and corrected call |
| Stale workspace | Hash mismatch, rollback conflict | Fresh inspection |
| Patch mismatch | Missing or ambiguous exact block | Fresh inspection and narrower patch |
| Diagnostic | Syntax, lint, project, compile, render failure | Revise plan |
| Provider transient | Timeout, rate limit, unavailable | Bounded transient retry |
| Dependency unavailable | Missing engine or dependency | Block for capability |
| Permission/policy | Path escape, permission denial | Fail safely |
| Fatal | Typed fatal tool result | Fail |

Repeated patch failures are covered by action/observation fingerprints. Repeated rejected finish-gate signatures and repeated plan revisions have separate detectors.

## Independent budgets

The durable run budget now covers:

- model calls;
- tool calls;
- total tokens;
- monetary cost;
- elapsed wall time;
- compile retries;
- render retries.

Budget exhaustion returns a typed `PolicyViolation::BudgetExceeded`; it cannot become successful completion.

## Blocked-state policy

The policy engine exposes blocking only for two explicit requirement classes:

- missing user input;
- unavailable capability.

The detail must be non-empty, the current lifecycle transition must allow blocking, and the persisted reason identifies its class. Ordinary diagnostics, uncertainty, or repeated failure do not qualify as missing input.

## Durable policy state

`AgentRunState` now persists:

- active plan step;
- recent action fingerprints;
- recent observation fingerprints;
- rejected finish-gate fingerprints;
- plan-revision fingerprints;
- compile/render attempts;
- last meaningful sequence marker.

Histories are bounded to avoid unbounded checkpoint growth.

## Fault-injection verification

`desktop/src-tauri/tests/agent_policy_engine.rs` verifies:

- generated criteria and active plan transitions;
- inspect-before-edit rejection and authorization after inspection;
- error classification and targeted recovery;
- repeated action and unchanged-observation detection;
- rejected finish-loop detection;
- repeated plan-revision detection;
- model-call, tool-call, token, cost, elapsed-time, compile, and render budgets;
- valid capability blocking and rejection of empty blocked reasons.

These tests use no LLM and therefore demonstrate deterministic policy behavior.
