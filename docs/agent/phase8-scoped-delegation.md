# Phase 8: Optional scoped delegation

Phase 8 adds a deliberately disabled-by-default delegation primitive. It does not turn every run into a multi-agent run. The parent may create a child only after an approved benchmark report shows a success-rate improvement on selected complex tasks without increasing false success or unsafe edits.

## Contracts

`agent_delegation.rs` defines the child capability, budget, task, evidence, and result contracts. A child receives an explicit tool allowlist and workspace-relative read/write scopes. Absolute paths, parent traversal, recursive delegation, missing acceptance criteria, and allocations exceeding the parent's remaining budget are rejected.

The parent retains ownership of its state and budgets. Child results contain only an outcome, a concise summary, source-linked evidence, and changed paths. They contain no terminal parent status or verification manifest.

## Write isolation

The coordinator reserves every active child's normalized write scopes. Equal, ancestor, and descendant scopes conflict; disjoint scopes can run concurrently. Read-only children do not reserve write scopes. Reported changed paths are checked against the original capability before a result is accepted. Releasing or cancelling a child releases its leases.

This is process-local lease enforcement. The existing mutation journal and precondition hashes remain the final protection against user edits or other processes.

## Evidence and completion

Child summaries are limited to 4 KiB and at most 16 evidence records. Every evidence record must identify a source and include a concise summary. The parent decides whether to reload the source and may use the evidence during its own execution, but only `AgentVerificationController` can authorize the parent's completion manifest.

## Enablement gate

The machine-readable gate is `evals/agent/phase8-delegation-gate.json`. `DelegationCoordinator::disabled()` is the production default. `from_benchmark` enables it only when:

- at least five selected complex cases were compared;
- delegated task success is strictly higher than the single-agent baseline;
- false-success rate does not increase; and
- unsafe-edit rate does not increase.

Phase 9 must execute and publish the real model comparison before production configuration supplies a passing benchmark. Unit tests validate the gate semantics; they are not a substitute for that benchmark.

## Exit gate

The implementation requirements are complete and mechanically tested. Operational enablement remains off pending the Phase 9 benchmark, as required by the Phase 8 exit gate.
