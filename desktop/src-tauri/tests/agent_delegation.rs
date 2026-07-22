use std::collections::BTreeSet;

use matemium_desktop_lib::agent_delegation::*;
use matemium_desktop_lib::agent_runs::{AgentRunState, RunBudgets, RunStatus};

fn set(values: &[&str]) -> BTreeSet<String> {
    values.iter().map(|value| value.to_string()).collect()
}

fn parent() -> AgentRunState {
    let mut state = AgentRunState::new("project", "Complex task").unwrap();
    state.transition(RunStatus::Understanding, None).unwrap();
    state.transition(RunStatus::Planning, None).unwrap();
    state.transition(RunStatus::Executing, None).unwrap();
    state
}

fn benchmark() -> DelegationBenchmark {
    DelegationBenchmark {
        selected_complex_cases: 8,
        baseline_success_rate: 0.60,
        delegated_success_rate: 0.75,
        baseline_false_success_rate: 0.01,
        delegated_false_success_rate: 0.01,
        baseline_unsafe_edit_rate: 0.0,
        delegated_unsafe_edit_rate: 0.0,
    }
}

fn contract(parent: &AgentRunState, id: &str, writes: &[&str]) -> ChildRunContract {
    ChildRunContract {
        child_run_id: id.into(),
        parent_run_id: parent.run_id.clone(),
        objective: "Implement isolated scene change".into(),
        acceptance_criteria: vec!["Return source-linked evidence".into()],
        capability: ChildCapabilityContract {
            allowed_tools: set(&["read_file_slice", "apply_patch", "project_check"]),
            readable_paths: set(&["scenes"]),
            writable_paths: set(writes),
            may_delegate: false,
        },
        budgets: RunBudgets {
            model_calls: 2,
            tool_calls: 5,
            tokens: 4_000,
            wall_seconds: 60,
            cost: 0.1,
            compile_retries: 1,
            render_retries: 0,
        },
    }
}

#[test]
fn delegation_is_disabled_without_a_passing_benchmark() {
    let parent = parent();
    assert!(matches!(
        DelegationCoordinator::disabled()
            .reserve(&parent, contract(&parent, "c1", &["scenes/a.py"])),
        Err(DelegationError::Disabled)
    ));
    let mut regression = benchmark();
    regression.delegated_false_success_rate = 0.02;
    assert!(!DelegationCoordinator::from_benchmark(&regression).is_enabled());
}

#[test]
fn overlapping_parent_child_scopes_are_exclusive() {
    let parent = parent();
    let mut coordinator = DelegationCoordinator::from_benchmark(&benchmark());
    coordinator
        .reserve(&parent, contract(&parent, "c1", &["scenes"]))
        .unwrap();
    let error = coordinator
        .reserve(&parent, contract(&parent, "c2", &["scenes/b.py"]))
        .unwrap_err();
    assert!(matches!(error, DelegationError::WriteConflict { held_by, .. } if held_by == "c1"));
    coordinator
        .reserve(&parent, contract(&parent, "c3", &["assets/icons"]))
        .unwrap();
    assert!(matches!(
        coordinator.authorize_parent_write(&parent.run_id, "scenes/a.py"),
        Err(DelegationError::WriteConflict { held_by, .. }) if held_by == "c1"
    ));
    assert!(coordinator
        .authorize_parent_write(&parent.run_id, "assets/audio.wav")
        .is_ok());
}

#[test]
fn child_tools_are_enforced_against_allowlist_and_path_scope() {
    let parent = parent();
    let mut coordinator = DelegationCoordinator::from_benchmark(&benchmark());
    coordinator
        .reserve(&parent, contract(&parent, "c1", &["scenes/a.py"]))
        .unwrap();
    assert!(coordinator
        .authorize_child_tool("c1", "apply_patch", Some("scenes/a.py"), true)
        .is_ok());
    assert!(matches!(
        coordinator.authorize_child_tool("c1", "shell", None, false),
        Err(DelegationError::InvalidContract(_))
    ));
    assert!(matches!(
        coordinator.authorize_child_tool("c1", "apply_patch", Some("scenes/b.py"), true),
        Err(DelegationError::InvalidContract(_))
    ));
}

#[test]
fn aggregate_child_budgets_cannot_exceed_parent_remainder() {
    let mut parent = parent();
    parent.budgets.model_calls = 3;
    let mut coordinator = DelegationCoordinator::from_benchmark(&benchmark());
    coordinator
        .reserve(&parent, contract(&parent, "c1", &["a.py"]))
        .unwrap();
    assert!(matches!(
        coordinator.reserve(&parent, contract(&parent, "c2", &["b.py"])),
        Err(DelegationError::BudgetExceeded(_))
    ));
}

#[test]
fn result_is_bounded_source_linked_and_within_write_scope() {
    let parent = parent();
    let mut coordinator = DelegationCoordinator::from_benchmark(&benchmark());
    coordinator
        .reserve(&parent, contract(&parent, "c1", &["scenes/a.py"]))
        .unwrap();
    let invalid = ChildRunResult {
        child_run_id: "c1".into(),
        outcome: ChildOutcome::Succeeded,
        summary: "done".into(),
        evidence: vec![],
        changed_paths: set(&["scenes/b.py"]),
    };
    assert!(matches!(
        coordinator.complete(invalid),
        Err(DelegationError::InvalidResult(_))
    ));
    let valid = ChildRunResult {
        child_run_id: "c1".into(),
        outcome: ChildOutcome::Succeeded,
        summary: "Implemented the isolated scene change.".into(),
        evidence: vec![ChildEvidence {
            source: "project_check:run-c1".into(),
            summary: "Project check passed.".into(),
            sha256: Some("abc".into()),
        }],
        changed_paths: set(&["scenes/a.py"]),
    };
    assert_eq!(
        coordinator.complete(valid).unwrap().outcome,
        ChildOutcome::Succeeded
    );
}

#[test]
fn child_contract_forbids_recursive_delegation_and_workspace_escape() {
    let parent = parent();
    let mut coordinator = DelegationCoordinator::from_benchmark(&benchmark());
    let mut recursive = contract(&parent, "c1", &["a.py"]);
    recursive.capability.may_delegate = true;
    assert!(matches!(
        coordinator.reserve(&parent, recursive),
        Err(DelegationError::InvalidContract(_))
    ));
    assert!(matches!(
        coordinator.reserve(&parent, contract(&parent, "c2", &["../outside"])),
        Err(DelegationError::InvalidContract(_))
    ));
}

#[test]
fn child_result_has_no_completion_authority() {
    let parent = parent();
    let mut coordinator = DelegationCoordinator::from_benchmark(&benchmark());
    coordinator
        .reserve(&parent, contract(&parent, "c1", &["a.py"]))
        .unwrap();
    coordinator
        .complete(ChildRunResult {
            child_run_id: "c1".into(),
            outcome: ChildOutcome::Succeeded,
            summary: "Child work finished; parent must verify.".into(),
            evidence: vec![ChildEvidence {
                source: "read:a.py".into(),
                summary: "Inspected final child output.".into(),
                sha256: None,
            }],
            changed_paths: set(&["a.py"]),
        })
        .unwrap();
    assert_eq!(parent.status, RunStatus::Executing);
    assert!(parent.completion_manifest.is_none());
}
