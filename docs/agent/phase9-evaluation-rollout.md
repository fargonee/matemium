# Phase 9: End-to-end evaluation and rollout

Phase 9 provides the executable release gate and rollout policy for `state-machine-v2`. It deliberately separates implementation validation from real model evidence: generated reports can approve a profile only when every benchmark case has exactly one recorded result and every Phase 0 threshold passes.

## Evaluation workflow

Cloud and local runners write one JSON object per benchmark case to JSONL using the `BenchmarkResult` contract in `matemium.agent.evaluation`. Records include ground-truth success, claimed success, destructive edits, recovery, cancellation, resume, stall detection, provider-call reconciliation, calls, tokens, cost, and latency.

Run the aggregator from the repository root:

```bash
python evals/agent/run_phase9.py path/to/results.jsonl --output path/to/report.json
```

The command exits `0` only for an approved report and `2` for a failed or incomplete report. Missing cases, duplicate cases, empty profiles, and threshold violations fail closed. Separate profiles are required for each supported cloud model and local model configuration.

No synthetic result report is checked into the repository. Provider credentials, model assets, pinned benchmark workspaces, and human visual labels are required before the real run can be performed.

## Reliability and security scenarios

`phase9-scenarios.json` adds cancellation during a call, restart/resume, offline local execution, provider timeout, malformed structured output, and concurrent user edits. `phase9-security.json` defines workspace and tool-output prompt injection, path traversal, symlink escape, streamed-secret, and delegated capability-escalation cases.

These cases complement the deterministic policy, tool-boundary, event-redaction, verification, and delegation tests from Phases 1–8. Their end-to-end executions must still be recorded for every release profile.

## Rollout controller

`matemium.agent.rollout` defines four modes:

- `legacy`: execute `legacy-react-v1`;
- `shadow`: legacy remains authoritative and v2 is observation-only with mutations disabled;
- `canary`: stable cohort hashing selects approved v2 traffic;
- `target`: execute approved v2 for all traffic.

Evaluation approval is mandatory for canary and target modes. An operator rollback always selects legacy. The controller is ready for integration, but production must remain in legacy mode until the v2 orchestrator is connected to the server entry points and a report passes.

## Operations

`phase9-rollout-policy.json` is the dashboard and rollback contract. Automatic rollback is required for any destructive edit, false success above 1%, provider failures above 10%, cancellation p95 above three seconds, or accounting reconciliation below 99%.

The dashboard must segment all metrics by runtime version, provider, model, source mode (`byo_external` or `local`), release cohort, and application version. Reports and rollout changes are retained as release artifacts so rollback decisions are auditable.

## Current gate status

The evaluation, scenario, security, reporting, cohort-selection, and rollback-policy implementation is complete and unit tested. The Phase 9 exit gate remains open because real cloud/local benchmark execution, shadow traffic, dashboard publication, and a practiced rollback require deployed infrastructure and model access.
