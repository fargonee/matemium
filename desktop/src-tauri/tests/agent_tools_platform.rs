use std::fs;
use std::path::PathBuf;

use matemium_desktop_lib::agent_runs::{AgentRunState, AgentRunStore};
use matemium_desktop_lib::agent_tools::{
    validation_tool_specs, AgentToolPlatform, ToolLimits, ToolStatus, CODE_AMBIGUOUS_PATCH,
    CODE_OUTPUT_TRUNCATED, CODE_PATH_OUTSIDE_POLICY, CODE_ROLLBACK_CONFLICT,
    CODE_STALE_PRECONDITION,
};
use sha2::{Digest, Sha256};
use uuid::Uuid;

struct Sandbox {
    root: PathBuf,
    run_id: String,
    store: AgentRunStore,
}

impl Sandbox {
    fn new(source: &str) -> Self {
        let root = std::env::temp_dir().join(format!("matemium-agent-tools-{}", Uuid::new_v4()));
        let workspace = root.join("workspace");
        fs::create_dir_all(&workspace).unwrap();
        fs::write(workspace.join("scenes.py"), source).unwrap();
        fs::write(workspace.join("helpers.py"), "VALUE = 1\n").unwrap();
        fs::write(workspace.join("project.json"), "{}").unwrap();
        let store = AgentRunStore::open(root.join("agent/agent-runs.sqlite3")).unwrap();
        let state = store
            .create_run(
                AgentRunState::new("project-1", "Tool test").unwrap(),
                &workspace,
            )
            .unwrap();
        Self {
            root,
            run_id: state.run_id,
            store,
        }
    }

    fn workspace(&self) -> PathBuf {
        self.root.join("workspace")
    }

    fn platform(&self) -> AgentToolPlatform {
        AgentToolPlatform::new(
            self.workspace(),
            self.root.join("agent/runs").join(&self.run_id),
            self.run_id.clone(),
            self.store.clone(),
        )
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

fn hash(value: &str) -> String {
    hex::encode(Sha256::digest(value.as_bytes()))
}

#[test]
fn discovery_is_bounded_and_reports_truncation() {
    let sandbox = Sandbox::new("one\ntarget a\ntarget b\nfour\n");
    let platform = sandbox.platform().with_limits(ToolLimits {
        max_list_entries: 2,
        max_read_lines: 2,
        max_read_bytes: 1024,
        max_search_matches: 1,
        max_search_bytes: 1024,
    });

    let listed = platform.list_workspace();
    assert!(listed.truncated);
    assert_eq!(listed.code, CODE_OUTPUT_TRUNCATED);

    let read = platform.read_file_slice("scenes.py", 1, 4);
    assert!(read.truncated);
    assert_eq!(read.data["end_line"], 2);
    assert!(!read.evidence[0].sha256.as_ref().unwrap().is_empty());

    let search = platform.search_workspace("target");
    assert!(search.truncated);
    assert_eq!(search.data["matches"].as_array().unwrap().len(), 1);
}

#[test]
fn path_traversal_absolute_paths_and_unapproved_files_are_blocked() {
    let sandbox = Sandbox::new("safe\n");
    for path in [
        "../scenes.py",
        "/etc/passwd",
        "notes.txt",
        "renders/video.mp4",
    ] {
        let result = sandbox.platform().read_file_slice(path, 1, 1);
        assert_eq!(result.status, ToolStatus::Blocked, "{path}");
        assert_eq!(result.code, CODE_PATH_OUTSIDE_POLICY);
    }
}

#[cfg(unix)]
#[test]
fn symlink_escape_is_blocked() {
    use std::os::unix::fs::symlink;
    let sandbox = Sandbox::new("safe\n");
    let outside = sandbox.root.join("outside.py");
    fs::write(&outside, "secret\n").unwrap();
    fs::remove_file(sandbox.workspace().join("helpers.py")).unwrap();
    symlink(&outside, sandbox.workspace().join("helpers.py")).unwrap();
    let result = sandbox.platform().read_file_slice("helpers.py", 1, 1);
    assert_eq!(result.code, CODE_PATH_OUTSIDE_POLICY);
}

#[test]
fn edit_requires_current_hash_and_unique_patch() {
    let source = "same\nmiddle\nsame\n";
    let sandbox = Sandbox::new(source);
    let platform = sandbox.platform();

    let stale = platform.apply_patch("scenes.py", &hash("older"), "middle", "changed");
    assert_eq!(stale.code, CODE_STALE_PRECONDITION);
    assert_eq!(
        fs::read_to_string(sandbox.workspace().join("scenes.py")).unwrap(),
        source
    );

    let ambiguous = platform.apply_patch("scenes.py", &hash(source), "same", "changed");
    assert_eq!(ambiguous.code, CODE_AMBIGUOUS_PATCH);
    assert_eq!(
        fs::read_to_string(sandbox.workspace().join("scenes.py")).unwrap(),
        source
    );
}

#[test]
fn mutation_records_hashes_ranges_snapshot_and_rolls_back() {
    let source = "first\nold heading\nlast\n";
    let sandbox = Sandbox::new(source);
    let platform = sandbox.platform();
    let result = platform.apply_patch("scenes.py", &hash(source), "old heading", "new heading");
    assert_eq!(result.status, ToolStatus::Success);
    assert_eq!(result.data["changed_start_line"], 2);
    let mutation_id = result.data["mutation_id"].as_str().unwrap();
    let record = sandbox.store.load_mutation(mutation_id).unwrap();
    assert_eq!(record.before_hash, hash(source));
    assert_eq!(record.after_hash, hash("first\nnew heading\nlast\n"));
    assert!(PathBuf::from(&record.snapshot_path).is_file());

    let rollback = platform.rollback(mutation_id);
    assert_eq!(rollback.status, ToolStatus::Success);
    assert_eq!(
        fs::read_to_string(sandbox.workspace().join("scenes.py")).unwrap(),
        source
    );
    assert!(
        sandbox
            .store
            .load_mutation(mutation_id)
            .unwrap()
            .rolled_back
    );
}

#[test]
fn rollback_refuses_to_overwrite_newer_user_edit() {
    let source = "old\nrest\n";
    let sandbox = Sandbox::new(source);
    let platform = sandbox.platform();
    let result = platform.apply_patch("scenes.py", &hash(source), "old", "new");
    let mutation_id = result.data["mutation_id"].as_str().unwrap();
    fs::write(sandbox.workspace().join("scenes.py"), "user edit\n").unwrap();
    let rollback = platform.rollback(mutation_id);
    assert_eq!(rollback.status, ToolStatus::Blocked);
    assert_eq!(rollback.code, CODE_ROLLBACK_CONFLICT);
    assert_eq!(
        fs::read_to_string(sandbox.workspace().join("scenes.py")).unwrap(),
        "user edit\n"
    );
}

#[test]
fn validation_capabilities_are_separate_and_non_mutating() {
    let specs = validation_tool_specs();
    assert_eq!(specs.len(), 6);
    let kinds = specs
        .iter()
        .map(|item| format!("{:?}", item.kind))
        .collect::<std::collections::HashSet<_>>();
    assert_eq!(kinds.len(), 6);
    assert_eq!(
        specs
            .iter()
            .map(|item| item.name)
            .collect::<std::collections::HashSet<_>>()
            .len(),
        6
    );
    assert!(specs.iter().all(|item| !item.mutates_workspace));
    assert!(specs.iter().all(|item| !item.produces_evidence.is_empty()));
}
