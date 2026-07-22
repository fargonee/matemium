//! Per-provider-call accounting and reconciliation for agent runs.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::agent_runs::{AgentRunError, AgentRunState, AgentRunStore};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BillingMode {
    ByoExternal,
    Local,
}

impl BillingMode {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ByoExternal => "byo_external",
            Self::Local => "local",
        }
    }

    pub fn parse(value: &str) -> Result<Self, AccountingError> {
        match value {
            "byo_external" | "personal" => Ok(Self::ByoExternal),
            "local" => Ok(Self::Local),
            other => Err(AccountingError::InvalidCall(format!(
                "unknown billing mode '{other}'"
            ))),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AgentModelCall {
    pub call_id: String,
    pub run_id: String,
    pub provider: String,
    pub model: String,
    pub request_id: String,
    pub billing_mode: BillingMode,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub latency_ms: u64,
    pub cost_usd: f64,
    pub charged_credits: u64,
    pub created_at: DateTime<Utc>,
}

impl AgentModelCall {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        run_id: &str,
        provider: &str,
        model: &str,
        request_id: &str,
        billing_mode: BillingMode,
        input_tokens: u64,
        output_tokens: u64,
        latency_ms: u64,
        cost_usd: f64,
        charged_credits: u64,
    ) -> Result<Self, AccountingError> {
        if run_id.trim().is_empty()
            || provider.trim().is_empty()
            || model.trim().is_empty()
            || request_id.trim().is_empty()
        {
            return Err(AccountingError::InvalidCall(
                "run, provider, model, and request IDs are required".into(),
            ));
        }
        if !cost_usd.is_finite() || cost_usd < 0.0 {
            return Err(AccountingError::InvalidCall(
                "cost must be finite and non-negative".into(),
            ));
        }
        if charged_credits != 0 {
            return Err(AccountingError::InvalidCall(
                "Matemium no longer charges credits for model calls".into(),
            ));
        }
        Ok(Self {
            call_id: Uuid::new_v4().to_string(),
            run_id: run_id.into(),
            provider: provider.into(),
            model: model.into(),
            request_id: request_id.into(),
            billing_mode,
            input_tokens,
            output_tokens,
            latency_ms,
            cost_usd,
            charged_credits,
            created_at: Utc::now(),
        })
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UsageReconciliation {
    pub call_count: usize,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub cost_usd: f64,
    pub charged_credits: u64,
    pub matches_run_usage: bool,
    pub discrepancies: Vec<String>,
}

#[derive(Debug)]
pub enum AccountingError {
    InvalidCall(String),
    Store(AgentRunError),
}

impl std::fmt::Display for AccountingError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidCall(message) => f.write_str(message),
            Self::Store(error) => write!(f, "accounting store failed: {error}"),
        }
    }
}

impl std::error::Error for AccountingError {}
impl From<AgentRunError> for AccountingError {
    fn from(value: AgentRunError) -> Self {
        Self::Store(value)
    }
}

pub struct AgentAccounting {
    store: AgentRunStore,
}

impl AgentAccounting {
    pub fn new(store: AgentRunStore) -> Self {
        Self { store }
    }

    pub fn record(&self, call: &AgentModelCall) -> Result<(), AccountingError> {
        self.store.record_model_call(call)?;
        Ok(())
    }

    pub fn reconcile(&self, state: &AgentRunState) -> Result<UsageReconciliation, AccountingError> {
        let calls = self.store.list_model_calls(&state.run_id)?;
        let input_tokens = calls.iter().map(|call| call.input_tokens).sum();
        let output_tokens = calls.iter().map(|call| call.output_tokens).sum();
        let cost_usd: f64 = calls.iter().map(|call| call.cost_usd).sum();
        let charged_credits = calls.iter().map(|call| call.charged_credits).sum();
        let mut discrepancies = Vec::new();
        if calls.len() != state.usage.model_calls as usize {
            discrepancies.push(format!(
                "model calls: records={}, state={}",
                calls.len(),
                state.usage.model_calls
            ));
        }
        if input_tokens != state.usage.input_tokens {
            discrepancies.push(format!(
                "input tokens: records={input_tokens}, state={}",
                state.usage.input_tokens
            ));
        }
        if output_tokens != state.usage.output_tokens {
            discrepancies.push(format!(
                "output tokens: records={output_tokens}, state={}",
                state.usage.output_tokens
            ));
        }
        if (cost_usd - state.usage.cost).abs() > 0.000001 {
            discrepancies.push(format!(
                "cost: records={cost_usd:.6}, state={:.6}",
                state.usage.cost
            ));
        }
        Ok(UsageReconciliation {
            call_count: calls.len(),
            input_tokens,
            output_tokens,
            cost_usd,
            charged_credits,
            matches_run_usage: discrepancies.is_empty(),
            discrepancies,
        })
    }
}
