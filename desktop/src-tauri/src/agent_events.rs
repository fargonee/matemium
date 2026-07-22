//! Versioned, bounded, redacted event stream for agent UI and IPC.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use uuid::Uuid;

pub const AGENT_EVENT_SCHEMA_VERSION: u32 = 1;
const MAX_STRING_BYTES: usize = 2048;
const MAX_ARRAY_ITEMS: usize = 50;
const MAX_EVENT_BYTES: usize = 16 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AgentEventKind {
    RunStarted,
    StateChanged,
    PlanUpdated,
    ActionStarted,
    ActionCompleted,
    VerificationStarted,
    VerificationCompleted,
    UsageRecorded,
    BudgetUpdated,
    CheckpointSaved,
    ApprovalRequested,
    ApprovalRecorded,
    InputRequired,
    InputReceived,
    RunCompleted,
    RunBlocked,
    RunFailed,
    RunCancelled,
    RunResumed,
}

impl AgentEventKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::RunStarted => "run_started",
            Self::StateChanged => "state_changed",
            Self::PlanUpdated => "plan_updated",
            Self::ActionStarted => "action_started",
            Self::ActionCompleted => "action_completed",
            Self::VerificationStarted => "verification_started",
            Self::VerificationCompleted => "verification_completed",
            Self::UsageRecorded => "usage_recorded",
            Self::BudgetUpdated => "budget_updated",
            Self::CheckpointSaved => "checkpoint_saved",
            Self::ApprovalRequested => "approval_requested",
            Self::ApprovalRecorded => "approval_recorded",
            Self::InputRequired => "input_required",
            Self::InputReceived => "input_received",
            Self::RunCompleted => "run_completed",
            Self::RunBlocked => "run_blocked",
            Self::RunFailed => "run_failed",
            Self::RunCancelled => "run_cancelled",
            Self::RunResumed => "run_resumed",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AgentStreamEvent {
    pub event_id: String,
    pub run_id: String,
    pub sequence: u64,
    pub schema_version: u32,
    pub event_type: String,
    pub payload: Value,
    pub created_at: DateTime<Utc>,
}

impl AgentStreamEvent {
    pub fn new(run_id: &str, sequence: u64, event_type: &str, payload: Value) -> Self {
        Self {
            event_id: Uuid::new_v4().to_string(),
            run_id: run_id.into(),
            sequence,
            schema_version: AGENT_EVENT_SCHEMA_VERSION,
            event_type: event_type.into(),
            payload: sanitize_payload(payload),
            created_at: Utc::now(),
        }
    }

    pub fn new_typed(run_id: &str, sequence: u64, kind: AgentEventKind, payload: Value) -> Self {
        Self::new(run_id, sequence, kind.as_str(), payload)
    }
}

pub fn sanitize_payload(payload: Value) -> Value {
    let mut sanitized = sanitize_value(payload);
    let encoded = serde_json::to_vec(&sanitized).unwrap_or_default();
    if encoded.len() > MAX_EVENT_BYTES {
        sanitized = serde_json::json!({
            "truncated": true,
            "original_bytes": encoded.len(),
            "summary": "Event payload exceeded the 16 KiB stream limit. Reload bounded raw evidence by item ID."
        });
    }
    sanitized
}

fn sanitize_value(value: Value) -> Value {
    match value {
        Value::Object(map) => Value::Object(
            map.into_iter()
                .map(|(key, value)| {
                    let lower = key.to_lowercase();
                    let redacted = [
                        "api_key",
                        "apikey",
                        "authorization",
                        "password",
                        "secret",
                        "access_token",
                        "refresh_token",
                    ]
                    .iter()
                    .any(|needle| lower.contains(needle));
                    (
                        key,
                        if redacted {
                            Value::String("[REDACTED]".into())
                        } else {
                            sanitize_value(value)
                        },
                    )
                })
                .collect::<Map<_, _>>(),
        ),
        Value::Array(items) => Value::Array(
            items
                .into_iter()
                .take(MAX_ARRAY_ITEMS)
                .map(sanitize_value)
                .collect(),
        ),
        Value::String(mut text) => {
            truncate_utf8(&mut text, MAX_STRING_BYTES);
            Value::String(text)
        }
        other => other,
    }
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
    value.push_str("…[truncated]");
}
