//! Planner/executor policy enforcement for autonomous agent runtime v2.

use std::collections::HashSet;

use chrono::Utc;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::agent_runs::{AgentRunError, AgentRunState, PlanStep, PlanStepStatus, RunStatus};
use crate::agent_tools::{ToolResult, ToolStatus};

const MAX_PLAN_STEPS: usize = 8;
const HISTORY_LIMIT: usize = 32;
const REPEAT_LIMIT: usize = 3;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ActionClass {
    Inspect,
    Mutate,
    Validate,
    Compile,
    Render,
    VisualInspect,
    Other,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProposedAction {
    pub tool_name: String,
    pub arguments: Value,
    pub target_file: Option<String>,
}

impl ProposedAction {
    pub fn class(&self) -> ActionClass {
        match self.tool_name.as_str() {
            "list_workspace" | "read_file_slice" | "search_workspace" => ActionClass::Inspect,
            "apply_patch" | "rollback" => ActionClass::Mutate,
            "syntax_check" | "lint" | "project_check" => ActionClass::Validate,
            "compile_preview" => ActionClass::Compile,
            "render" => ActionClass::Render,
            "visual_inspection" => ActionClass::VisualInspect,
            _ => ActionClass::Other,
        }
    }

    pub fn fingerprint(&self) -> String {
        fingerprint(&json!({"tool": self.tool_name, "arguments": canonical_json(&self.arguments)}))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ErrorClass {
    InvalidArguments,
    StaleWorkspace,
    PatchMismatch,
    Diagnostic,
    DependencyUnavailable,
    PermissionDenied,
    ProviderTransient,
    Fatal,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RecoveryDecision {
    RetryWithFreshInspection,
    RevisePlan,
    RetryTransient,
    BlockForCapability,
    Fail,
    Continue,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MissingRequirementKind {
    UserInput,
    Capability,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PolicyViolation {
    InvalidPlan(String),
    InspectBeforeEdit(String),
    NoActiveStep,
    BudgetExceeded(String),
    RepeatedAction(String),
    RepeatedObservation(String),
    RejectedFinishLoop(String),
    RepeatedPlanRevision(String),
    InvalidBlockedReason,
    InvalidRunStatus(RunStatus),
}

pub struct AgentPolicyEngine;

impl AgentPolicyEngine {
    pub fn acceptance_criteria(objective: &str) -> Vec<String> {
        let lower = objective.to_lowercase();
        let mut criteria = vec![
            "Requested behavior is present in the approved project files.".to_string(),
            "Syntax and project checks pass without unresolved fatal diagnostics.".to_string(),
            "Unrelated project content remains unchanged.".to_string(),
        ];
        if [
            "scene",
            "animation",
            "layout",
            "camera",
            "geometry",
            "visual",
            "label",
        ]
        .iter()
        .any(|needle| lower.contains(needle))
        {
            criteria.push(
                "A preview render succeeds and relevant visual evidence is inspected.".into(),
            );
        }
        criteria
    }

    pub fn initialize_plan(
        state: &mut AgentRunState,
        proposed_steps: Vec<String>,
        mutation_expected: bool,
    ) -> Result<(), PolicyViolation> {
        if state.status != RunStatus::Planning {
            return Err(PolicyViolation::InvalidRunStatus(state.status));
        }
        let steps = if proposed_steps.is_empty() {
            let mut generated = vec!["Inspect the relevant workspace context".to_string()];
            if mutation_expected {
                generated.push("Apply the smallest safe change".into());
            }
            generated.push("Validate the objective with required evidence".into());
            generated
        } else {
            proposed_steps
        };
        if steps.is_empty() || steps.len() > MAX_PLAN_STEPS {
            return Err(PolicyViolation::InvalidPlan(format!(
                "plan requires 1-{MAX_PLAN_STEPS} steps"
            )));
        }
        if steps.iter().any(|step| step.trim().is_empty()) {
            return Err(PolicyViolation::InvalidPlan(
                "plan contains an empty step".into(),
            ));
        }
        let mut unique = HashSet::new();
        if steps
            .iter()
            .any(|step| !unique.insert(step.trim().to_lowercase()))
        {
            return Err(PolicyViolation::InvalidPlan(
                "plan contains duplicate steps".into(),
            ));
        }
        if state.acceptance_criteria.is_empty() {
            state.acceptance_criteria = Self::acceptance_criteria(&state.objective);
        }
        state.plan = steps
            .into_iter()
            .enumerate()
            .map(|(index, text)| PlanStep {
                id: format!("step-{}", index + 1),
                text,
                status: if index == 0 {
                    PlanStepStatus::InProgress
                } else {
                    PlanStepStatus::Pending
                },
            })
            .collect();
        state.policy.active_plan_step_id = state.plan.first().map(|step| step.id.clone());
        state.policy.last_meaningful_sequence = state.sequence;
        Ok(())
    }

    pub fn advance_plan(state: &mut AgentRunState) -> Result<(), PolicyViolation> {
        let active = state
            .policy
            .active_plan_step_id
            .clone()
            .ok_or(PolicyViolation::NoActiveStep)?;
        let index = state
            .plan
            .iter()
            .position(|step| step.id == active)
            .ok_or(PolicyViolation::NoActiveStep)?;
        state.plan[index].status = PlanStepStatus::Completed;
        if let Some(next) = state.plan.get_mut(index + 1) {
            next.status = PlanStepStatus::InProgress;
            state.policy.active_plan_step_id = Some(next.id.clone());
        } else {
            state.policy.active_plan_step_id = None;
        }
        state.policy.last_meaningful_sequence = state.sequence;
        Ok(())
    }

    pub fn revise_plan(
        state: &mut AgentRunState,
        steps: Vec<String>,
        reason: &str,
    ) -> Result<(), PolicyViolation> {
        if !matches!(state.status, RunStatus::Planning | RunStatus::Recovering) {
            return Err(PolicyViolation::InvalidRunStatus(state.status));
        }
        if reason.trim().is_empty() || steps.is_empty() || steps.len() > MAX_PLAN_STEPS {
            return Err(PolicyViolation::InvalidPlan(
                "plan revision requires a reason and 1-8 steps".into(),
            ));
        }
        if steps.iter().any(|step| step.trim().is_empty()) {
            return Err(PolicyViolation::InvalidPlan(
                "plan contains an empty step".into(),
            ));
        }
        let mut unique = HashSet::new();
        if steps
            .iter()
            .any(|step| !unique.insert(step.trim().to_lowercase()))
        {
            return Err(PolicyViolation::InvalidPlan(
                "plan contains duplicate steps".into(),
            ));
        }
        let revision_fp = fingerprint(&json!({"steps": steps, "reason": reason.trim()}));
        if repeated(&state.policy.plan_revision_fingerprints, &revision_fp) >= REPEAT_LIMIT {
            return Err(PolicyViolation::RepeatedPlanRevision(revision_fp));
        }
        push_bounded(&mut state.policy.plan_revision_fingerprints, revision_fp);
        state.plan = steps
            .into_iter()
            .enumerate()
            .map(|(index, text)| PlanStep {
                id: format!("step-{}", index + 1),
                text,
                status: if index == 0 {
                    PlanStepStatus::InProgress
                } else {
                    PlanStepStatus::Pending
                },
            })
            .collect();
        state.policy.active_plan_step_id = state.plan.first().map(|step| step.id.clone());
        state.policy.last_meaningful_sequence = state.sequence;
        Ok(())
    }

    pub fn before_action(
        state: &mut AgentRunState,
        action: &ProposedAction,
    ) -> Result<(), PolicyViolation> {
        if state.status != RunStatus::Executing && state.status != RunStatus::Recovering {
            return Err(PolicyViolation::InvalidRunStatus(state.status));
        }
        if state.policy.active_plan_step_id.is_none() {
            return Err(PolicyViolation::NoActiveStep);
        }
        Self::check_budgets(state)?;
        if action.class() == ActionClass::Mutate {
            let target = action.target_file.as_deref().ok_or_else(|| {
                PolicyViolation::InspectBeforeEdit("mutation has no target file".into())
            })?;
            if !state.files_inspected.iter().any(|path| path == target) {
                return Err(PolicyViolation::InspectBeforeEdit(target.into()));
            }
        }
        match action.class() {
            ActionClass::Compile
                if state.policy.compile_attempts >= state.budgets.compile_retries =>
            {
                return Err(PolicyViolation::BudgetExceeded("compile retries".into()));
            }
            ActionClass::Render if state.policy.render_attempts >= state.budgets.render_retries => {
                return Err(PolicyViolation::BudgetExceeded("render retries".into()));
            }
            _ => {}
        }
        let action_fp = action.fingerprint();
        if repeated(&state.policy.action_fingerprints, &action_fp) >= REPEAT_LIMIT {
            return Err(PolicyViolation::RepeatedAction(action_fp));
        }
        push_bounded(&mut state.policy.action_fingerprints, action_fp);
        state.usage.tool_calls = state.usage.tool_calls.saturating_add(1);
        match action.class() {
            ActionClass::Compile => {
                state.policy.compile_attempts = state.policy.compile_attempts.saturating_add(1)
            }
            ActionClass::Render => {
                state.policy.render_attempts = state.policy.render_attempts.saturating_add(1)
            }
            _ => {}
        }
        Ok(())
    }

    pub fn record_observation(
        state: &mut AgentRunState,
        action: &ProposedAction,
        result: &ToolResult,
    ) -> Result<RecoveryDecision, PolicyViolation> {
        let observation_fp = fingerprint(&json!({
            "action": action.fingerprint(),
            "status": result.status,
            "code": result.code,
            "data": canonical_json(&result.data),
        }));
        if repeated(&state.policy.observation_fingerprints, &observation_fp) >= REPEAT_LIMIT {
            return Err(PolicyViolation::RepeatedObservation(observation_fp));
        }
        push_bounded(&mut state.policy.observation_fingerprints, observation_fp);

        if result.status == ToolStatus::Success {
            match action.class() {
                ActionClass::Inspect => {
                    if let Some(path) = result.data.get("path").and_then(Value::as_str) {
                        if !state.files_inspected.iter().any(|known| known == path) {
                            state.files_inspected.push(path.into());
                        }
                    }
                }
                ActionClass::Mutate => state.changes.push(result.data.clone()),
                ActionClass::Validate
                | ActionClass::Compile
                | ActionClass::Render
                | ActionClass::VisualInspect => state.verification.push(result.data.clone()),
                ActionClass::Other => {}
            }
            state.policy.last_meaningful_sequence = state.sequence;
            return Ok(RecoveryDecision::Continue);
        }
        state.diagnostics.push(
            json!({"tool": action.tool_name, "code": result.code, "summary": result.summary}),
        );
        Ok(Self::recovery_for(Self::classify_error(result)))
    }

    pub fn classify_error(result: &ToolResult) -> ErrorClass {
        match result.code.as_str() {
            "INVALID_ARGUMENT" => ErrorClass::InvalidArguments,
            "STALE_PRECONDITION" | "ROLLBACK_CONFLICT" => ErrorClass::StaleWorkspace,
            "PATCH_NOT_FOUND" | "AMBIGUOUS_PATCH" => ErrorClass::PatchMismatch,
            "SYNTAX_ERROR"
            | "LINT_ERROR"
            | "PROJECT_CHECK_FAILED"
            | "COMPILE_FAILED"
            | "RENDER_FAILED" => ErrorClass::Diagnostic,
            "DEPENDENCY_UNAVAILABLE" | "ENGINE_NOT_READY" => ErrorClass::DependencyUnavailable,
            "PATH_OUTSIDE_POLICY" | "PERMISSION_DENIED" => ErrorClass::PermissionDenied,
            "PROVIDER_TIMEOUT" | "PROVIDER_RATE_LIMIT" | "PROVIDER_UNAVAILABLE" => {
                ErrorClass::ProviderTransient
            }
            _ if result.status == ToolStatus::FatalError => ErrorClass::Fatal,
            _ => ErrorClass::Unknown,
        }
    }

    pub fn recovery_for(error: ErrorClass) -> RecoveryDecision {
        match error {
            ErrorClass::InvalidArguments
            | ErrorClass::PatchMismatch
            | ErrorClass::StaleWorkspace => RecoveryDecision::RetryWithFreshInspection,
            ErrorClass::Diagnostic => RecoveryDecision::RevisePlan,
            ErrorClass::ProviderTransient => RecoveryDecision::RetryTransient,
            ErrorClass::DependencyUnavailable => RecoveryDecision::BlockForCapability,
            ErrorClass::PermissionDenied | ErrorClass::Fatal => RecoveryDecision::Fail,
            ErrorClass::Unknown => RecoveryDecision::RevisePlan,
        }
    }

    pub fn record_model_usage(
        state: &mut AgentRunState,
        input_tokens: u64,
        output_tokens: u64,
        cost: f64,
    ) -> Result<(), PolicyViolation> {
        state.usage.model_calls = state.usage.model_calls.saturating_add(1);
        state.usage.input_tokens = state.usage.input_tokens.saturating_add(input_tokens);
        state.usage.output_tokens = state.usage.output_tokens.saturating_add(output_tokens);
        state.usage.cost += cost.max(0.0);
        Self::check_budgets(state)
    }

    pub fn check_budgets(state: &AgentRunState) -> Result<(), PolicyViolation> {
        let total_tokens = state
            .usage
            .input_tokens
            .saturating_add(state.usage.output_tokens);
        let elapsed = (Utc::now() - state.created_at).num_seconds().max(0) as u64;
        for (exceeded, name) in [
            (
                state.usage.model_calls > state.budgets.model_calls,
                "model calls",
            ),
            (
                state.usage.tool_calls >= state.budgets.tool_calls,
                "tool calls",
            ),
            (total_tokens > state.budgets.tokens, "tokens"),
            (state.usage.cost > state.budgets.cost, "cost"),
            (elapsed > state.budgets.wall_seconds, "elapsed time"),
        ] {
            if exceeded {
                return Err(PolicyViolation::BudgetExceeded(name.into()));
            }
        }
        Ok(())
    }

    pub fn reject_finish(
        state: &mut AgentRunState,
        gate_fingerprint: &str,
    ) -> Result<(), PolicyViolation> {
        if repeated(
            &state.policy.finish_rejection_fingerprints,
            gate_fingerprint,
        ) >= REPEAT_LIMIT
        {
            return Err(PolicyViolation::RejectedFinishLoop(gate_fingerprint.into()));
        }
        push_bounded(
            &mut state.policy.finish_rejection_fingerprints,
            gate_fingerprint.into(),
        );
        Ok(())
    }

    pub fn block_for_missing_requirement(
        state: &mut AgentRunState,
        kind: MissingRequirementKind,
        detail: &str,
    ) -> Result<(), PolicyViolation> {
        if detail.trim().is_empty() {
            return Err(PolicyViolation::InvalidBlockedReason);
        }
        let prefix = match kind {
            MissingRequirementKind::UserInput => "User input required",
            MissingRequirementKind::Capability => "Capability unavailable",
        };
        state
            .transition(
                RunStatus::Blocked,
                Some(format!("{prefix}: {}", detail.trim())),
            )
            .map_err(|error| match error {
                AgentRunError::InvalidTransition { .. } => {
                    PolicyViolation::InvalidRunStatus(state.status)
                }
                _ => PolicyViolation::InvalidBlockedReason,
            })
    }
}

fn repeated(history: &[String], fingerprint: &str) -> usize {
    history
        .iter()
        .rev()
        .take_while(|item| item.as_str() == fingerprint)
        .count()
}

fn push_bounded(history: &mut Vec<String>, value: String) {
    history.push(value);
    if history.len() > HISTORY_LIMIT {
        history.remove(0);
    }
}

fn fingerprint(value: &Value) -> String {
    hex::encode(Sha256::digest(
        serde_json::to_vec(value).unwrap_or_default(),
    ))
}

fn canonical_json(value: &Value) -> Value {
    match value {
        Value::Object(map) => {
            let mut entries = map.iter().collect::<Vec<_>>();
            entries.sort_by_key(|(key, _)| *key);
            Value::Object(
                entries
                    .into_iter()
                    .map(|(key, value)| (key.clone(), canonical_json(value)))
                    .collect(),
            )
        }
        Value::Array(items) => Value::Array(items.iter().map(canonical_json).collect()),
        other => other.clone(),
    }
}
