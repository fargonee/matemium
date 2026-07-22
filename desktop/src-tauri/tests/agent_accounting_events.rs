use std::fs;
use std::path::PathBuf;

use matemium_desktop_lib::agent_accounting::{AgentAccounting, AgentModelCall, BillingMode};
use matemium_desktop_lib::agent_events::{
    sanitize_payload, AgentEventKind, AgentStreamEvent, AGENT_EVENT_SCHEMA_VERSION,
};
use matemium_desktop_lib::agent_runs::{AgentRunState, AgentRunStore};
use serde_json::json;
use uuid::Uuid;

struct Sandbox {
    root: PathBuf,
    store: AgentRunStore,
    state: AgentRunState,
}

impl Sandbox {
    fn new() -> Self {
        let root =
            std::env::temp_dir().join(format!("matemium-agent-accounting-{}", Uuid::new_v4()));
        let workspace = root.join("workspace");
        fs::create_dir_all(&workspace).unwrap();
        fs::write(workspace.join("scenes.py"), "pass\n").unwrap();
        let store = AgentRunStore::open(root.join("agent/agent-runs.sqlite3")).unwrap();
        let state = store
            .create_run(
                AgentRunState::new("project-1", "Accounting test").unwrap(),
                &workspace,
            )
            .unwrap();
        Self { root, store, state }
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

#[test]
fn every_provider_call_reconciles_with_run_usage() {
    let sandbox = Sandbox::new();
    let accounting = AgentAccounting::new(sandbox.store.clone());
    let calls = [
        AgentModelCall::new(
            &sandbox.state.run_id,
            "openai",
            "gpt-4o-mini",
            "provider-request-1",
            BillingMode::ByoExternal,
            100,
            20,
            350,
            0.001,
            0,
        )
        .unwrap(),
        AgentModelCall::new(
            &sandbox.state.run_id,
            "groq",
            "llama",
            "provider-request-2",
            BillingMode::ByoExternal,
            50,
            10,
            200,
            0.0,
            0,
        )
        .unwrap(),
    ];
    for call in &calls {
        accounting.record(call).unwrap();
    }
    let mut state = sandbox.state.clone();
    state.usage.model_calls = 2;
    state.usage.input_tokens = 150;
    state.usage.output_tokens = 30;
    state.usage.cost = 0.001;
    let reconciliation = accounting.reconcile(&state).unwrap();
    assert!(reconciliation.matches_run_usage);
    assert_eq!(reconciliation.charged_credits, 0);
    assert_eq!(reconciliation.call_count, 2);
}

#[test]
fn byo_and_local_calls_cannot_charge_matemium_credits() {
    for mode in [BillingMode::ByoExternal, BillingMode::Local] {
        assert!(
            AgentModelCall::new("run", "provider", "model", "request", mode, 1, 1, 1, 0.0, 1,)
                .is_err()
        );
    }
}

#[test]
fn versioned_events_are_ordered_redacted_and_bounded() {
    let sandbox = Sandbox::new();
    let first = sandbox
        .store
        .append_stream_event(
            "action_completed",
            &sandbox.state.run_id,
            &json!({
                "rationale": "Inspect the file needed by the active step.",
                "api_key": "must-not-leak",
                "nested": {"Authorization": "Bearer secret"},
                "output": "x".repeat(40_000)
            }),
        )
        .unwrap();
    let second = sandbox
        .store
        .append_stream_event(
            "budget_updated",
            &sandbox.state.run_id,
            &json!({"tokens_remaining": 100}),
        )
        .unwrap();
    assert_eq!(first.schema_version, AGENT_EVENT_SCHEMA_VERSION);
    assert_eq!(second.sequence, first.sequence + 1);
    assert_eq!(first.payload["api_key"], "[REDACTED]");
    assert!(first.payload["output"]
        .as_str()
        .unwrap()
        .ends_with("…[truncated]"));

    let events = sandbox
        .store
        .list_stream_events(&sandbox.state.run_id, 0, 100)
        .unwrap();
    assert_eq!(events.len(), 2);
    assert_eq!(events[0].sequence, 1);

    let small = sanitize_payload(json!({"api_key": "secret", "nested": {"password": "pw"}}));
    assert_eq!(small["api_key"], "[REDACTED]");
    assert_eq!(small["nested"]["password"], "[REDACTED]");
}

#[test]
fn run_history_returns_latest_durable_states() {
    let sandbox = Sandbox::new();
    let history = sandbox.store.list_runs(20).unwrap();
    assert_eq!(history.len(), 1);
    assert_eq!(history[0].run_id, sandbox.state.run_id);
}

#[test]
fn typed_event_catalog_covers_progress_evidence_budgets_and_terminal_states() {
    for kind in [
        AgentEventKind::ActionStarted,
        AgentEventKind::ActionCompleted,
        AgentEventKind::VerificationCompleted,
        AgentEventKind::UsageRecorded,
        AgentEventKind::BudgetUpdated,
        AgentEventKind::RunCompleted,
        AgentEventKind::RunBlocked,
        AgentEventKind::RunFailed,
        AgentEventKind::RunCancelled,
    ] {
        let event = AgentStreamEvent::new_typed("run", 1, kind, json!({"summary": "bounded"}));
        assert_eq!(event.event_type, kind.as_str());
    }
}
