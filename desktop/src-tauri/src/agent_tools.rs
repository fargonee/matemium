//! Safe, bounded tools and mutation journal integration for agent runtime v2.

use std::fs;
use std::path::{Component, Path, PathBuf};

use chrono::Utc;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use uuid::Uuid;

use crate::agent_runs::{AgentRunStore, MutationRecord};

pub const CODE_OK: &str = "OK";
pub const CODE_INVALID_ARGUMENT: &str = "INVALID_ARGUMENT";
pub const CODE_PATH_OUTSIDE_POLICY: &str = "PATH_OUTSIDE_POLICY";
pub const CODE_FILE_NOT_FOUND: &str = "FILE_NOT_FOUND";
pub const CODE_STALE_PRECONDITION: &str = "STALE_PRECONDITION";
pub const CODE_PATCH_NOT_FOUND: &str = "PATCH_NOT_FOUND";
pub const CODE_AMBIGUOUS_PATCH: &str = "AMBIGUOUS_PATCH";
pub const CODE_OUTPUT_TRUNCATED: &str = "OUTPUT_TRUNCATED";
pub const CODE_MUTATION_FAILED: &str = "MUTATION_FAILED";
pub const CODE_ROLLBACK_CONFLICT: &str = "ROLLBACK_CONFLICT";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ToolStatus {
    Success,
    RetryableError,
    Blocked,
    FatalError,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ToolEvidence {
    pub kind: String,
    pub path: Option<String>,
    pub sha256: Option<String>,
    pub start_line: Option<u64>,
    pub end_line: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub status: ToolStatus,
    pub code: String,
    pub summary: String,
    pub data: Value,
    pub evidence: Vec<ToolEvidence>,
    pub retry_hint: Option<String>,
    pub truncated: bool,
}

impl ToolResult {
    fn success(summary: impl Into<String>, data: Value, evidence: Vec<ToolEvidence>) -> Self {
        Self {
            status: ToolStatus::Success,
            code: CODE_OK.into(),
            summary: summary.into(),
            data,
            evidence,
            retry_hint: None,
            truncated: false,
        }
    }

    fn error(
        status: ToolStatus,
        code: &str,
        summary: impl Into<String>,
        retry_hint: Option<String>,
    ) -> Self {
        Self {
            status,
            code: code.into(),
            summary: summary.into(),
            data: json!({}),
            evidence: Vec::new(),
            retry_hint,
            truncated: false,
        }
    }
}

#[derive(Debug, Clone)]
pub struct ToolLimits {
    pub max_list_entries: usize,
    pub max_read_lines: usize,
    pub max_read_bytes: usize,
    pub max_search_matches: usize,
    pub max_search_bytes: usize,
}

impl Default for ToolLimits {
    fn default() -> Self {
        Self {
            max_list_entries: 100,
            max_read_lines: 400,
            max_read_bytes: 64 * 1024,
            max_search_matches: 100,
            max_search_bytes: 128 * 1024,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ValidationToolKind {
    SyntaxCheck,
    Lint,
    ProjectCheck,
    CompilePreview,
    Render,
    VisualInspection,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationToolSpec {
    pub name: &'static str,
    pub kind: ValidationToolKind,
    pub executor: &'static str,
    pub mutates_workspace: bool,
    pub produces_evidence: &'static str,
}

pub fn validation_tool_specs() -> Vec<ValidationToolSpec> {
    use ValidationToolKind::*;
    vec![
        ValidationToolSpec {
            name: "syntax_check",
            kind: SyntaxCheck,
            executor: "sidecar",
            mutates_workspace: false,
            produces_evidence: "syntax_diagnostics",
        },
        ValidationToolSpec {
            name: "lint",
            kind: Lint,
            executor: "sidecar",
            mutates_workspace: false,
            produces_evidence: "lint_diagnostics",
        },
        ValidationToolSpec {
            name: "project_check",
            kind: ProjectCheck,
            executor: "sidecar",
            mutates_workspace: false,
            produces_evidence: "project_diagnostics",
        },
        ValidationToolSpec {
            name: "compile_preview",
            kind: CompilePreview,
            executor: "sidecar",
            mutates_workspace: false,
            produces_evidence: "compile_manifest",
        },
        ValidationToolSpec {
            name: "render",
            kind: Render,
            executor: "sidecar",
            mutates_workspace: false,
            produces_evidence: "render_manifest",
        },
        ValidationToolSpec {
            name: "visual_inspection",
            kind: VisualInspection,
            executor: "desktop",
            mutates_workspace: false,
            produces_evidence: "visual_inspection",
        },
    ]
}

#[derive(Debug, Clone)]
pub struct AgentToolPlatform {
    workspace: PathBuf,
    artifacts: PathBuf,
    run_id: String,
    store: AgentRunStore,
    limits: ToolLimits,
}

impl AgentToolPlatform {
    pub fn new(
        workspace: PathBuf,
        artifacts: PathBuf,
        run_id: String,
        store: AgentRunStore,
    ) -> Self {
        Self {
            workspace,
            artifacts,
            run_id,
            store,
            limits: ToolLimits::default(),
        }
    }

    pub fn with_limits(mut self, limits: ToolLimits) -> Self {
        self.limits = limits;
        self
    }

    pub fn list_workspace(&self) -> ToolResult {
        let mut entries = Vec::new();
        let mut names = vec![
            "project.json",
            "scenes.py",
            "helpers.py",
            "brief/passport.json",
            "brief/description.md",
            "brief/tapes/main.md",
            "brief/orchestration.md",
            "brief/roadmap.json",
            "brief/tts-narration.md",
            "brief/tts-narration-style.md",
            "brief/audio-description.md",
            "brief/custom-narration.md",
            "brief/transcript.md",
            "brief/timestamps.json",
        ]
        .into_iter()
        .map(str::to_string)
        .collect::<Vec<_>>();
        append_tape_content_files(&self.workspace, &mut names);
        for name in names {
            let path = self.workspace.join(&name);
            if path.is_file() {
                entries.push(
                    json!({"path": name, "bytes": path.metadata().map(|m| m.len()).unwrap_or(0)}),
                );
            }
        }
        let truncated = entries.len() > self.limits.max_list_entries;
        entries.truncate(self.limits.max_list_entries);
        let mut result = ToolResult::success(
            "Listed approved workspace files.",
            json!({"entries": entries}),
            Vec::new(),
        );
        result.truncated = truncated;
        if truncated {
            result.code = CODE_OUTPUT_TRUNCATED.into();
        }
        result
    }

    pub fn read_file_slice(
        &self,
        relative: &str,
        start_line: usize,
        end_line: usize,
    ) -> ToolResult {
        let path = match self.resolve_read_path(relative) {
            Ok(path) => path,
            Err(result) => return result,
        };
        if start_line == 0 || end_line < start_line {
            return ToolResult::error(
                ToolStatus::RetryableError,
                CODE_INVALID_ARGUMENT,
                "Line range must be 1-based and ordered.",
                Some("Use start_line >= 1 and end_line >= start_line.".into()),
            );
        }
        let bytes = match fs::read(&path) {
            Ok(bytes) => bytes,
            Err(error) => return io_error(CODE_FILE_NOT_FOUND, relative, error),
        };
        let hash = sha256(&bytes);
        let content = String::from_utf8_lossy(&bytes);
        let all: Vec<&str> = content.lines().collect();
        let requested_end = end_line.min(all.len());
        let capped_end = requested_end.min(
            start_line
                .saturating_add(self.limits.max_read_lines)
                .saturating_sub(1),
        );
        let mut selected = if start_line <= all.len() {
            all[start_line - 1..capped_end].join("\n")
        } else {
            String::new()
        };
        let mut truncated = requested_end > capped_end || bytes.len() > self.limits.max_read_bytes;
        if selected.len() > self.limits.max_read_bytes {
            truncate_utf8(&mut selected, self.limits.max_read_bytes);
            truncated = true;
        }
        let mut result = ToolResult::success(
            format!("Read {relative} lines {start_line}-{capped_end}."),
            json!({"path": relative, "start_line": start_line, "end_line": capped_end, "total_lines": all.len(), "content": selected}),
            vec![file_evidence(
                relative,
                &hash,
                start_line as u64,
                capped_end as u64,
            )],
        );
        result.truncated = truncated;
        if truncated {
            result.code = CODE_OUTPUT_TRUNCATED.into();
        }
        result
    }

    pub fn search_workspace(&self, query: &str) -> ToolResult {
        if query.is_empty() || query.len() > 512 {
            return ToolResult::error(
                ToolStatus::RetryableError,
                CODE_INVALID_ARGUMENT,
                "Search query must contain 1-512 bytes.",
                None,
            );
        }
        let mut matches = Vec::new();
        let mut searched_bytes = 0usize;
        let mut truncated = false;
        let mut names = vec![
            "project.json",
            "scenes.py",
            "helpers.py",
            "brief/passport.json",
            "brief/description.md",
            "brief/tapes/main.md",
            "brief/orchestration.md",
            "brief/roadmap.json",
            "brief/tts-narration.md",
            "brief/tts-narration-style.md",
            "brief/audio-description.md",
            "brief/custom-narration.md",
            "brief/transcript.md",
            "brief/timestamps.json",
        ]
        .into_iter()
        .map(str::to_string)
        .collect::<Vec<_>>();
        append_tape_content_files(&self.workspace, &mut names);
        for name in names {
            let path = self.workspace.join(&name);
            let bytes = match fs::read(&path) {
                Ok(bytes) => bytes,
                Err(_) => continue,
            };
            if searched_bytes.saturating_add(bytes.len()) > self.limits.max_search_bytes {
                truncated = true;
                break;
            }
            searched_bytes += bytes.len();
            for (index, line) in String::from_utf8_lossy(&bytes).lines().enumerate() {
                if line.contains(query) {
                    if matches.len() == self.limits.max_search_matches {
                        truncated = true;
                        break;
                    }
                    let mut text = line.to_string();
                    if text.len() > 512 {
                        truncate_utf8(&mut text, 512);
                        truncated = true;
                    }
                    matches.push(json!({"path": name.clone(), "line": index + 1, "text": text}));
                }
            }
            if truncated {
                break;
            }
        }
        let mut result = ToolResult::success(
            format!("Found {} match(es).", matches.len()),
            json!({"query": query, "matches": matches, "searched_bytes": searched_bytes}),
            Vec::new(),
        );
        result.truncated = truncated;
        if truncated {
            result.code = CODE_OUTPUT_TRUNCATED.into();
        }
        result
    }

    pub fn apply_patch(
        &self,
        relative: &str,
        expected_sha256: &str,
        search: &str,
        replace: &str,
    ) -> ToolResult {
        match self.apply_patch_inner(relative, expected_sha256, search, replace) {
            Ok(result) => result,
            Err(result) => result,
        }
    }

    fn apply_patch_inner(
        &self,
        relative: &str,
        expected_sha256: &str,
        search: &str,
        replace: &str,
    ) -> Result<ToolResult, ToolResult> {
        let path = self.resolve_mutation_path(relative)?;
        if search.is_empty() {
            return Err(ToolResult::error(
                ToolStatus::RetryableError,
                CODE_INVALID_ARGUMENT,
                "Patch search text cannot be empty.",
                None,
            ));
        }
        let before = fs::read(&path).map_err(|e| io_error(CODE_FILE_NOT_FOUND, relative, e))?;
        let before_hash = sha256(&before);
        if before_hash != expected_sha256 {
            return Err(ToolResult::error(
                ToolStatus::RetryableError,
                CODE_STALE_PRECONDITION,
                "File changed after it was inspected; patch was not applied.",
                Some("Read the file again and use its new SHA-256 precondition.".into()),
            ));
        }
        let source = String::from_utf8(before.clone()).map_err(|_| {
            ToolResult::error(
                ToolStatus::FatalError,
                CODE_INVALID_ARGUMENT,
                "Approved source file is not UTF-8.",
                None,
            )
        })?;
        if search.len() == source.len() {
            return Err(ToolResult::error(
                ToolStatus::Blocked,
                CODE_INVALID_ARGUMENT,
                "Full-file replacement is outside the patch tool policy.",
                Some("Use a smaller unique search block.".into()),
            ));
        }
        let occurrences = source.match_indices(search).collect::<Vec<_>>();
        if occurrences.is_empty() {
            return Err(ToolResult::error(
                ToolStatus::RetryableError,
                CODE_PATCH_NOT_FOUND,
                "Search text did not match the current file.",
                Some("Read a fresh slice and retry with exact text.".into()),
            ));
        }
        if occurrences.len() != 1 {
            return Err(ToolResult::error(
                ToolStatus::RetryableError,
                CODE_AMBIGUOUS_PATCH,
                "Search text matched more than once.",
                Some("Include more surrounding context to make the patch unique.".into()),
            ));
        }
        let byte_start = occurrences[0].0;
        let start_line = source[..byte_start].bytes().filter(|b| *b == b'\n').count() as u64 + 1;
        let end_line = start_line + search.bytes().filter(|b| *b == b'\n').count() as u64;
        let updated = source.replacen(search, replace, 1);
        let after_hash = sha256(updated.as_bytes());
        let mutation_id = Uuid::new_v4().to_string();
        let snapshot = self
            .artifacts
            .join("snapshots")
            .join(format!("{mutation_id}-{relative}"));
        if let Some(parent) = snapshot.parent() {
            fs::create_dir_all(parent).map_err(|e| io_error(CODE_MUTATION_FAILED, relative, e))?;
        }
        fs::write(&snapshot, &before).map_err(|e| io_error(CODE_MUTATION_FAILED, relative, e))?;
        atomic_write(&path, updated.as_bytes())
            .map_err(|e| io_error(CODE_MUTATION_FAILED, relative, e))?;
        let record = MutationRecord {
            mutation_id: mutation_id.clone(),
            run_id: self.run_id.clone(),
            file_path: relative.into(),
            before_hash: before_hash.clone(),
            after_hash: after_hash.clone(),
            snapshot_path: snapshot.to_string_lossy().into_owned(),
            changed_start_line: start_line,
            changed_end_line: end_line,
            rolled_back: false,
            created_at: Utc::now(),
        };
        if let Err(error) = self.store.record_mutation(&record) {
            let _ = atomic_write(&path, &before);
            let _ = fs::remove_file(&snapshot);
            return Err(ToolResult::error(
                ToolStatus::FatalError,
                CODE_MUTATION_FAILED,
                format!("Mutation journal rejected the edit; file was restored: {error}"),
                None,
            ));
        }
        Ok(ToolResult::success(
            format!("Applied one hash-guarded patch to {relative}."),
            json!({"mutation_id": mutation_id, "path": relative, "before_sha256": before_hash, "after_sha256": after_hash, "changed_start_line": start_line, "changed_end_line": end_line}),
            vec![file_evidence(relative, &after_hash, start_line, end_line)],
        ))
    }

    pub fn rollback(&self, mutation_id: &str) -> ToolResult {
        match self.rollback_inner(mutation_id) {
            Ok(result) | Err(result) => result,
        }
    }

    fn rollback_inner(&self, mutation_id: &str) -> Result<ToolResult, ToolResult> {
        let mutation = self.store.load_mutation(mutation_id).map_err(|e| {
            ToolResult::error(
                ToolStatus::RetryableError,
                CODE_INVALID_ARGUMENT,
                e.to_string(),
                None,
            )
        })?;
        if mutation.run_id != self.run_id || mutation.rolled_back {
            return Err(ToolResult::error(
                ToolStatus::Blocked,
                CODE_ROLLBACK_CONFLICT,
                "Mutation does not belong to this active run or was already rolled back.",
                None,
            ));
        }
        let path = self.resolve_mutation_path(&mutation.file_path)?;
        let current =
            fs::read(&path).map_err(|e| io_error(CODE_FILE_NOT_FOUND, &mutation.file_path, e))?;
        if sha256(&current) != mutation.after_hash {
            return Err(ToolResult::error(
                ToolStatus::Blocked,
                CODE_ROLLBACK_CONFLICT,
                "File changed after the mutation; automatic rollback would overwrite newer work.",
                None,
            ));
        }
        let snapshot = fs::read(&mutation.snapshot_path)
            .map_err(|e| io_error(CODE_MUTATION_FAILED, &mutation.file_path, e))?;
        if sha256(&snapshot) != mutation.before_hash {
            return Err(ToolResult::error(
                ToolStatus::FatalError,
                CODE_MUTATION_FAILED,
                "Snapshot hash verification failed.",
                None,
            ));
        }
        atomic_write(&path, &snapshot)
            .map_err(|e| io_error(CODE_MUTATION_FAILED, &mutation.file_path, e))?;
        self.store
            .mark_mutation_rolled_back(mutation_id)
            .map_err(|e| {
                ToolResult::error(
                    ToolStatus::FatalError,
                    CODE_MUTATION_FAILED,
                    e.to_string(),
                    None,
                )
            })?;
        Ok(ToolResult::success(
            format!("Rolled back mutation {mutation_id}."),
            json!({"mutation_id": mutation_id, "path": mutation.file_path, "restored_sha256": mutation.before_hash}),
            vec![file_evidence(
                &mutation.file_path,
                &mutation.before_hash,
                mutation.changed_start_line,
                mutation.changed_end_line,
            )],
        ))
    }

    fn resolve_read_path(&self, relative: &str) -> Result<PathBuf, ToolResult> {
        resolve_policy_path(
            &self.workspace,
            relative,
            &[
                "project.json",
                "scenes.py",
                "helpers.py",
                "brief/passport.json",
                "brief/description.md",
                "brief/tapes/main.md",
                "brief/orchestration.md",
                "brief/roadmap.json",
                "brief/tts-narration.md",
                "brief/tts-narration-style.md",
                "brief/audio-description.md",
                "brief/custom-narration.md",
                "brief/transcript.md",
                "brief/timestamps.json",
            ],
        )
    }

    fn resolve_mutation_path(&self, relative: &str) -> Result<PathBuf, ToolResult> {
        resolve_policy_path(
            &self.workspace,
            relative,
            &[
                "scenes.py",
                "helpers.py",
                "brief/passport.json",
                "brief/description.md",
                "brief/tapes/main.md",
                "brief/orchestration.md",
                "brief/roadmap.json",
                "brief/tts-narration.md",
                "brief/tts-narration-style.md",
                "brief/audio-description.md",
                "brief/custom-narration.md",
                "brief/transcript.md",
                "brief/timestamps.json",
            ],
        )
    }
}

fn resolve_policy_path(
    workspace: &Path,
    relative: &str,
    allowed: &[&str],
) -> Result<PathBuf, ToolResult> {
    let candidate = Path::new(relative);
    if candidate.is_absolute()
        || candidate
            .components()
            .any(|part| !matches!(part, Component::Normal(_)))
        || (!allowed.contains(&relative) && !is_tape_content_path(relative))
    {
        return Err(ToolResult::error(
            ToolStatus::Blocked,
            CODE_PATH_OUTSIDE_POLICY,
            format!("Path '{relative}' is outside the approved workspace file policy."),
            None,
        ));
    }
    let path = workspace.join(candidate);
    if !path.is_file() {
        return Err(ToolResult::error(
            ToolStatus::RetryableError,
            CODE_FILE_NOT_FOUND,
            format!("Approved file '{relative}' does not exist."),
            None,
        ));
    }
    let workspace_real = workspace
        .canonicalize()
        .map_err(|e| io_error(CODE_FILE_NOT_FOUND, "workspace", e))?;
    let path_real = path
        .canonicalize()
        .map_err(|e| io_error(CODE_FILE_NOT_FOUND, relative, e))?;
    if !path_real.starts_with(&workspace_real) {
        return Err(ToolResult::error(
            ToolStatus::Blocked,
            CODE_PATH_OUTSIDE_POLICY,
            "Resolved path escapes the workspace (including through a symlink).",
            None,
        ));
    }
    Ok(path_real)
}

fn is_tape_content_path(relative: &str) -> bool {
    let Some(filename) = relative.strip_prefix("brief/tapes/") else {
        return false;
    };
    !filename.is_empty()
        && !filename.contains('/')
        && filename.ends_with(".md")
        && filename[..filename.len() - 3]
            .chars()
            .all(|ch| ch.is_ascii_lowercase() || ch.is_ascii_digit() || ch == '-' || ch == '_')
}

fn append_tape_content_files(workspace: &Path, names: &mut Vec<String>) {
    let Ok(entries) = fs::read_dir(workspace.join("brief/tapes")) else {
        return;
    };
    let mut tapes = entries
        .filter_map(Result::ok)
        .filter_map(|entry| {
            let filename = entry.file_name().to_string_lossy().into_owned();
            let relative = format!("brief/tapes/{filename}");
            (entry.path().is_file() && is_tape_content_path(&relative)).then_some(relative)
        })
        .collect::<Vec<_>>();
    tapes.sort();
    for tape in tapes {
        if !names.contains(&tape) {
            names.push(tape);
        }
    }
}

fn atomic_write(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let parent = path.parent().ok_or_else(|| {
        std::io::Error::new(std::io::ErrorKind::InvalidInput, "file has no parent")
    })?;
    let temporary = parent.join(format!(".agent-write-{}.tmp", Uuid::new_v4()));
    fs::write(&temporary, bytes)?;
    if let Err(error) = fs::rename(&temporary, path) {
        let _ = fs::remove_file(&temporary);
        return Err(error);
    }
    Ok(())
}

fn truncate_utf8(value: &mut String, max_bytes: usize) {
    if value.len() <= max_bytes {
        return;
    }
    let mut boundary = max_bytes;
    while boundary > 0 && !value.is_char_boundary(boundary) {
        boundary -= 1;
    }
    value.truncate(boundary);
}

fn sha256(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn file_evidence(path: &str, hash: &str, start: u64, end: u64) -> ToolEvidence {
    ToolEvidence {
        kind: "file_slice".into(),
        path: Some(path.into()),
        sha256: Some(hash.into()),
        start_line: Some(start),
        end_line: Some(end),
    }
}

fn io_error(code: &str, path: &str, error: std::io::Error) -> ToolResult {
    ToolResult::error(
        ToolStatus::FatalError,
        code,
        format!("I/O failure for '{path}': {error}"),
        None,
    )
}
