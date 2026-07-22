use std::fs;
use std::path::PathBuf;

use matemium_desktop_lib::agent_runs::{
    AgentRunError, AgentRunState, AgentRunStore, RunStatus, TARGET_STATE_MACHINE_RUNTIME,
};
use serde_json::json;
use uuid::Uuid;

struct Sandbox {
    root: PathBuf,
}

impl Sandbox {
    fn new() -> Self {
        let root = std::env::temp_dir().join(format!("matemium-agent-state-{}", Uuid::new_v4()));
        fs::create_dir_all(root.join("workspace")).expect("create sandbox");
        fs::write(root.join("workspace/scenes.py"), "class Scene: pass\n").expect("fixture");
        Self { root }
    }

    fn workspace(&self) -> PathBuf {
        self.root.join("workspace")
    }
    fn store(&self) -> AgentRunStore {
        AgentRunStore::open(self.root.join("agent/agent-runs.sqlite3")).expect("open store")
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

#[test]
fn run_can_checkpoint_restart_and_complete_without_an_llm() {
    let sandbox = Sandbox::new();
    let store = sandbox.store();
    let state = AgentRunState::new("project-1", "Create a verified scene").expect("state");
    assert_eq!(state.runtime_version, TARGET_STATE_MACHINE_RUNTIME);
    let run_id = state.run_id.clone();
    store
        .create_run(state, &sandbox.workspace())
        .expect("create");

    store
        .transition(
            &run_id,
            RunStatus::Understanding,
            None,
            &sandbox.workspace(),
        )
        .expect("understanding");
    store
        .transition(&run_id, RunStatus::Planning, None, &sandbox.workspace())
        .expect("planning");
    store
        .transition(&run_id, RunStatus::Executing, None, &sandbox.workspace())
        .expect("executing");
    store
        .transition(&run_id, RunStatus::Verifying, None, &sandbox.workspace())
        .expect("verifying");

    // Reopen the SQLite store to simulate an app restart.
    drop(store);
    let reopened = sandbox.store();
    let resumed = reopened
        .resume(&run_id, &sandbox.workspace())
        .expect("resume");
    assert_eq!(resumed.status, RunStatus::Verifying);
    let completed = reopened
        .transition(&run_id, RunStatus::Completed, None, &sandbox.workspace())
        .expect("complete");
    assert_eq!(completed.status, RunStatus::Completed);
    assert_eq!(reopened.event_count(&run_id).expect("events"), 6);
}

#[test]
fn invalid_transition_and_missing_terminal_reason_are_rejected() {
    let sandbox = Sandbox::new();
    let store = sandbox.store();
    let state = store
        .create_run(
            AgentRunState::new("project-1", "Test transitions").unwrap(),
            &sandbox.workspace(),
        )
        .unwrap();

    assert!(matches!(
        store.transition(
            &state.run_id,
            RunStatus::Completed,
            None,
            &sandbox.workspace()
        ),
        Err(AgentRunError::InvalidTransition { .. })
    ));
    assert!(matches!(
        store.transition(
            &state.run_id,
            RunStatus::Cancelled,
            None,
            &sandbox.workspace()
        ),
        Err(AgentRunError::Validation(_))
    ));
}

#[test]
fn optimistic_sequence_prevents_concurrent_checkpoint_overwrite() {
    let sandbox = Sandbox::new();
    let store = sandbox.store();
    let original = store
        .create_run(
            AgentRunState::new("project-1", "Concurrent checkpoint").unwrap(),
            &sandbox.workspace(),
        )
        .unwrap();
    let stale = original.clone();

    let saved = store
        .checkpoint(
            original,
            0,
            &sandbox.workspace(),
            "plan_updated",
            json!({"steps": 1}),
        )
        .expect("first checkpoint");
    assert_eq!(saved.sequence, 1);

    assert!(matches!(
        store.checkpoint(
            stale,
            0,
            &sandbox.workspace(),
            "plan_updated",
            json!({"steps": 2})
        ),
        Err(AgentRunError::Conflict {
            expected: 0,
            actual: 1
        })
    ));
}

#[test]
fn resume_blocks_when_user_changed_workspace() {
    let sandbox = Sandbox::new();
    let store = sandbox.store();
    let state = store
        .create_run(
            AgentRunState::new("project-1", "Respect user edits").unwrap(),
            &sandbox.workspace(),
        )
        .unwrap();
    store
        .transition(
            &state.run_id,
            RunStatus::Understanding,
            None,
            &sandbox.workspace(),
        )
        .unwrap();
    fs::write(
        sandbox.workspace().join("scenes.py"),
        "# user changed this\n",
    )
    .unwrap();

    assert!(matches!(
        store.resume(&state.run_id, &sandbox.workspace()),
        Err(AgentRunError::WorkspaceChanged { .. })
    ));
    let blocked = store
        .load_run(&state.run_id)
        .expect("blocked state persisted");
    assert_eq!(blocked.status, RunStatus::Blocked);
    assert!(blocked.terminal_reason.unwrap().contains("reconciliation"));
}

#[test]
fn cancellation_is_checkpointed_and_terminal() {
    let sandbox = Sandbox::new();
    let store = sandbox.store();
    let state = store
        .create_run(
            AgentRunState::new("project-1", "Cancel safely").unwrap(),
            &sandbox.workspace(),
        )
        .unwrap();
    let cancelled = store
        .cancel(
            &state.run_id,
            "User requested cancellation",
            &sandbox.workspace(),
        )
        .unwrap();
    assert_eq!(cancelled.status, RunStatus::Cancelled);
    assert!(matches!(
        store.transition(
            &state.run_id,
            RunStatus::Understanding,
            None,
            &sandbox.workspace()
        ),
        Err(AgentRunError::InvalidTransition { .. })
    ));
}
