use chrono::{Duration, Utc};
use matemium_desktop_lib::agent_policy::{
    AgentPolicyEngine, ErrorClass, MissingRequirementKind, PolicyViolation, ProposedAction,
    RecoveryDecision,
};
use matemium_desktop_lib::agent_runs::{AgentRunState, RunStatus};
use matemium_desktop_lib::agent_tools::{ToolResult, ToolStatus};
use serde_json::json;

fn executing_state() -> AgentRunState {
    let mut state = AgentRunState::new("project-1", "Fix the scene layout and labels").unwrap();
    state.transition(RunStatus::Understanding, None).unwrap();
    state.transition(RunStatus::Planning, None).unwrap();
    AgentPolicyEngine::initialize_plan(&mut state, Vec::new(), true).unwrap();
    state.transition(RunStatus::Executing, None).unwrap();
    state
}

fn action(name: &str, target: Option<&str>) -> ProposedAction {
    ProposedAction {
        tool_name: name.into(),
        arguments: json!({"path": target}),
        target_file: target.map(str::to_string),
    }
}

fn result(status: ToolStatus, code: &str, data: serde_json::Value) -> ToolResult {
    ToolResult {
        status,
        code: code.into(),
        summary: code.into(),
        data,
        evidence: Vec::new(),
        retry_hint: None,
        truncated: false,
    }
}

#[test]
fn generates_conservative_criteria_and_short_mutable_plan() {
    let state = executing_state();
    assert!(state
        .acceptance_criteria
        .iter()
        .any(|item| item.contains("visual evidence")));
    assert_eq!(state.plan.len(), 3);
    assert_eq!(state.policy.active_plan_step_id.as_deref(), Some("step-1"));

    let mut state = state;
    AgentPolicyEngine::advance_plan(&mut state).unwrap();
    assert_eq!(state.policy.active_plan_step_id.as_deref(), Some("step-2"));
}

#[test]
fn inspect_before_edit_is_enforced_by_policy() {
    let mut state = executing_state();
    let edit = action("apply_patch", Some("scenes.py"));
    assert!(matches!(
        AgentPolicyEngine::before_action(&mut state, &edit),
        Err(PolicyViolation::InspectBeforeEdit(path)) if path == "scenes.py"
    ));

    let read = action("read_file_slice", Some("scenes.py"));
    AgentPolicyEngine::before_action(&mut state, &read).unwrap();
    AgentPolicyEngine::record_observation(
        &mut state,
        &read,
        &result(ToolStatus::Success, "OK", json!({"path": "scenes.py"})),
    )
    .unwrap();
    AgentPolicyEngine::before_action(&mut state, &edit).unwrap();
}

#[test]
fn errors_are_classified_into_targeted_recovery() {
    for (code, class, decision) in [
        (
            "STALE_PRECONDITION",
            ErrorClass::StaleWorkspace,
            RecoveryDecision::RetryWithFreshInspection,
        ),
        (
            "AMBIGUOUS_PATCH",
            ErrorClass::PatchMismatch,
            RecoveryDecision::RetryWithFreshInspection,
        ),
        (
            "COMPILE_FAILED",
            ErrorClass::Diagnostic,
            RecoveryDecision::RevisePlan,
        ),
        (
            "PROVIDER_TIMEOUT",
            ErrorClass::ProviderTransient,
            RecoveryDecision::RetryTransient,
        ),
        (
            "DEPENDENCY_UNAVAILABLE",
            ErrorClass::DependencyUnavailable,
            RecoveryDecision::BlockForCapability,
        ),
        (
            "PATH_OUTSIDE_POLICY",
            ErrorClass::PermissionDenied,
            RecoveryDecision::Fail,
        ),
    ] {
        let observation = result(ToolStatus::RetryableError, code, json!({}));
        assert_eq!(AgentPolicyEngine::classify_error(&observation), class);
        assert_eq!(AgentPolicyEngine::recovery_for(class), decision);
    }
}

