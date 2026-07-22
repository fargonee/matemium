//! Durable structured context and compaction for autonomous runtime v2.

use std::fmt;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use uuid::Uuid;

use crate::agent_runs::{
    AgentRunError, AgentRunState, AgentRunStore, PlanStep, RunBudgets, RunUsage,
};

const MAX_RAW_ITEM_BYTES: usize = 1024 * 1024;
const MAX_SUMMARY_BYTES: usize = 2048;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContextItemKind {
    Fact,
    ResolvedObservation,
    UnresolvedDiagnostic,
    PendingPatch,
    VerificationEvidence,
}

impl ContextItemKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Fact => "fact",
            Self::ResolvedObservation => "resolved_observation",
            Self::UnresolvedDiagnostic => "unresolved_diagnostic",
            Self::PendingPatch => "pending_patch",
            Self::VerificationEvidence => "verification_evidence",
        }
    }

    pub fn parse(value: &str) -> Result<Self, ContextError> {
        match value {
            "fact" => Ok(Self::Fact),
            "resolved_observation" => Ok(Self::ResolvedObservation),
            "unresolved_diagnostic" => Ok(Self::UnresolvedDiagnostic),
            "pending_patch" => Ok(Self::PendingPatch),
            "verification_evidence" => Ok(Self::VerificationEvidence),
            other => Err(ContextError::InvalidItem(format!(
                "unknown context kind '{other}'"
            ))),
        }
    }

    fn is_lossless(self) -> bool {
        matches!(self, Self::UnresolvedDiagnostic | Self::PendingPatch)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContextResolution {
    Resolved,
    Unresolved,
}

impl ContextResolution {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Resolved => "resolved",
            Self::Unresolved => "unresolved",
        }
    }

    pub fn parse(value: &str) -> Result<Self, ContextError> {
        match value {
            "resolved" => Ok(Self::Resolved),
            "unresolved" => Ok(Self::Unresolved),
            other => Err(ContextError::InvalidItem(format!(
                "unknown context resolution '{other}'"
            ))),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContextMemoryItem {
    pub item_id: String,
    pub run_id: String,
    pub sequence: u64,
    pub kind: ContextItemKind,
    pub resolution: ContextResolution,
    pub source: String,
    pub summary: String,
    pub raw: Value,
    pub pinned: bool,
    pub compacted: bool,
    pub created_at: DateTime<Utc>,
}

impl ContextMemoryItem {
    pub fn new(
        run_id: &str,
        sequence: u64,
        kind: ContextItemKind,
        resolution: ContextResolution,
        source: &str,
        summary: &str,
        raw: Value,
        pinned: bool,
    ) -> Result<Self, ContextError> {
        if run_id.trim().is_empty() || source.trim().is_empty() || summary.trim().is_empty() {
            return Err(ContextError::InvalidItem(
                "run, source, and summary are required".into(),
            ));
        }
        if summary.len() > MAX_SUMMARY_BYTES {
            return Err(ContextError::InvalidItem(
                "context summary exceeds 2048 bytes".into(),
            ));
        }
        let raw_size = serde_json::to_vec(&raw)
            .map_err(|error| ContextError::InvalidItem(error.to_string()))?
            .len();
        if raw_size > MAX_RAW_ITEM_BYTES {
            return Err(ContextError::InvalidItem(
                "raw context item exceeds 1 MiB".into(),
            ));
        }
        if kind.is_lossless() && resolution != ContextResolution::Unresolved {
            return Err(ContextError::InvalidItem(
                "diagnostics and pending patches must remain unresolved until explicitly replaced"
                    .into(),
            ));
        }
        Ok(Self {
            item_id: Uuid::new_v4().to_string(),
            run_id: run_id.into(),
            sequence,
            kind,
            resolution,
            source: source.into(),
            summary: summary.into(),
            raw,
            pinned,
            compacted: false,
            created_at: Utc::now(),
        })
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PromptMemory {
    pub item_id: String,
    pub kind: ContextItemKind,
    pub source: String,
    pub summary: String,
    pub raw: Option<Value>,
    pub pinned: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RemainingBudgets {
    pub model_calls: u32,
    pub tool_calls: u32,
    pub tokens: u64,
    pub cost: f64,
    pub wall_seconds: u64,
    pub compile_retries: u32,
    pub render_retries: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContextBundle {
    pub run_id: String,
    pub objective: String,
    pub acceptance_criteria: Vec<String>,
    pub plan: Vec<PlanStep>,
    pub active_plan_step_id: Option<String>,
    pub changed_files: Vec<Value>,
    pub latest_verification: Vec<Value>,
    pub mandatory_memory: Vec<PromptMemory>,
    pub pinned_facts: Vec<PromptMemory>,
    pub resolved_summaries: Vec<PromptMemory>,
    pub remaining_budgets: RemainingBudgets,
    pub omitted_resolved_items: usize,
    pub approximate_tokens: usize,
}

#[derive(Debug, Clone)]
pub struct ContextConfig {
    pub max_prompt_bytes: usize,
    pub max_changes: usize,
    pub max_verification: usize,
}

impl Default for ContextConfig {
    fn default() -> Self {
        Self {
            max_prompt_bytes: 32 * 1024,
            max_changes: 20,
            max_verification: 20,
        }
    }
}

#[derive(Debug)]
pub enum ContextError {
    InvalidItem(String),
    MandatoryContextTooLarge { required: usize, budget: usize },
    Store(AgentRunError),
    Serialization(String),
}

impl fmt::Display for ContextError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidItem(message) | Self::Serialization(message) => f.write_str(message),
            Self::MandatoryContextTooLarge { required, budget } => write!(
                f,
                "lossless mandatory context requires {required} bytes, budget is {budget}"
            ),
            Self::Store(error) => write!(f, "context store failed: {error}"),
        }
    }
}

impl std::error::Error for ContextError {}

impl From<AgentRunError> for ContextError {
    fn from(value: AgentRunError) -> Self {
        Self::Store(value)
    }
}

pub struct AgentContextEngine {
    store: AgentRunStore,
    config: ContextConfig,
}

impl AgentContextEngine {
    pub fn new(store: AgentRunStore, config: ContextConfig) -> Self {
        Self { store, config }
    }

    pub fn remember(&self, item: &ContextMemoryItem) -> Result<(), ContextError> {
        self.store.add_context_item(item)?;
        Ok(())
    }

    pub fn raw_item(&self, item_id: &str) -> Result<ContextMemoryItem, ContextError> {
        Ok(self.store.load_context_item(item_id)?)
    }

    pub fn mark_resolved(&self, item_id: &str) -> Result<(), ContextError> {
        self.store.resolve_context_item(item_id)?;
        Ok(())
    }

    pub fn compact_resolved(
        &self,
        run_id: &str,
        through_sequence: u64,
    ) -> Result<usize, ContextError> {
        Ok(self
            .store
            .compact_resolved_context(run_id, through_sequence)?)
    }

    pub fn build_bundle(&self, state: &AgentRunState) -> Result<ContextBundle, ContextError> {
        let items = self.store.list_context_items(&state.run_id)?;
        let mut mandatory = Vec::new();
        let mut pinned = Vec::new();
        let mut optional = Vec::new();
        for item in items {
            let prompt = PromptMemory {
                item_id: item.item_id,
                kind: item.kind,
                source: item.source,
                summary: item.summary,
                raw: if item.kind.is_lossless() && item.resolution == ContextResolution::Unresolved
                {
                    Some(item.raw)
                } else {
                    None
                },
                pinned: item.pinned,
            };
            if item.resolution == ContextResolution::Unresolved {
                mandatory.push(prompt);
            } else if item.pinned {
                pinned.push(prompt);
            } else {
                optional.push(prompt);
            }
        }
        let changes = tail(&state.changes, self.config.max_changes);
        let verification = tail(&state.verification, self.config.max_verification);
        let remaining = remaining_budgets(&state.budgets, &state.usage, state);
        let mut bundle = ContextBundle {
            run_id: state.run_id.clone(),
            objective: state.objective.clone(),
            acceptance_criteria: state.acceptance_criteria.clone(),
            plan: state.plan.clone(),
            active_plan_step_id: state.policy.active_plan_step_id.clone(),
            changed_files: changes,
            latest_verification: verification,
            mandatory_memory: mandatory,
            pinned_facts: pinned,
            resolved_summaries: Vec::new(),
            remaining_budgets: remaining,
            omitted_resolved_items: optional.len(),
            approximate_tokens: 0,
        };
        let base_size = encoded_size(&bundle)?;
        if base_size > self.config.max_prompt_bytes {
            return Err(ContextError::MandatoryContextTooLarge {
                required: base_size,
                budget: self.config.max_prompt_bytes,
            });
        }
        for item in optional {
            bundle.resolved_summaries.push(item);
            let size = encoded_size(&bundle)?;
            if size > self.config.max_prompt_bytes {
                bundle.resolved_summaries.pop();
                break;
            }
            bundle.omitted_resolved_items -= 1;
        }
        let final_size = encoded_size(&bundle)?;
        bundle.approximate_tokens = final_size.div_ceil(4);
        Ok(bundle)
    }
}

fn tail(values: &[Value], limit: usize) -> Vec<Value> {
    values
        .iter()
        .skip(values.len().saturating_sub(limit))
        .cloned()
        .collect()
}

fn encoded_size(value: &impl Serialize) -> Result<usize, ContextError> {
    serde_json::to_vec(value)
        .map(|bytes| bytes.len())
        .map_err(|error| ContextError::Serialization(error.to_string()))
}

fn remaining_budgets(
    budgets: &RunBudgets,
    usage: &RunUsage,
    state: &AgentRunState,
) -> RemainingBudgets {
    let elapsed = (Utc::now() - state.created_at).num_seconds().max(0) as u64;
    RemainingBudgets {
        model_calls: budgets.model_calls.saturating_sub(usage.model_calls),
        tool_calls: budgets.tool_calls.saturating_sub(usage.tool_calls),
        tokens: budgets
            .tokens
            .saturating_sub(usage.input_tokens.saturating_add(usage.output_tokens)),
        cost: (budgets.cost - usage.cost).max(0.0),
        wall_seconds: budgets.wall_seconds.saturating_sub(elapsed),
        compile_retries: budgets
            .compile_retries
            .saturating_sub(state.policy.compile_attempts),
        render_retries: budgets
            .render_retries
            .saturating_sub(state.policy.render_attempts),
    }
}
