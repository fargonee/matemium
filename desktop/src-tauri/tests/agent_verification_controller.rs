use matemium_desktop_lib::agent_runs::{AgentRunState, RunStatus};
use matemium_desktop_lib::agent_verifier::{
    AgentVerificationController, EvidenceKind, EvidenceProducer, FinishProposal, GateKind,
    VerificationDecision, VerificationEvidence,
};
use serde_json::json;

fn verifying_state(objective: &str) -> AgentRunState {
    let mut state = AgentRunState::new("project-1", objective).unwrap();
    state.transition(RunStatus::Understanding, None).unwrap();
    state.transition(RunStatus::Planning, None).unwrap();
    state.transition(RunStatus::Executing, None).unwrap();
    state.transition(RunStatus::Verifying, None).unwrap();
    state.acceptance_criteria = vec!["Requested heading is correct".into()];
    state.changes.push(json!({
        "path": "scenes.py",
        "before_sha256": "before",
        "after_sha256": "final-hash"
    }));
    state
}

fn proposal() -> FinishProposal {
    FinishProposal {
        summary: "Updated the requested scene heading.".into(),
        claimed_outcomes: vec!["The requested heading is present".into()],
        requested_verification: vec!["project_check".into(), "preview_render".into()],
    }
}

fn evidence(kind: EvidenceKind, passed: bool) -> VerificationEvidence {
    let mut item = VerificationEvidence::passed(
        kind,
        EvidenceProducer::TestHarness,
        "test-harness",
        &format!("{kind:?}"),
    );
    item.passed = passed;
    item
}

fn final_file(hash: &str) -> VerificationEvidence {
    let mut item = evidence(EvidenceKind::FinalFileInspection, true);
    item.path = Some("scenes.py".into());
    item.sha256 = Some(hash.into());
    item
}

fn complete_nonvisual_evidence() -> Vec<VerificationEvidence> {
    vec![
        final_file("final-hash"),
        evidence(EvidenceKind::SyntaxCheck, true),
        evidence(EvidenceKind::ProjectCheck, true),
        evidence(EvidenceKind::PreviewRender, true),
        evidence(EvidenceKind::SemanticReview, true),
    ]
}

#[test]
fn model_finish_proposal_without_evidence_cannot_complete() {
    let mut state = verifying_state("Change the introduction heading");
    let decision =
        AgentVerificationController::authorize_completion(&mut state, &proposal(), &[]).unwrap();
    assert!(matches!(decision, VerificationDecision::Rejected(_)));
    assert_eq!(state.status, RunStatus::Verifying);
    assert!(state.completion_manifest.is_none());
}

#[test]
fn all_required_evidence_authorizes_completion_and_manifest() {
    let mut state = verifying_state("Change the introduction heading");
    let decision = AgentVerificationController::authorize_completion(
        &mut state,
        &proposal(),
        &complete_nonvisual_evidence(),
    )
    .unwrap();
    let VerificationDecision::Authorized(manifest) = decision else {
        panic!("expected authorization")
    };
    assert_eq!(state.status, RunStatus::Completed);
    assert!(state.completion_manifest.is_some());
    assert_eq!(manifest.changed_files, vec!["scenes.py"]);
    assert!(manifest.gates.iter().all(|gate| gate.passed));
    assert!(manifest
        .executed_checks
        .iter()
        .any(|check| check.contains("ProjectCheck")));
}

#[test]
fn compile_success_does_not_hide_semantic_failure() {
    let mut state = verifying_state("Change the introduction heading");
    let mut observations = complete_nonvisual_evidence();
    observations.retain(|item| item.kind != EvidenceKind::SemanticReview);
    observations.push(evidence(EvidenceKind::SemanticReview, false));
    let decision =
        AgentVerificationController::authorize_completion(&mut state, &proposal(), &observations)
            .unwrap();
    let VerificationDecision::Rejected(rejection) = decision else {
        panic!("expected rejection")
    };
    assert!(rejection
        .failed_gates
        .iter()
        .any(|gate| gate.gate == GateKind::ObjectiveAccepted));
    assert_eq!(state.status, RunStatus::Verifying);
}