#[test]
fn repeated_actions_and_observations_stop_deterministically() {
    let mut state = executing_state();
    let read = action("read_file_slice", Some("scenes.py"));
    for _ in 0..3 {
        AgentPolicyEngine::before_action(&mut state, &read).unwrap();
    }
    assert!(matches!(
        AgentPolicyEngine::before_action(&mut state, &read),
        Err(PolicyViolation::RepeatedAction(_))
    ));

    let mut state = executing_state();
    let unchanged = result(
        ToolStatus::RetryableError,
        "PATCH_NOT_FOUND",
        json!({"same": true}),
    );
    for _ in 0..3 {
        AgentPolicyEngine::record_observation(&mut state, &read, &unchanged).unwrap();
    }
    assert!(matches!(
        AgentPolicyEngine::record_observation(&mut state, &read, &unchanged),
        Err(PolicyViolation::RepeatedObservation(_))
    ));
}

#[test]
fn rejected_finish_gate_loop_is_stopped() {
    let mut state = executing_state();
    for _ in 0..3 {
        AgentPolicyEngine::reject_finish(&mut state, "missing-render").unwrap();
    }
    assert!(matches!(
        AgentPolicyEngine::reject_finish(&mut state, "missing-render"),
        Err(PolicyViolation::RejectedFinishLoop(_))
    ));
}

#[test]
fn repeated_plan_revision_is_stopped() {
    let mut state = executing_state();
    state.transition(RunStatus::Recovering, None).unwrap();
    let steps = vec![
        "Inspect fresh diagnostics".into(),
        "Apply a corrected patch".into(),
    ];
    for _ in 0..3 {
        AgentPolicyEngine::revise_plan(&mut state, steps.clone(), "same diagnostic").unwrap();
    }
    assert!(matches!(
        AgentPolicyEngine::revise_plan(&mut state, steps, "same diagnostic"),
        Err(PolicyViolation::RepeatedPlanRevision(_))
    ));
}

#[test]
fn independent_budgets_are_enforced() {
    let mut model = executing_state();
    model.budgets.model_calls = 0;
    assert!(
        matches!(AgentPolicyEngine::record_model_usage(&mut model, 0, 0, 0.0), Err(PolicyViolation::BudgetExceeded(name)) if name == "model calls")
    );

    let mut tokens = executing_state();
    tokens.budgets.tokens = 5;
    assert!(
        matches!(AgentPolicyEngine::record_model_usage(&mut tokens, 4, 2, 0.0), Err(PolicyViolation::BudgetExceeded(name)) if name == "tokens")
    );

    let mut cost = executing_state();
    cost.budgets.cost = 0.01;
    assert!(
        matches!(AgentPolicyEngine::record_model_usage(&mut cost, 0, 0, 0.02), Err(PolicyViolation::BudgetExceeded(name)) if name == "cost")
    );

    let mut elapsed = executing_state();
    elapsed.budgets.wall_seconds = 1;
    elapsed.created_at = Utc::now() - Duration::seconds(2);
    assert!(
        matches!(AgentPolicyEngine::check_budgets(&elapsed), Err(PolicyViolation::BudgetExceeded(name)) if name == "elapsed time")
    );

    let mut tools = executing_state();
    tools.budgets.tool_calls = 0;
    assert!(
        matches!(AgentPolicyEngine::before_action(&mut tools, &action("read_file_slice", Some("scenes.py"))), Err(PolicyViolation::BudgetExceeded(name)) if name == "tool calls")
    );

    let mut compile = executing_state();
    compile.budgets.compile_retries = 0;
    assert!(
        matches!(AgentPolicyEngine::before_action(&mut compile, &action("compile_preview", None)), Err(PolicyViolation::BudgetExceeded(name)) if name == "compile retries")
    );

    let mut render = executing_state();
    render.budgets.render_retries = 0;
    assert!(
        matches!(AgentPolicyEngine::before_action(&mut render, &action("render", None)), Err(PolicyViolation::BudgetExceeded(name)) if name == "render retries")
    );
}

#[test]
fn blocked_state_requires_real_missing_input_or_capability_detail() {
    let mut state = executing_state();
    assert_eq!(
        AgentPolicyEngine::block_for_missing_requirement(
            &mut state,
            MissingRequirementKind::Capability,
            "TinyTeX is unavailable"
        ),
        Ok(())
    );
    assert_eq!(state.status, RunStatus::Blocked);
    assert!(state
        .terminal_reason
        .unwrap()
        .contains("Capability unavailable"));

    let mut invalid = executing_state();
    assert_eq!(
        AgentPolicyEngine::block_for_missing_requirement(
            &mut invalid,
            MissingRequirementKind::UserInput,
            "  "
        ),
        Err(PolicyViolation::InvalidBlockedReason)
    );
    assert_eq!(invalid.status, RunStatus::Executing);
}
