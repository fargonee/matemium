//! Parent-controlled, optional delegation for autonomous agent runtime v2.
//!
//! Children receive least-privilege contracts. They never authorize completion,
//! mutate parent state directly, or share overlapping write scopes.

use std::collections::{BTreeSet, HashMap};
use std::path::{Component, Path};

use serde::{Deserialize, Serialize};

use crate::agent_runs::{AgentRunState, RunBudgets, RunStatus};

pub const MAX_CHILDREN_PER_PARENT: usize = 4;
pub const MAX_CHILD_EVIDENCE: usize = 16;
pub const MAX_CHILD_SUMMARY_BYTES: usize = 4 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChildCapabilityContract {
    pub allowed_tools: BTreeSet<String>,
    pub readable_paths: BTreeSet<String>,
    pub writable_paths: BTreeSet<String>,
    #[serde(default)]
    pub may_delegate: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ChildRunContract {
    pub child_run_id: String,
    pub parent_run_id: String,
    pub objective: String,
    pub acceptance_criteria: Vec<String>,
    pub capability: ChildCapabilityContract,
    pub budgets: RunBudgets,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChildEvidence {
    pub source: String,
    pub summary: String,
    pub sha256: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ChildOutcome {
    Succeeded,
    Blocked,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChildRunResult {
    pub child_run_id: String,
    pub outcome: ChildOutcome,
    pub summary: String,
    pub evidence: Vec<ChildEvidence>,
    pub changed_paths: BTreeSet<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DelegationBenchmark {
    pub selected_complex_cases: u32,
    pub baseline_success_rate: f64,
    pub delegated_success_rate: f64,
    pub baseline_false_success_rate: f64,
    pub delegated_false_success_rate: f64,
    pub baseline_unsafe_edit_rate: f64,
    pub delegated_unsafe_edit_rate: f64,
}

impl DelegationBenchmark {
    pub fn enables_delegation(&self) -> bool {
        self.selected_complex_cases >= 5
            && self.delegated_success_rate > self.baseline_success_rate
            && self.delegated_false_success_rate <= self.baseline_false_success_rate
            && self.delegated_unsafe_edit_rate <= self.baseline_unsafe_edit_rate
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DelegationError {
    Disabled,
    InvalidParentStatus(RunStatus),
    InvalidContract(String),
    BudgetExceeded(String),
    WriteConflict { requested: String, held_by: String },
    TooManyChildren,
    UnknownChild(String),
    InvalidResult(String),
}

/// In-memory lease coordinator. Durable child state can be checkpointed by the
/// run store, while these leases serialize mutation within one active runtime.
pub struct DelegationCoordinator {
    enabled: bool,
    active: HashMap<String, ChildRunContract>,
}

impl DelegationCoordinator {
    pub fn disabled() -> Self {
        Self {
            enabled: false,
            active: HashMap::new(),
        }
    }

    pub fn from_benchmark(benchmark: &DelegationBenchmark) -> Self {
        Self {
            enabled: benchmark.enables_delegation(),
            active: HashMap::new(),
        }
    }

    pub fn is_enabled(&self) -> bool {
        self.enabled
    }

    /// The parent executor calls this before mutation so it cannot race a child lease.
    pub fn authorize_parent_write(
        &self,
        parent_run_id: &str,
        path: &str,
    ) -> Result<String, DelegationError> {
        let normalized = normalize_scope(path)?;
        for child in self
            .active
            .values()
            .filter(|child| child.parent_run_id == parent_run_id)
        {
            if child
                .capability
                .writable_paths
                .iter()
                .any(|scope| scopes_overlap(scope, &normalized))
            {
                return Err(DelegationError::WriteConflict {
                    requested: normalized,
                    held_by: child.child_run_id.clone(),
                });
            }
        }
        Ok(normalized)
    }

    /// Enforces capabilities at tool execution time, independently of prompts.
    pub fn authorize_child_tool(
        &self,
        child_run_id: &str,
        tool_name: &str,
        target_path: Option<&str>,
        mutates: bool,
    ) -> Result<Option<String>, DelegationError> {
        let child = self
            .active
            .get(child_run_id)
            .ok_or_else(|| DelegationError::UnknownChild(child_run_id.into()))?;
        if !child.capability.allowed_tools.contains(tool_name) {
            return Err(DelegationError::InvalidContract(format!(
                "tool {tool_name} is outside the child capability"
            )));
        }
        let Some(path) = target_path else {
            return Ok(None);
        };
        let normalized = normalize_scope(path)?;
        let scopes = if mutates {
            &child.capability.writable_paths
        } else {
            &child.capability.readable_paths
        };
        if !scopes
            .iter()
            .any(|scope| scope_contains(scope, &normalized))
        {
            return Err(DelegationError::InvalidContract(format!(
                "path {normalized} is outside the child {} capability",
                if mutates { "write" } else { "read" }
            )));
        }
        Ok(Some(normalized))
    }

    pub fn reserve(
        &mut self,
        parent: &AgentRunState,
        mut contract: ChildRunContract,
    ) -> Result<ChildRunContract, DelegationError> {
        if !self.enabled {
            return Err(DelegationError::Disabled);
        }
        if !matches!(
            parent.status,
            RunStatus::Planning | RunStatus::Executing | RunStatus::Recovering
        ) {
            return Err(DelegationError::InvalidParentStatus(parent.status));
        }
        if contract.parent_run_id != parent.run_id || contract.child_run_id.trim().is_empty() {
            return Err(DelegationError::InvalidContract(
                "child and parent identifiers must match the active parent".into(),
            ));
        }
        if contract.objective.trim().is_empty() || contract.acceptance_criteria.is_empty() {
            return Err(DelegationError::InvalidContract(
                "child objective and acceptance criteria are required".into(),
            ));
        }
        if contract.capability.may_delegate {
            return Err(DelegationError::InvalidContract(
                "recursive delegation is not permitted".into(),
            ));
        }
        if self.active.contains_key(&contract.child_run_id) {
            return Err(DelegationError::InvalidContract(
                "child run id is already active".into(),
            ));
        }
        let siblings = self
            .active
            .values()
            .filter(|item| item.parent_run_id == parent.run_id)
            .count();
        if siblings >= MAX_CHILDREN_PER_PARENT {
            return Err(DelegationError::TooManyChildren);
        }
        validate_budget(
            parent,
            &contract.budgets,
            self.active
                .values()
                .filter(|c| c.parent_run_id == parent.run_id),
        )?;

        contract.capability.readable_paths = normalize_scopes(&contract.capability.readable_paths)?;
        contract.capability.writable_paths = normalize_scopes(&contract.capability.writable_paths)?;
        if !contract.capability.writable_paths.is_empty()
            && !contract
                .capability
                .allowed_tools
                .iter()
                .any(|tool| matches!(tool.as_str(), "apply_patch" | "rollback"))
        {
            return Err(DelegationError::InvalidContract(
                "write scope requires an explicit mutation tool".into(),
            ));
        }
        for requested in &contract.capability.writable_paths {
            for active in self.active.values() {
                for held in &active.capability.writable_paths {
                    if scopes_overlap(requested, held) {
                        return Err(DelegationError::WriteConflict {
                            requested: requested.clone(),
                            held_by: active.child_run_id.clone(),
                        });
                    }
                }
            }
        }
        self.active
            .insert(contract.child_run_id.clone(), contract.clone());
        Ok(contract)
    }

    pub fn complete(&mut self, result: ChildRunResult) -> Result<ChildRunResult, DelegationError> {
        let contract = self
            .active
            .get(&result.child_run_id)
            .ok_or_else(|| DelegationError::UnknownChild(result.child_run_id.clone()))?;
        if result.summary.trim().is_empty() || result.summary.len() > MAX_CHILD_SUMMARY_BYTES {
            return Err(DelegationError::InvalidResult(
                "child summary must be concise and non-empty".into(),
            ));
        }
        if result.evidence.len() > MAX_CHILD_EVIDENCE
            || result
                .evidence
                .iter()
                .any(|item| item.source.trim().is_empty() || item.summary.trim().is_empty())
        {
            return Err(DelegationError::InvalidResult(
                "child evidence must be bounded and source-linked".into(),
            ));
        }
        let changed = normalize_scopes(&result.changed_paths)?;
        if changed.iter().any(|path| {
            !contract
                .capability
                .writable_paths
                .iter()
                .any(|scope| scope_contains(scope, path))
        }) {
            return Err(DelegationError::InvalidResult(
                "child reported a change outside its write capability".into(),
            ));
        }
        let mut normalized = result;
        normalized.changed_paths = changed;
        self.active.remove(&normalized.child_run_id);
        Ok(normalized)
    }

    pub fn cancel(&mut self, child_run_id: &str) -> Result<(), DelegationError> {
        self.active
            .remove(child_run_id)
            .map(|_| ())
            .ok_or_else(|| DelegationError::UnknownChild(child_run_id.into()))
    }
}

fn validate_budget<'a>(
    parent: &AgentRunState,
    requested: &RunBudgets,
    active: impl Iterator<Item = &'a ChildRunContract>,
) -> Result<(), DelegationError> {
    let mut calls = requested.model_calls;
    let mut tools = requested.tool_calls;
    let mut tokens = requested.tokens;
    let mut seconds = requested.wall_seconds;
    let mut cost = requested.cost;
    for child in active {
        calls = calls.saturating_add(child.budgets.model_calls);
        tools = tools.saturating_add(child.budgets.tool_calls);
        tokens = tokens.saturating_add(child.budgets.tokens);
        seconds = seconds.saturating_add(child.budgets.wall_seconds);
        cost += child.budgets.cost;
    }
    let remaining_tokens = parent
        .budgets
        .tokens
        .saturating_sub(parent.usage.input_tokens + parent.usage.output_tokens);
    if calls
        > parent
            .budgets
            .model_calls
            .saturating_sub(parent.usage.model_calls)
        || tools
            > parent
                .budgets
                .tool_calls
                .saturating_sub(parent.usage.tool_calls)
        || tokens > remaining_tokens
        || seconds > parent.budgets.wall_seconds
        || cost > (parent.budgets.cost - parent.usage.cost).max(0.0)
    {
        return Err(DelegationError::BudgetExceeded(
            "aggregate child allocation exceeds the parent's remaining budget".into(),
        ));
    }
    Ok(())
}

fn normalize_scopes(scopes: &BTreeSet<String>) -> Result<BTreeSet<String>, DelegationError> {
    scopes.iter().map(|scope| normalize_scope(scope)).collect()
}

fn normalize_scope(scope: &str) -> Result<String, DelegationError> {
    let path = Path::new(scope);
    if scope.trim().is_empty() || path.is_absolute() {
        return Err(DelegationError::InvalidContract(
            "capability paths must be non-empty workspace-relative paths".into(),
        ));
    }
    let mut parts = Vec::new();
    for component in path.components() {
        match component {
            Component::Normal(value) => parts.push(value.to_string_lossy().to_string()),
            Component::CurDir => {}
            Component::ParentDir | Component::RootDir | Component::Prefix(_) => {
                return Err(DelegationError::InvalidContract(
                    "capability path escapes the workspace".into(),
                ));
            }
        }
    }
    if parts.is_empty() {
        return Err(DelegationError::InvalidContract(
            "empty capability path".into(),
        ));
    }
    Ok(parts.join("/"))
}

fn scope_contains(scope: &str, path: &str) -> bool {
    path == scope
        || path
            .strip_prefix(scope)
            .is_some_and(|tail| tail.starts_with('/'))
}

fn scopes_overlap(left: &str, right: &str) -> bool {
    scope_contains(left, right) || scope_contains(right, left)
}
