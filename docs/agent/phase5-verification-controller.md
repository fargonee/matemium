# Agent Phase 5: Verification and Completion Controller

**Implemented:** 2026-07-18

**Completion authority:** Desktop/Tauri verifier

Phase 5 removes completion authority from the model. `finish_task` produces only a proposal. The run remains `verifying` until the controller derives and passes every applicable evidence gate.

## Evidence contract

`desktop/src-tauri/src/agent_verifier.rs` defines typed evidence for:

- final file inspection;
- syntax checks;
- project checks;
- relevant tests;
- preview renders;
- visual inspection;
- semantic/objective review.

Each record identifies whether it passed, its source, summary, optional file/hash, structured details, and timestamp.

Evidence also carries a typed producer. Sidecar checks are trusted for syntax, project, tests, and render evidence; desktop/verifier records are trusted for file, visual, and semantic evidence. Model-produced evidence is never trusted as proof of execution.

## Derived gates

Every task requires:

- semantic acceptance of the objective;
- no unresolved fatal diagnostics;
- evidence support for every success claim.

Every mutation task additionally requires:

- final inspection of every changed file at its recorded after-hash;
- passing syntax evidence;
- passing project-check evidence;
- a passing preview render.

Relevant-test evidence is added for test, refactor, computation, algorithm, and `assets.py` objectives. Visual-inspection evidence is added for visual, layout, animation, camera, geometry, overlap, appearance, and label objectives.

These rules are deliberately conservative. A compile pass is never treated as semantic or visual proof.

## Final-file integrity

The verifier derives the latest `after_sha256` for each changed path from the mutation records carried by run state. A final-file inspection passes only when its path and SHA-256 exactly match. Evidence from an earlier file version is rejected.

## Claims policy

The proposal summary and explicit claimed outcomes are scanned for test, syntax, project/compile, render/video, visual, and semantic claims. Each claim must map to passing executed evidence of the corresponding type.

The final verification manifest is constructed by the controller, not the model. It reports:

- objective and acceptance criteria;
- changed files;
- every gate and supporting sources;
- checks actually executed;
- applicable checks not run;
- requested checks that were not applicable or not executed;
- verification timestamp.

Therefore the user-facing response can be generated from the manifest without claiming checks that never ran.

## Rejection behavior

A rejected proposal returns:

- failed gates;
- checks not run;
- unsupported claims;
- a deterministic retry fingerprint.

The fingerprint is passed through the Phase 4 finish-loop detector. Repeated proposals rejected by the same evidence state terminate through policy rather than looping.

## Completion transition

Only `AgentVerificationController::authorize_completion` may:

1. serialize the verification manifest into durable run state;
2. persist the exact evidence set;
3. transition `verifying` to `completed`.

Missing or failing evidence leaves the run in `verifying`. Calling the verifier from any other lifecycle state is rejected.

## False-success tests

`desktop/src-tauri/tests/agent_verification_controller.rs` verifies that completion is rejected when:

- a model proposes finishing without evidence;
- compilation passes but semantic review fails;
- compilation passes but visual inspection detects a bad layout;
- final-file evidence uses a stale hash;
- the proposal claims tests passed without test evidence;
- a refactor omits relevant tests;
- an unresolved fatal diagnostic remains.
- a model attempts to supply its own verification evidence.

The positive scenario proves that complete evidence produces a manifest and is the only path that transitions the run to `completed`.
