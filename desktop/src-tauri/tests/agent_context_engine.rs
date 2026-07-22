use std::fs;
use std::path::PathBuf;

use matemium_desktop_lib::agent_context::{
    AgentContextEngine, ContextConfig, ContextError, ContextItemKind, ContextMemoryItem,
    ContextResolution,
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
        let root = std::env::temp_dir().join(format!("matemium-agent-context-{}", Uuid::new_v4()));
        let workspace = root.join("workspace");
        fs::create_dir_all(&workspace).unwrap();
        fs::write(workspace.join("scenes.py"), "class Scene: pass\n").unwrap();
        fs::write(workspace.join("helpers.py"), "VALUE = 1\n").unwrap();
        fs::write(workspace.join("project.json"), "{}").unwrap();
        let store = AgentRunStore::open(root.join("agent/agent-runs.sqlite3")).unwrap();
        let state = store
            .create_run(
                AgentRunState::new(
                    "project-1",
                    "Refactor the scene while preserving the first constraint",
                )
                .unwrap(),
                &workspace,
            )
            .unwrap();
        Self { root, store, state }
    }

    fn engine(&self, bytes: usize) -> AgentContextEngine {
        AgentContextEngine::new(
            self.store.clone(),
            ContextConfig {
                max_prompt_bytes: bytes,
                max_changes: 10,
                max_verification: 10,
            },
        )
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

fn item(
    state: &AgentRunState,
    sequence: u64,
    kind: ContextItemKind,
    resolution: ContextResolution,
    summary: &str,
    raw: serde_json::Value,
    pinned: bool,
) -> ContextMemoryItem {
    ContextMemoryItem::new(
        &state.run_id,
        sequence,
        kind,
        resolution,
        &format!("event:{sequence}"),
        summary,
        raw,
        pinned,
    )
    .unwrap()
}

#[test]
fn long_run_is_compacted_but_first_pinned_constraint_and_lossless_items_survive() {
    let sandbox = Sandbox::new();
    let engine = sandbox.engine(8 * 1024);
    let first_constraint = item(
        &sandbox.state,
        1,
        ContextItemKind::Fact,
        ContextResolution::Resolved,
        "Never change the mathematical meaning of the first equation.",
        json!({"constraint": "preserve x^2 + 1 exactly"}),
        true,
    );
    engine.remember(&first_constraint).unwrap();

    let first_raw = item(
        &sandbox.state,
        2,
        ContextItemKind::ResolvedObservation,
        ContextResolution::Resolved,
        "Initial workspace inspection completed.",
        json!({"large_raw_output": "x".repeat(4000), "source": "scenes.py"}),
        false,
    );
    engine.remember(&first_raw).unwrap();
    for sequence in 3..503 {
        engine
            .remember(&item(
                &sandbox.state,
                sequence,
                ContextItemKind::ResolvedObservation,
                ContextResolution::Resolved,
                &format!("Resolved observation {sequence} from the workspace."),
                json!({"observation": sequence, "raw": "y".repeat(500)}),
                false,
            ))
            .unwrap();
    }
    let diagnostic = item(
        &sandbox.state,
        503,
        ContextItemKind::UnresolvedDiagnostic,
        ContextResolution::Unresolved,
        "The latest project check still has an import error.",
        json!({"stderr": "NameError: CanvasBuilder is not defined", "line": 12}),
        false,
    );
    let patch = item(
        &sandbox.state,
        504,
        ContextItemKind::PendingPatch,
        ContextResolution::Unresolved,
        "Exact patch awaiting safe application.",
        json!({"search": "old exact text", "replace": "new exact text"}),
        false,
    );
    engine.remember(&diagnostic).unwrap();
    engine.remember(&patch).unwrap();
    assert!(
        engine
            .compact_resolved(&sandbox.state.run_id, 1000)
            .unwrap()
            >= 502
    );

    let bundle = engine.build_bundle(&sandbox.state).unwrap();
    assert!(bundle.approximate_tokens <= 8 * 1024 / 4 + 8);
    assert!(bundle.omitted_resolved_items > 0);
    assert!(bundle
        .pinned_facts
        .iter()
        .any(|memory| memory.summary.contains("mathematical meaning")));
    assert!(bundle.mandatory_memory.iter().any(|memory| {
        memory
            .raw
            .as_ref()
            .is_some_and(|raw| raw["stderr"] == "NameError: CanvasBuilder is not defined")
    }));
    assert!(bundle.mandatory_memory.iter().any(|memory| {
        memory
            .raw
            .as_ref()
            .is_some_and(|raw| raw["search"] == "old exact text")
    }));

    let reloaded = engine.raw_item(&first_raw.item_id).unwrap();
    assert_eq!(
        reloaded.raw["large_raw_output"].as_str().unwrap().len(),
        4000
    );
    assert!(reloaded.compacted);
}

#[test]
fn resolved_diagnostic_leaves_prompt_but_raw_evidence_remains_reloadable() {
    let sandbox = Sandbox::new();
    let engine = sandbox.engine(4096);
    let diagnostic = item(
        &sandbox.state,
        1,
        ContextItemKind::UnresolvedDiagnostic,
        ContextResolution::Unresolved,
        "Syntax error remains.",
        json!({"traceback": "exact traceback"}),
        false,
    );
    engine.remember(&diagnostic).unwrap();
    assert_eq!(
        engine
            .build_bundle(&sandbox.state)
            .unwrap()
            .mandatory_memory
            .len(),
        1
    );
    engine.mark_resolved(&diagnostic.item_id).unwrap();
    engine.compact_resolved(&sandbox.state.run_id, 1).unwrap();
    let bundle = engine.build_bundle(&sandbox.state).unwrap();
    assert!(bundle.mandatory_memory.is_empty());
    assert!(bundle
        .resolved_summaries
        .iter()
        .any(|memory| memory.item_id == diagnostic.item_id && memory.raw.is_none()));
    assert_eq!(
        engine.raw_item(&diagnostic.item_id).unwrap().raw["traceback"],
        "exact traceback"
    );
}

#[test]
fn mandatory_lossless_context_is_never_silently_truncated() {
    let sandbox = Sandbox::new();
    let engine = sandbox.engine(512);
    engine
        .remember(&item(
            &sandbox.state,
            1,
            ContextItemKind::PendingPatch,
            ContextResolution::Unresolved,
            "Large exact patch.",
            json!({"search": "a".repeat(1000), "replace": "b".repeat(1000)}),
            false,
        ))
        .unwrap();
    assert!(matches!(
        engine.build_bundle(&sandbox.state),
        Err(ContextError::MandatoryContextTooLarge { .. })
    ));
}

#[test]
fn prompt_growth_stays_bounded_as_resolved_history_grows() {
    let sandbox = Sandbox::new();
    let engine = sandbox.engine(4096);
    for sequence in 1..=20 {
        engine
            .remember(&item(
                &sandbox.state,
                sequence,
                ContextItemKind::ResolvedObservation,
                ContextResolution::Resolved,
                &format!("Observation {sequence}"),
                json!({"raw": "z".repeat(200)}),
                false,
            ))
            .unwrap();
    }
    let early = engine
        .build_bundle(&sandbox.state)
        .unwrap()
        .approximate_tokens;
    for sequence in 21..=1000 {
        engine
            .remember(&item(
                &sandbox.state,
                sequence,
                ContextItemKind::ResolvedObservation,
                ContextResolution::Resolved,
                &format!("Observation {sequence}"),
                json!({"raw": "z".repeat(200)}),
                false,
            ))
            .unwrap();
    }
    let late_bundle = engine.build_bundle(&sandbox.state).unwrap();
    assert!(late_bundle.approximate_tokens <= 4096 / 4 + 8);
    assert!(late_bundle.approximate_tokens <= early + 256);
    assert!(late_bundle.omitted_resolved_items > 900);
}