#[test]
fn compile_success_does_not_hide_visual_failure() {
    let mut state = verifying_state("Fix the overlapping labels in the scene layout");
    let mut observations = complete_nonvisual_evidence();
    observations.push(evidence(EvidenceKind::VisualInspection, false));
    let decision =
        AgentVerificationController::authorize_completion(&mut state, &proposal(), &observations)
            .unwrap();
    let VerificationDecision::Rejected(rejection) = decision else {
        panic!("expected rejection")
    };
    assert!(rejection
        .failed_gates
        .iter()
        .any(|gate| gate.gate == GateKind::VisualInspectionPassed));
}

#[test]
fn stale_final_file_inspection_is_rejected() {
    let mut state = verifying_state("Change the introduction heading");
    let mut observations = complete_nonvisual_evidence();
    observations[0] = final_file("stale-hash");
    let decision =
        AgentVerificationController::authorize_completion(&mut state, &proposal(), &observations)
            .unwrap();
    let VerificationDecision::Rejected(rejection) = decision else {
        panic!("expected rejection")
    };
    assert!(rejection
        .failed_gates
        .iter()
        .any(|gate| gate.gate == GateKind::FinalChangedFilesInspected));
}

#[test]
fn unsupported_test_claim_is_rejected_and_unrun_check_reported() {
    let mut state = verifying_state("Change the introduction heading");
    let mut claim = proposal();
    claim.claimed_outcomes.push("All tests passed".into());
    let decision = AgentVerificationController::authorize_completion(
        &mut state,
        &claim,
        &complete_nonvisual_evidence(),
    )
    .unwrap();
    let VerificationDecision::Rejected(rejection) = decision else {
        panic!("expected rejection")
    };
    assert_eq!(rejection.unsupported_claims, vec!["All tests passed"]);
    assert!(rejection
        .failed_gates
        .iter()
        .any(|gate| gate.gate == GateKind::ClaimsSupported));
}

#[test]
fn relevant_test_gate_is_derived_from_refactor_objective() {
    let mut state = verifying_state("Refactor the helpers.py computation and test it");
    let decision = AgentVerificationController::authorize_completion(
        &mut state,
        &proposal(),
        &complete_nonvisual_evidence(),
    )
    .unwrap();
    let VerificationDecision::Rejected(rejection) = decision else {
        panic!("expected rejection")
    };
    assert!(rejection.checks_not_run.contains(&"relevant_tests".into()));
    assert!(rejection
        .failed_gates
        .iter()
        .any(|gate| gate.gate == GateKind::RelevantTestsPassed));
}

#[test]
fn unresolved_fatal_diagnostic_blocks_completion() {
    let mut state = verifying_state("Change the introduction heading");
    state
        .diagnostics
        .push(json!({"fatal": true, "resolved": false, "message": "import failed"}));
    let decision = AgentVerificationController::authorize_completion(
        &mut state,
        &proposal(),
        &complete_nonvisual_evidence(),
    )
    .unwrap();
    let VerificationDecision::Rejected(rejection) = decision else {
        panic!("expected rejection")
    };
    assert!(rejection
        .failed_gates
        .iter()
        .any(|gate| gate.gate == GateKind::NoFatalDiagnostics));
}

#[test]
fn model_generated_evidence_is_not_trusted() {
    let mut state = verifying_state("Change the introduction heading");
    let mut observations = complete_nonvisual_evidence();
    let project = observations
        .iter_mut()
        .find(|item| item.kind == EvidenceKind::ProjectCheck)
        .unwrap();
    project.producer = EvidenceProducer::Model;
    let decision =
        AgentVerificationController::authorize_completion(&mut state, &proposal(), &observations)
            .unwrap();
    let VerificationDecision::Rejected(rejection) = decision else {
        panic!("expected rejection")
    };
    assert!(rejection
        .failed_gates
        .iter()
        .any(|gate| gate.gate == GateKind::ProjectCheckPassed));
}
