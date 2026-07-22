//! Durable, LLM-independent state machine for autonomous agent runs.

use std::fmt;
use std::fs;
use std::path::{Path, PathBuf};

use chrono::{DateTime, Utc};
use rusqlite::{params, Connection, OptionalExtension, Transaction};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use uuid::Uuid;

pub const LEGACY_REACT_RUNTIME: &str = "legacy-react-v1";
pub const TARGET_STATE_MACHINE_RUNTIME: &str = "state-machine-v2";
const SCHEMA_VERSION: i64 = 1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RunStatus {
    Received,
    Understanding,
    Planning,
    Executing,
    Verifying,
    Recovering,
    Completed,
    Blocked,
    Failed,
    Cancelled,
}

impl RunStatus {
    pub fn is_terminal(self) -> bool {
        matches!(self, Self::Completed | Self::Failed | Self::Cancelled)
    }

    pub fn can_transition_to(self, next: Self) -> bool {
        use RunStatus::*;
        matches!(
            (self, next),
            (Received, Understanding | Failed | Cancelled)
                | (Understanding, Planning | Blocked | Failed | Cancelled)
                | (Planning, Executing | Blocked | Failed | Cancelled)
                | (
                    Executing,
                    Planning | Verifying | Recovering | Blocked | Failed | Cancelled
                )
                | (
                    Verifying,
                    Completed | Recovering | Blocked | Failed | Cancelled
                )
                | (
                    Recovering,
                    Planning | Executing | Verifying | Blocked | Failed | Cancelled
                )
                | (Blocked, Planning | Failed | Cancelled)
        )
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PlanStepStatus {
    Pending,
    InProgress,
    Completed,
    Blocked,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PlanStep {
    pub id: String,
    pub text: String,
    pub status: PlanStepStatus,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RunBudgets {
    pub model_calls: u32,
    pub tool_calls: u32,
    pub tokens: u64,
    pub wall_seconds: u64,
    #[serde(default = "default_cost_budget")]
    pub cost: f64,
    #[serde(default = "default_compile_retries")]
    pub compile_retries: u32,
    #[serde(default = "default_render_retries")]
    pub render_retries: u32,
}

fn default_cost_budget() -> f64 {
    2.0
}
fn default_compile_retries() -> u32 {
    5
}
fn default_render_retries() -> u32 {
    3
}

impl Default for RunBudgets {
    fn default() -> Self {
        Self {
            model_calls: 20,
            tool_calls: 40,
            tokens: 100_000,
            wall_seconds: 900,
            cost: default_cost_budget(),
            compile_retries: default_compile_retries(),
            render_retries: default_render_retries(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct RunUsage {
    pub model_calls: u32,
    pub tool_calls: u32,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub cost: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct PolicyRuntimeState {
    pub active_plan_step_id: Option<String>,
    pub action_fingerprints: Vec<String>,
    pub observation_fingerprints: Vec<String>,
    pub finish_rejection_fingerprints: Vec<String>,
    pub plan_revision_fingerprints: Vec<String>,
    pub compile_attempts: u32,
    pub render_attempts: u32,
    pub last_meaningful_sequence: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AgentRunState {
    pub schema_version: u32,
    pub sequence: u64,
    pub run_id: String,
    pub runtime_version: String,
    pub project_id: String,
    pub objective: String,
    pub acceptance_criteria: Vec<String>,
    pub status: RunStatus,
    pub plan: Vec<PlanStep>,
    pub facts: Vec<Value>,
    pub files_inspected: Vec<String>,
    pub changes: Vec<Value>,
    pub diagnostics: Vec<Value>,
    pub verification: Vec<Value>,
    pub budgets: RunBudgets,
    pub usage: RunUsage,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub last_progress_at: DateTime<Utc>,
    pub terminal_reason: Option<String>,
    #[serde(default)]
    pub policy: PolicyRuntimeState,
    #[serde(default)]
    pub completion_manifest: Option<Value>,
}

impl AgentRunState {
    pub fn new(
        project_id: impl Into<String>,
        objective: impl Into<String>,
    ) -> Result<Self, AgentRunError> {
        let project_id = project_id.into();
        let objective = objective.into().trim().to_string();
        if project_id.trim().is_empty() || objective.is_empty() {
            return Err(AgentRunError::Validation(
                "project_id and objective are required".into(),
            ));
        }
        let now = Utc::now();
        Ok(Self {
            schema_version: SCHEMA_VERSION as u32,
            sequence: 0,
            run_id: Uuid::new_v4().to_string(),
            runtime_version: TARGET_STATE_MACHINE_RUNTIME.to_string(),
            project_id,
            objective,
            acceptance_criteria: Vec::new(),
            status: RunStatus::Received,
            plan: Vec::new(),
            facts: Vec::new(),
            files_inspected: Vec::new(),
            changes: Vec::new(),
            diagnostics: Vec::new(),
            verification: Vec::new(),
            budgets: RunBudgets::default(),
            usage: RunUsage::default(),
            created_at: now,
            updated_at: now,
            last_progress_at: now,
            terminal_reason: None,
            policy: PolicyRuntimeState::default(),
            completion_manifest: None,
        })
    }

    pub fn transition(
        &mut self,
        next: RunStatus,
        reason: Option<String>,
    ) -> Result<(), AgentRunError> {
        if !self.status.can_transition_to(next) {
            return Err(AgentRunError::InvalidTransition {
                from: self.status,
                to: next,
            });
        }
        if matches!(
            next,
            RunStatus::Blocked | RunStatus::Failed | RunStatus::Cancelled
        ) && reason
            .as_deref()
            .map(str::trim)
            .unwrap_or_default()
            .is_empty()
        {
            return Err(AgentRunError::Validation(format!(
                "{next:?} requires a reason"
            )));
        }
        self.status = next;
        self.terminal_reason = if matches!(
            next,
            RunStatus::Blocked | RunStatus::Failed | RunStatus::Cancelled
        ) {
            reason
        } else {
            None
        };
        let now = Utc::now();
        self.updated_at = now;
        self.last_progress_at = now;
        Ok(())
    }
}

#[derive(Debug)]
pub enum AgentRunError {
    Database(String),
    Serialization(String),
    Validation(String),
    NotFound(String),
    Conflict { expected: u64, actual: u64 },
    InvalidTransition { from: RunStatus, to: RunStatus },
    WorkspaceChanged { expected: String, actual: String },
}

impl fmt::Display for AgentRunError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Database(v)
            | Self::Serialization(v)
            | Self::Validation(v)
            | Self::NotFound(v) => f.write_str(v),
            Self::Conflict { expected, actual } => write!(
                f,
                "checkpoint conflict: expected sequence {expected}, found {actual}"
            ),
            Self::InvalidTransition { from, to } => {
                write!(f, "invalid agent transition: {from:?} -> {to:?}")
            }
            Self::WorkspaceChanged { expected, actual } => {
                write!(f, "workspace changed: expected {expected}, found {actual}")
            }
        }
    }
}

impl std::error::Error for AgentRunError {}

impl From<rusqlite::Error> for AgentRunError {
    fn from(value: rusqlite::Error) -> Self {
        Self::Database(value.to_string())
    }
}

impl From<serde_json::Error> for AgentRunError {
    fn from(value: serde_json::Error) -> Self {
        Self::Serialization(value.to_string())
    }
}

#[derive(Debug, Clone)]
pub struct AgentRunStore {
    db_path: PathBuf,
}

impl AgentRunStore {
    pub fn open(db_path: PathBuf) -> Result<Self, AgentRunError> {
        if let Some(parent) = db_path.parent() {
            fs::create_dir_all(parent).map_err(|e| AgentRunError::Database(e.to_string()))?;
        }
        let store = Self { db_path };
        store.with_connection(|conn| {
            conn.execute_batch(
                "PRAGMA journal_mode=WAL;
                 PRAGMA foreign_keys=ON;
                 CREATE TABLE IF NOT EXISTS agent_schema(version INTEGER NOT NULL);
                 INSERT INTO agent_schema(version) SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM agent_schema);
                 CREATE TABLE IF NOT EXISTS agent_runs(
                   run_id TEXT PRIMARY KEY,
                   project_id TEXT NOT NULL,
                   runtime_version TEXT NOT NULL,
                   status TEXT NOT NULL,
                   sequence INTEGER NOT NULL,
                   workspace_fingerprint TEXT NOT NULL,
                   state_json TEXT NOT NULL,
                   created_at TEXT NOT NULL,
                   updated_at TEXT NOT NULL
                 );
                 CREATE TABLE IF NOT EXISTS agent_events(
                   run_id TEXT NOT NULL,
                   sequence INTEGER NOT NULL,
                   event_type TEXT NOT NULL,
                   payload_json TEXT NOT NULL,
                   created_at TEXT NOT NULL,
                   PRIMARY KEY(run_id, sequence),
                   FOREIGN KEY(run_id) REFERENCES agent_runs(run_id) ON DELETE CASCADE
                 );
                 CREATE TABLE IF NOT EXISTS agent_mutations(
                   mutation_id TEXT PRIMARY KEY,
                   run_id TEXT NOT NULL,
                   file_path TEXT NOT NULL,
                   before_hash TEXT NOT NULL,
                   after_hash TEXT NOT NULL,
                   snapshot_path TEXT NOT NULL,
                   changed_start_line INTEGER NOT NULL,
                   changed_end_line INTEGER NOT NULL,
                   rolled_back INTEGER NOT NULL DEFAULT 0,
                   created_at TEXT NOT NULL,
                   FOREIGN KEY(run_id) REFERENCES agent_runs(run_id) ON DELETE CASCADE
                 );
                 CREATE TABLE IF NOT EXISTS agent_context_items(
                   item_id TEXT PRIMARY KEY,
                   run_id TEXT NOT NULL,
                   sequence INTEGER NOT NULL,
                   kind TEXT NOT NULL,
                   resolution TEXT NOT NULL,
                   source TEXT NOT NULL,
                   summary TEXT NOT NULL,
                   raw_json TEXT NOT NULL,
                   pinned INTEGER NOT NULL DEFAULT 0,
                   compacted INTEGER NOT NULL DEFAULT 0,
                   created_at TEXT NOT NULL,
                   FOREIGN KEY(run_id) REFERENCES agent_runs(run_id) ON DELETE CASCADE
                 );
                 CREATE TABLE IF NOT EXISTS agent_model_calls(
                   call_id TEXT PRIMARY KEY,
                   run_id TEXT NOT NULL,
                   provider TEXT NOT NULL,
                   model TEXT NOT NULL,
                   request_id TEXT NOT NULL,
                   billing_mode TEXT NOT NULL,
                   input_tokens INTEGER NOT NULL,
                   output_tokens INTEGER NOT NULL,
                   latency_ms INTEGER NOT NULL,
                   cost_usd REAL NOT NULL,
                   charged_credits INTEGER NOT NULL,
                   created_at TEXT NOT NULL,
                   FOREIGN KEY(run_id) REFERENCES agent_runs(run_id) ON DELETE CASCADE
                 );
                 CREATE TABLE IF NOT EXISTS agent_stream_events(
                   event_id TEXT PRIMARY KEY,
                   run_id TEXT NOT NULL,
                   stream_sequence INTEGER NOT NULL,
                   schema_version INTEGER NOT NULL,
                   event_type TEXT NOT NULL,
                   payload_json TEXT NOT NULL,
                   created_at TEXT NOT NULL,
                   UNIQUE(run_id, stream_sequence),
                   FOREIGN KEY(run_id) REFERENCES agent_runs(run_id) ON DELETE CASCADE
                 );"
            )?;
            let version: i64 = conn.query_row("SELECT version FROM agent_schema LIMIT 1", [], |row| row.get(0))?;
            if version != SCHEMA_VERSION {
                return Err(AgentRunError::Database(format!("unsupported agent database schema {version}")));
            }
            Ok(())
        })?;
        Ok(store)
    }

    fn with_connection<T>(
        &self,
        f: impl FnOnce(&mut Connection) -> Result<T, AgentRunError>,
    ) -> Result<T, AgentRunError> {
        let mut conn = Connection::open(&self.db_path)?;
        conn.pragma_update(None, "foreign_keys", true)?;
        f(&mut conn)
    }

    pub fn create_run(
        &self,
        state: AgentRunState,
        workspace: &Path,
    ) -> Result<AgentRunState, AgentRunError> {
        let fingerprint = workspace_fingerprint(workspace)?;
        self.with_connection(|conn| {
            let tx = conn.transaction()?;
            insert_run(&tx, &state, &fingerprint)?;
            insert_event(
                &tx,
                &state.run_id,
                0,
                "run_created",
                &serde_json::json!({"status": state.status}),
            )?;
            tx.commit()?;
            Ok(state)
        })
    }

    pub fn load_run(&self, run_id: &str) -> Result<AgentRunState, AgentRunError> {
        self.with_connection(|conn| load_state(conn, run_id))
    }

    pub fn checkpoint(
        &self,
        mut state: AgentRunState,
        expected_sequence: u64,
        workspace: &Path,
        event_type: &str,
        payload: Value,
    ) -> Result<AgentRunState, AgentRunError> {
        let fingerprint = workspace_fingerprint(workspace)?;
        self.with_connection(|conn| {
            checkpoint_tx(
                conn,
                &mut state,
                expected_sequence,
                &fingerprint,
                event_type,
                payload,
            )
        })
    }

    pub fn transition(
        &self,
        run_id: &str,
        next: RunStatus,
        reason: Option<String>,
        workspace: &Path,
    ) -> Result<AgentRunState, AgentRunError> {
        let mut state = self.load_run(run_id)?;
        let expected = state.sequence;
        state.transition(next, reason.clone())?;
        self.checkpoint(
            state,
            expected,
            workspace,
            "state_changed",
            serde_json::json!({"to": next, "reason": reason}),
        )
    }

    pub fn cancel(
        &self,
        run_id: &str,
        reason: impl Into<String>,
        workspace: &Path,
    ) -> Result<AgentRunState, AgentRunError> {
        self.transition(run_id, RunStatus::Cancelled, Some(reason.into()), workspace)
    }

    pub fn resume(&self, run_id: &str, workspace: &Path) -> Result<AgentRunState, AgentRunError> {
        let actual = workspace_fingerprint(workspace)?;
        self.with_connection(|conn| {
            let (expected, mut state): (String, AgentRunState) = conn
                .query_row(
                    "SELECT workspace_fingerprint, state_json FROM agent_runs WHERE run_id=?1",
                    [run_id],
                    |row| {
                        let raw: String = row.get(1)?;
                        let parsed = serde_json::from_str(&raw).map_err(|e| rusqlite::Error::FromSqlConversionFailure(raw.len(), rusqlite::types::Type::Text, Box::new(e)))?;
                        Ok((row.get(0)?, parsed))
                    },
                )
                .optional()?
                .ok_or_else(|| AgentRunError::NotFound(format!("agent run '{run_id}' not found")))?;
            if expected != actual {
                if !state.status.is_terminal() && state.status != RunStatus::Blocked {
                    let previous = state.sequence;
                    state.transition(RunStatus::Blocked, Some("Workspace changed since the last checkpoint; reconciliation is required.".into()))?;
                    checkpoint_tx(conn, &mut state, previous, &actual, "workspace_conflict", serde_json::json!({"expected": expected, "actual": actual}))?;
                }
                return Err(AgentRunError::WorkspaceChanged { expected, actual });
            }
            Ok(state)
        })
    }

    pub fn event_count(&self, run_id: &str) -> Result<u64, AgentRunError> {
        self.with_connection(|conn| {
            let count: u64 = conn.query_row(
                "SELECT COUNT(*) FROM agent_events WHERE run_id=?1",
                [run_id],
                |row| row.get(0),
            )?;
            Ok(count)
        })
    }

    pub fn record_mutation(&self, mutation: &MutationRecord) -> Result<(), AgentRunError> {
        self.with_connection(|conn| {
            conn.execute(
                "INSERT INTO agent_mutations(
                   mutation_id, run_id, file_path, before_hash, after_hash, snapshot_path,
                   changed_start_line, changed_end_line, rolled_back, created_at
                 ) VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 0, ?9)",
                params![
                    mutation.mutation_id,
                    mutation.run_id,
                    mutation.file_path,
                    mutation.before_hash,
                    mutation.after_hash,
                    mutation.snapshot_path,
                    mutation.changed_start_line,
                    mutation.changed_end_line,
                    mutation.created_at.to_rfc3339(),
                ],
            )?;
            Ok(())
        })
    }

    pub fn load_mutation(&self, mutation_id: &str) -> Result<MutationRecord, AgentRunError> {
        self.with_connection(|conn| {
            conn.query_row(
                "SELECT mutation_id, run_id, file_path, before_hash, after_hash, snapshot_path,
                        changed_start_line, changed_end_line, rolled_back, created_at
                 FROM agent_mutations WHERE mutation_id=?1",
                [mutation_id],
                |row| {
                    let created: String = row.get(9)?;
                    let created_at = DateTime::parse_from_rfc3339(&created)
                        .map_err(|e| {
                            rusqlite::Error::FromSqlConversionFailure(
                                created.len(),
                                rusqlite::types::Type::Text,
                                Box::new(e),
                            )
                        })?
                        .with_timezone(&Utc);
                    Ok(MutationRecord {
                        mutation_id: row.get(0)?,
                        run_id: row.get(1)?,
                        file_path: row.get(2)?,
                        before_hash: row.get(3)?,
                        after_hash: row.get(4)?,
                        snapshot_path: row.get(5)?,
                        changed_start_line: row.get(6)?,
                        changed_end_line: row.get(7)?,
                        rolled_back: row.get::<_, i64>(8)? != 0,
                        created_at,
                    })
                },
            )
            .optional()?
            .ok_or_else(|| AgentRunError::NotFound(format!("mutation '{mutation_id}' not found")))
        })
    }

    pub fn mark_mutation_rolled_back(&self, mutation_id: &str) -> Result<(), AgentRunError> {
        self.with_connection(|conn| {
            let changed = conn.execute(
                "UPDATE agent_mutations SET rolled_back=1 WHERE mutation_id=?1 AND rolled_back=0",
                [mutation_id],
            )?;
            if changed != 1 {
                return Err(AgentRunError::Conflict {
                    expected: 0,
                    actual: 1,
                });
            }
            Ok(())
        })
    }

    pub fn add_context_item(
        &self,
        item: &crate::agent_context::ContextMemoryItem,
    ) -> Result<(), AgentRunError> {
        self.with_connection(|conn| {
            conn.execute(
                "INSERT INTO agent_context_items(
                   item_id, run_id, sequence, kind, resolution, source, summary,
                   raw_json, pinned, compacted, created_at
                 ) VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
                params![
                    item.item_id,
                    item.run_id,
                    item.sequence,
                    item.kind.as_str(),
                    item.resolution.as_str(),
                    item.source,
                    item.summary,
                    serde_json::to_string(&item.raw)?,
                    i64::from(item.pinned),
                    i64::from(item.compacted),
                    item.created_at.to_rfc3339(),
                ],
            )?;
            Ok(())
        })
    }

    pub fn load_context_item(
        &self,
        item_id: &str,
    ) -> Result<crate::agent_context::ContextMemoryItem, AgentRunError> {
        self.with_connection(|conn| load_context_item_row(conn, item_id))
    }

    pub fn list_context_items(
        &self,
        run_id: &str,
    ) -> Result<Vec<crate::agent_context::ContextMemoryItem>, AgentRunError> {
        self.with_connection(|conn| {
            let mut statement = conn.prepare(
                "SELECT item_id, run_id, sequence, kind, resolution, source, summary,
                        raw_json, pinned, compacted, created_at
                 FROM agent_context_items WHERE run_id=?1
                 ORDER BY pinned DESC, sequence DESC, created_at DESC",
            )?;
            let rows = statement.query_map([run_id], context_item_from_row)?;
            rows.collect::<Result<Vec<_>, _>>()
                .map_err(AgentRunError::from)
        })
    }

    pub fn compact_resolved_context(
        &self,
        run_id: &str,
        through_sequence: u64,
    ) -> Result<usize, AgentRunError> {
        self.with_connection(|conn| {
            let changed = conn.execute(
                "UPDATE agent_context_items SET compacted=1
                 WHERE run_id=?1 AND sequence<=?2 AND resolution='resolved'",
                params![run_id, through_sequence],
            )?;
            Ok(changed)
        })
    }

    pub fn resolve_context_item(&self, item_id: &str) -> Result<(), AgentRunError> {
        self.with_connection(|conn| {
            let changed = conn.execute(
                "UPDATE agent_context_items SET resolution='resolved' WHERE item_id=?1 AND resolution='unresolved'",
                [item_id],
            )?;
            if changed != 1 {
                return Err(AgentRunError::Conflict { expected: 0, actual: 1 });
            }
            Ok(())
        })
    }

    pub fn record_model_call(
        &self,
        call: &crate::agent_accounting::AgentModelCall,
    ) -> Result<(), AgentRunError> {
        self.with_connection(|conn| {
            conn.execute(
                "INSERT INTO agent_model_calls(
                   call_id, run_id, provider, model, request_id, billing_mode,
                   input_tokens, output_tokens, latency_ms, cost_usd, charged_credits, created_at
                 ) VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
                params![
                    call.call_id,
                    call.run_id,
                    call.provider,
                    call.model,
                    call.request_id,
                    call.billing_mode.as_str(),
                    call.input_tokens,
                    call.output_tokens,
                    call.latency_ms,
                    call.cost_usd,
                    call.charged_credits,
                    call.created_at.to_rfc3339(),
                ],
            )?;
            Ok(())
        })
    }

    pub fn list_model_calls(
        &self,
        run_id: &str,
    ) -> Result<Vec<crate::agent_accounting::AgentModelCall>, AgentRunError> {
        self.with_connection(|conn| {
            let mut statement = conn.prepare(
                "SELECT call_id, run_id, provider, model, request_id, billing_mode,
                        input_tokens, output_tokens, latency_ms, cost_usd, charged_credits, created_at
                 FROM agent_model_calls WHERE run_id=?1 ORDER BY created_at, call_id",
            )?;
            let rows = statement.query_map([run_id], |row| {
                use crate::agent_accounting::{AgentModelCall, BillingMode};
                let mode: String = row.get(5)?;
                let created: String = row.get(11)?;
                Ok(AgentModelCall {
                    call_id: row.get(0)?,
                    run_id: row.get(1)?,
                    provider: row.get(2)?,
                    model: row.get(3)?,
                    request_id: row.get(4)?,
                    billing_mode: BillingMode::parse(&mode).map_err(sql_conversion_error)?,
                    input_tokens: row.get(6)?,
                    output_tokens: row.get(7)?,
                    latency_ms: row.get(8)?,
                    cost_usd: row.get(9)?,
                    charged_credits: row.get(10)?,
                    created_at: DateTime::parse_from_rfc3339(&created)
                        .map_err(sql_conversion_error)?
                        .with_timezone(&Utc),
                })
            })?;
            rows.collect::<Result<Vec<_>, _>>().map_err(AgentRunError::from)
        })
    }

    pub fn append_stream_event(
        &self,
        event_type: &str,
        run_id: &str,
        payload: &Value,
    ) -> Result<crate::agent_events::AgentStreamEvent, AgentRunError> {
        self.with_connection(|conn| {
            let tx = conn.transaction()?;
            let sequence: u64 = tx.query_row(
                "SELECT COALESCE(MAX(stream_sequence), 0) + 1 FROM agent_stream_events WHERE run_id=?1",
                [run_id],
                |row| row.get(0),
            )?;
            let event = crate::agent_events::AgentStreamEvent::new(
                run_id,
                sequence,
                event_type,
                payload.clone(),
            );
            tx.execute(
                "INSERT INTO agent_stream_events(
                   event_id, run_id, stream_sequence, schema_version, event_type, payload_json, created_at
                 ) VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                params![
                    event.event_id,
                    event.run_id,
                    event.sequence,
                    event.schema_version,
                    event.event_type,
                    serde_json::to_string(&event.payload)?,
                    event.created_at.to_rfc3339(),
                ],
            )?;
            tx.commit()?;
            Ok(event)
        })
    }

    pub fn list_stream_events(
        &self,
        run_id: &str,
        after_sequence: u64,
        limit: usize,
    ) -> Result<Vec<crate::agent_events::AgentStreamEvent>, AgentRunError> {
        let limit = limit.clamp(1, 500) as u64;
        self.with_connection(|conn| {
            let mut statement = conn.prepare(
                "SELECT event_id, run_id, stream_sequence, schema_version, event_type, payload_json, created_at
                 FROM agent_stream_events WHERE run_id=?1 AND stream_sequence>?2
                 ORDER BY stream_sequence LIMIT ?3",
            )?;
            let rows = statement.query_map(params![run_id, after_sequence, limit], |row| {
                let payload: String = row.get(5)?;
                let created: String = row.get(6)?;
                Ok(crate::agent_events::AgentStreamEvent {
                    event_id: row.get(0)?,
                    run_id: row.get(1)?,
                    sequence: row.get(2)?,
                    schema_version: row.get(3)?,
                    event_type: row.get(4)?,
                    payload: serde_json::from_str(&payload).map_err(sql_conversion_error)?,
                    created_at: DateTime::parse_from_rfc3339(&created)
                        .map_err(sql_conversion_error)?
                        .with_timezone(&Utc),
                })
            })?;
            rows.collect::<Result<Vec<_>, _>>().map_err(AgentRunError::from)
        })
    }

    pub fn list_runs(&self, limit: usize) -> Result<Vec<AgentRunState>, AgentRunError> {
        let limit = limit.clamp(1, 200) as u64;
        self.with_connection(|conn| {
            let mut statement = conn
                .prepare("SELECT state_json FROM agent_runs ORDER BY updated_at DESC LIMIT ?1")?;
            let rows = statement.query_map([limit], |row| {
                let raw: String = row.get(0)?;
                serde_json::from_str(&raw).map_err(sql_conversion_error)
            })?;
            rows.collect::<Result<Vec<_>, _>>()
                .map_err(AgentRunError::from)
        })
    }
}

fn load_context_item_row(
    conn: &Connection,
    item_id: &str,
) -> Result<crate::agent_context::ContextMemoryItem, AgentRunError> {
    conn.query_row(
        "SELECT item_id, run_id, sequence, kind, resolution, source, summary,
                raw_json, pinned, compacted, created_at
         FROM agent_context_items WHERE item_id=?1",
        [item_id],
        context_item_from_row,
    )
    .optional()?
    .ok_or_else(|| AgentRunError::NotFound(format!("context item '{item_id}' not found")))
}

fn context_item_from_row(
    row: &rusqlite::Row<'_>,
) -> rusqlite::Result<crate::agent_context::ContextMemoryItem> {
    use crate::agent_context::{ContextItemKind, ContextMemoryItem, ContextResolution};
    let kind: String = row.get(3)?;
    let resolution: String = row.get(4)?;
    let raw: String = row.get(7)?;
    let created: String = row.get(10)?;
    Ok(ContextMemoryItem {
        item_id: row.get(0)?,
        run_id: row.get(1)?,
        sequence: row.get(2)?,
        kind: ContextItemKind::parse(&kind).map_err(sql_conversion_error)?,
        resolution: ContextResolution::parse(&resolution).map_err(sql_conversion_error)?,
        source: row.get(5)?,
        summary: row.get(6)?,
        raw: serde_json::from_str(&raw).map_err(sql_conversion_error)?,
        pinned: row.get::<_, i64>(8)? != 0,
        compacted: row.get::<_, i64>(9)? != 0,
        created_at: DateTime::parse_from_rfc3339(&created)
            .map_err(sql_conversion_error)?
            .with_timezone(&Utc),
    })
}

fn sql_conversion_error(error: impl std::error::Error + Send + Sync + 'static) -> rusqlite::Error {
    rusqlite::Error::FromSqlConversionFailure(0, rusqlite::types::Type::Text, Box::new(error))
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MutationRecord {
    pub mutation_id: String,
    pub run_id: String,
    pub file_path: String,
    pub before_hash: String,
    pub after_hash: String,
    pub snapshot_path: String,
    pub changed_start_line: u64,
    pub changed_end_line: u64,
    pub rolled_back: bool,
    pub created_at: DateTime<Utc>,
}

fn insert_run(
    tx: &Transaction<'_>,
    state: &AgentRunState,
    fingerprint: &str,
) -> Result<(), AgentRunError> {
    let raw = serde_json::to_string(state)?;
    tx.execute(
        "INSERT INTO agent_runs(run_id, project_id, runtime_version, status, sequence, workspace_fingerprint, state_json, created_at, updated_at)
         VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        params![state.run_id, state.project_id, state.runtime_version, status_name(state.status), state.sequence, fingerprint, raw, state.created_at.to_rfc3339(), state.updated_at.to_rfc3339()],
    )?;
    Ok(())
}

fn load_state(conn: &Connection, run_id: &str) -> Result<AgentRunState, AgentRunError> {
    let raw: String = conn
        .query_row(
            "SELECT state_json FROM agent_runs WHERE run_id=?1",
            [run_id],
            |row| row.get(0),
        )
        .optional()?
        .ok_or_else(|| AgentRunError::NotFound(format!("agent run '{run_id}' not found")))?;
    Ok(serde_json::from_str(&raw)?)
}

fn checkpoint_tx(
    conn: &mut Connection,
    state: &mut AgentRunState,
    expected_sequence: u64,
    fingerprint: &str,
    event_type: &str,
    payload: Value,
) -> Result<AgentRunState, AgentRunError> {
    let tx = conn.transaction()?;
    let actual: u64 = tx.query_row(
        "SELECT sequence FROM agent_runs WHERE run_id=?1",
        [&state.run_id],
        |row| row.get(0),
    )?;
    if actual != expected_sequence {
        return Err(AgentRunError::Conflict {
            expected: expected_sequence,
            actual,
        });
    }
    state.sequence = expected_sequence + 1;
    state.updated_at = Utc::now();
    let raw = serde_json::to_string(state)?;
    let changed = tx.execute(
        "UPDATE agent_runs SET status=?1, sequence=?2, workspace_fingerprint=?3, state_json=?4, updated_at=?5 WHERE run_id=?6 AND sequence=?7",
        params![status_name(state.status), state.sequence, fingerprint, raw, state.updated_at.to_rfc3339(), state.run_id, expected_sequence],
    )?;
    if changed != 1 {
        return Err(AgentRunError::Conflict {
            expected: expected_sequence,
            actual,
        });
    }
    insert_event(&tx, &state.run_id, state.sequence, event_type, &payload)?;
    tx.commit()?;
    Ok(state.clone())
}

fn insert_event(
    tx: &Transaction<'_>,
    run_id: &str,
    sequence: u64,
    event_type: &str,
    payload: &Value,
) -> Result<(), AgentRunError> {
    tx.execute(
        "INSERT INTO agent_events(run_id, sequence, event_type, payload_json, created_at) VALUES(?1, ?2, ?3, ?4, ?5)",
        params![run_id, sequence, event_type, serde_json::to_string(payload)?, Utc::now().to_rfc3339()],
    )?;
    Ok(())
}

fn status_name(status: RunStatus) -> &'static str {
    match status {
        RunStatus::Received => "received",
        RunStatus::Understanding => "understanding",
        RunStatus::Planning => "planning",
        RunStatus::Executing => "executing",
        RunStatus::Verifying => "verifying",
        RunStatus::Recovering => "recovering",
        RunStatus::Completed => "completed",
        RunStatus::Blocked => "blocked",
        RunStatus::Failed => "failed",
        RunStatus::Cancelled => "cancelled",
    }
}

pub fn workspace_fingerprint(workspace: &Path) -> Result<String, AgentRunError> {
    let mut hasher = Sha256::new();
    for name in [
        "project.json",
        "scenes.py",
        "helpers.py",
        "brief/passport.json",
        "brief/description.md",
        "brief/tape.md",
        "brief/roadmap.json",
        "brief/narration.md",
    ] {
        let path = workspace.join(name);
        hasher.update(name.as_bytes());
        if path.exists() {
            let content = fs::read(&path)
                .map_err(|e| AgentRunError::Validation(format!("read {}: {e}", path.display())))?;
            hasher.update((content.len() as u64).to_le_bytes());
            hasher.update(content);
        } else {
            hasher.update(b"<missing>");
        }
    }
    Ok(hex::encode(hasher.finalize()))
}
