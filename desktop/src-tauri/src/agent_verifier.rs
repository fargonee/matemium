//! Evidence-backed completion controller for autonomous agent runtime v2.

use std::collections::{BTreeMap, BTreeSet};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::agent_policy::{AgentPolicyEngine, PolicyViolation};
use crate::agent_runs::{AgentRunError, AgentRunState, RunStatus};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceKind {
    FinalFileInspection,
    SyntaxCheck,
    ProjectCheck,
    RelevantTests,
    PreviewRender,
    VisualInspection,
    SemanticReview,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceProducer {
    Desktop,
    Sidecar,
    Verifier,
    TestHarness,
    Model,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VerificationEvidence {
    pub kind: EvidenceKind,
    pub passed: bool,
    pub source: String,
    pub producer: EvidenceProducer,
    pub summary: String,
    pub path: Option<String>,
    pub sha256: Option<String>,
    pub details: Value,
    pub recorded_at: DateTime<Utc>,
}

impl VerificationEvidence {
    pub fn passed(
        kind: EvidenceKind,
        producer: EvidenceProducer,
        source: &str,
        summary: &str,
    ) -> Self {
        Self {
            kind,
            passed: true,
            source: source.into(),
            producer,
            summary: summary.into(),
            path: None,
            sha256: None,
            details: json!({}),
            recorded_at: Utc::now(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FinishProposal {
    pub summary: String,
    pub claimed_outcomes: Vec<String>,
    pub requested_verification: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GateKind {
    FinalChangedFilesInspected,
    SyntaxPassed,
    ProjectCheckPassed,
    RelevantTestsPassed,
    PreviewRenderPassed,
    VisualInspectionPassed,
    ObjectiveAccepted,
    NoFatalDiagnostics,
    ClaimsSupported,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GateResult {
    pub gate: GateKind,
    pub passed: bool,
    pub summary: String,
    pub evidence_sources: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VerificationManifest {
    pub run_id: String,
    pub objective: String,
    pub final_summary: String,
    pub changed_files: Vec<String>,
    pub acceptance_criteria: Vec<String>,
    pub gates: Vec<GateResult>,
    pub executed_checks: Vec<String>,
    pub checks_not_run: Vec<String>,
    pub limitations: Vec<String>,
    pub verified_at: DateTime<Utc>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VerificationRejection {
    pub failed_gates: Vec<GateResult>,
    pub checks_not_run: Vec<String>,
    pub unsupported_claims: Vec<String>,
    pub retry_fingerprint: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum VerificationDecision {
    Authorized(VerificationManifest),
    Rejected(VerificationRejection),
}

#[derive(Debug)]
pub enum VerificationError {
    InvalidStatus(RunStatus),
    InvalidProposal(String),
    Policy(PolicyViolation),
    State(AgentRunError),
    Serialization(String),
}

impl std::fmt::Display for VerificationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidStatus(status) => write!(
                f,
                "verification requires verifying status, found {status:?}"
            ),
            Self::InvalidProposal(message) | Self::Serialization(message) => f.write_str(message),
            Self::Policy(error) => write!(f, "verification policy rejected finish: {error:?}"),
            Self::State(error) => write!(f, "verification state transition failed: {error}"),
        }
    }
}

impl std::error::Error for VerificationError {}

pub struct AgentVerificationController;

impl AgentVerificationController {
    pub fn required_gates(state: &AgentRunState) -> BTreeSet<GateKind> {
        let lower = state.objective.to_lowercase();
        let changed = changed_file_hashes(state);
        let mut gates = BTreeSet::from([
            GateKind::ObjectiveAccepted,
            GateKind::NoFatalDiagnostics,
            GateKind::ClaimsSupported,
        ]);
        if !changed.is_empty() {
            gates.extend([
                GateKind::FinalChangedFilesInspected,
                GateKind::SyntaxPassed,
                GateKind::ProjectCheckPassed,
                GateKind::PreviewRenderPassed,
            ]);
        }
        if ["test", "refactor", "computation", "algorithm", "helpers.py"]
            .iter()
            .any(|needle| lower.contains(needle))
        {
            gates.insert(GateKind::RelevantTestsPassed);
        }
        if [
            "visual",
            "layout",
            "animation",
            "camera",
            "geometry",
            "overlap",
            "appearance",
            "label",
        ]
        .iter()
        .any(|needle| lower.contains(needle))
        {
            gates.insert(GateKind::VisualInspectionPassed);
            gates.insert(GateKind::PreviewRenderPassed);
        }
        gates
    }

    pub fn evaluate(
        state: &AgentRunState,
        proposal: &FinishProposal,
        evidence: &[VerificationEvidence],
    ) -> Result<VerificationDecision, VerificationError> {
        if state.status != RunStatus::Verifying {
            return Err(VerificationError::InvalidStatus(state.status));
        }
        if proposal.summary.trim().is_empty() {
            return Err(VerificationError::InvalidProposal(
                "finish proposal requires a summary".into(),
            ));
        }
        let required = Self::required_gates(state);
        let changed = changed_file_hashes(state);
        let mut results = Vec::new();

        for gate in &required {
            results.push(evaluate_gate(*gate, state, proposal, evidence, &changed));
        }
        let unsupported_claims = unsupported_claims(proposal, evidence);
        if let Some(claim_gate) = results
            .iter_mut()
            .find(|result| result.gate == GateKind::ClaimsSupported)
        {
            if !unsupported_claims.is_empty() {
                claim_gate.passed = false;
                claim_gate.summary = format!(
                    "Unsupported success claims: {}",
                    unsupported_claims.join("; ")
                );
            }
        }
        let failed_gates = results
            .iter()
            .filter(|result| !result.passed)
            .cloned()
            .collect::<Vec<_>>();
        let executed = evidence
            .iter()
            .filter(|item| trusted_producer(item.kind, item.producer))
            .map(|item| format!("{:?}: {}", item.kind, item.summary))
            .collect::<Vec<_>>();
        let checks_not_run = missing_check_names(&required, evidence, &changed);
        if !failed_gates.is_empty() {
            let retry_fingerprint = fingerprint(&json!({
                "failed": failed_gates,
                "unsupported_claims": unsupported_claims,
            }));
            return Ok(VerificationDecision::Rejected(VerificationRejection {
                failed_gates,
                checks_not_run,
                unsupported_claims,
                retry_fingerprint,
            }));
        }
        Ok(VerificationDecision::Authorized(VerificationManifest {
            run_id: state.run_id.clone(),
            objective: state.objective.clone(),
            final_summary: proposal.summary.trim().into(),
            changed_files: changed.keys().cloned().collect(),
            acceptance_criteria: state.acceptance_criteria.clone(),
            gates: results,
            executed_checks: executed,
            checks_not_run,
            limitations: proposal
                .requested_verification
                .iter()
                .filter(|requested| {
                    !evidence
                        .iter()
                        .any(|item| evidence_name(item.kind) == requested.as_str())
                })
                .map(|requested| {
                    format!(
                        "Requested verification '{requested}' was not applicable or was not run."
                    )
                })
                .collect(),
            verified_at: Utc::now(),
        }))
    }

    pub fn authorize_completion(
        state: &mut AgentRunState,
        proposal: &FinishProposal,
        evidence: &[VerificationEvidence],
    ) -> Result<VerificationDecision, VerificationError> {
        let decision = Self::evaluate(state, proposal, evidence)?;
        match &decision {
            VerificationDecision::Authorized(manifest) => {
                state.completion_manifest = Some(
                    serde_json::to_value(manifest)
                        .map_err(|error| VerificationError::Serialization(error.to_string()))?,
                );
                state.verification = evidence
                    .iter()
                    .map(|item| {
                        serde_json::to_value(item)
                            .unwrap_or_else(|_| json!({"serialization_error": true}))
                    })
                    .collect();
                state
                    .transition(RunStatus::Completed, None)
                    .map_err(VerificationError::State)?;
            }
            VerificationDecision::Rejected(rejection) => {
                AgentPolicyEngine::reject_finish(state, &rejection.retry_fingerprint)
                    .map_err(VerificationError::Policy)?;
            }
        }
        Ok(decision)
    }
}

fn evaluate_gate(
    gate: GateKind,
    state: &AgentRunState,
    _proposal: &FinishProposal,
    evidence: &[VerificationEvidence],
    changed: &BTreeMap<String, String>,
) -> GateResult {
    match gate {
        GateKind::FinalChangedFilesInspected => {
            let missing = changed
                .iter()
                .filter(|(path, hash)| {
                    !evidence.iter().any(|item| {
                        item.kind == EvidenceKind::FinalFileInspection
                            && item.passed
                            && trusted_producer(item.kind, item.producer)
                            && item.path.as_deref() == Some(path.as_str())
                            && item.sha256.as_deref() == Some(hash.as_str())
                    })
                })
                .map(|(path, _)| path.clone())
                .collect::<Vec<_>>();
            gate_result(
                gate,
                missing.is_empty(),
                if missing.is_empty() {
                    "Every changed file was inspected at its final hash.".into()
                } else {
                    format!("Missing final-hash inspection: {}", missing.join(", "))
                },
                evidence,
                EvidenceKind::FinalFileInspection,
            )
        }
        GateKind::SyntaxPassed => evidence_gate(gate, EvidenceKind::SyntaxCheck, evidence),
        GateKind::ProjectCheckPassed => evidence_gate(gate, EvidenceKind::ProjectCheck, evidence),
        GateKind::RelevantTestsPassed => evidence_gate(gate, EvidenceKind::RelevantTests, evidence),
        GateKind::PreviewRenderPassed => evidence_gate(gate, EvidenceKind::PreviewRender, evidence),
        GateKind::VisualInspectionPassed => {
            evidence_gate(gate, EvidenceKind::VisualInspection, evidence)
        }
        GateKind::ObjectiveAccepted => evidence_gate(gate, EvidenceKind::SemanticReview, evidence),
        GateKind::NoFatalDiagnostics => {
            let fatal = state.diagnostics.iter().any(|item| {
                item.get("fatal").and_then(Value::as_bool).unwrap_or(false)
                    && !item
                        .get("resolved")
                        .and_then(Value::as_bool)
                        .unwrap_or(false)
            });
            GateResult {
                gate,
                passed: !fatal,
                summary: if fatal {
                    "Unresolved fatal diagnostics remain.".into()
                } else {
                    "No unresolved fatal diagnostics remain.".into()
                },
                evidence_sources: Vec::new(),
            }
        }
        GateKind::ClaimsSupported => GateResult {
            gate,
            passed: true,
            summary: "Every success claim maps to executed evidence.".into(),
            evidence_sources: Vec::new(),
        },
    }
}

fn evidence_gate(
    gate: GateKind,
    kind: EvidenceKind,
    evidence: &[VerificationEvidence],
) -> GateResult {
    let matching = evidence
        .iter()
        .filter(|item| item.kind == kind)
        .collect::<Vec<_>>();
    let passed = !matching.is_empty()
        && matching
            .iter()
            .all(|item| item.passed && trusted_producer(item.kind, item.producer));
    let summary = if matching.is_empty() {
        format!(
            "Required {} evidence was not executed.",
            evidence_name(kind)
        )
    } else if passed {
        format!("{} passed.", evidence_name(kind))
    } else {
        format!("{} produced failing evidence.", evidence_name(kind))
    };
    GateResult {
        gate,
        passed,
        summary,
        evidence_sources: matching.iter().map(|item| item.source.clone()).collect(),
    }
}

fn gate_result(
    gate: GateKind,
    passed: bool,
    summary: String,
    evidence: &[VerificationEvidence],
    kind: EvidenceKind,
) -> GateResult {
    GateResult {
        gate,
        passed,
        summary,
        evidence_sources: evidence
            .iter()
            .filter(|item| item.kind == kind)
            .map(|item| item.source.clone())
            .collect(),
    }
}

fn changed_file_hashes(state: &AgentRunState) -> BTreeMap<String, String> {
    let mut changed = BTreeMap::new();
    for change in &state.changes {
        if let (Some(path), Some(hash)) = (
            change.get("path").and_then(Value::as_str),
            change.get("after_sha256").and_then(Value::as_str),
        ) {
            changed.insert(path.into(), hash.into());
        }
    }
    changed
}

fn unsupported_claims(proposal: &FinishProposal, evidence: &[VerificationEvidence]) -> Vec<String> {
    std::iter::once(&proposal.summary)
        .chain(proposal.claimed_outcomes.iter())
        .filter(|claim| {
            let lower = claim.to_lowercase();
            let required = if lower.contains("test") {
                Some(EvidenceKind::RelevantTests)
            } else if lower.contains("visual")
                || lower.contains("overlap")
                || lower.contains("looks")
            {
                Some(EvidenceKind::VisualInspection)
            } else if lower.contains("render") || lower.contains("video") {
                Some(EvidenceKind::PreviewRender)
            } else if lower.contains("compile") || lower.contains("project check") {
                Some(EvidenceKind::ProjectCheck)
            } else if lower.contains("syntax") {
                Some(EvidenceKind::SyntaxCheck)
            } else {
                Some(EvidenceKind::SemanticReview)
            };
            required.is_some_and(|kind| {
                !evidence.iter().any(|item| {
                    item.kind == kind && item.passed && trusted_producer(item.kind, item.producer)
                })
            })
        })
        .cloned()
        .collect()
}

fn missing_check_names(
    required: &BTreeSet<GateKind>,
    evidence: &[VerificationEvidence],
    changed: &BTreeMap<String, String>,
) -> Vec<String> {
    required
        .iter()
        .filter_map(|gate| match gate {
            GateKind::FinalChangedFilesInspected if !changed.is_empty() => {
                Some("final_file_inspection")
            }
            GateKind::SyntaxPassed => Some("syntax_check"),
            GateKind::ProjectCheckPassed => Some("project_check"),
            GateKind::RelevantTestsPassed => Some("relevant_tests"),
            GateKind::PreviewRenderPassed => Some("preview_render"),
            GateKind::VisualInspectionPassed => Some("visual_inspection"),
            GateKind::ObjectiveAccepted => Some("semantic_review"),
            _ => None,
        })
        .filter(|name| {
            !evidence.iter().any(|item| {
                evidence_name(item.kind) == *name
                    && trusted_producer(item.kind, item.producer)
                    && (item.kind != EvidenceKind::FinalFileInspection
                        || changed.iter().all(|(path, hash)| {
                            evidence.iter().any(|candidate| {
                                candidate.kind == EvidenceKind::FinalFileInspection
                                    && trusted_producer(candidate.kind, candidate.producer)
                                    && candidate.path.as_deref() == Some(path)
                                    && candidate.sha256.as_deref() == Some(hash)
                            })
                        }))
            })
        })
        .map(str::to_string)
        .collect()
}

fn evidence_name(kind: EvidenceKind) -> &'static str {
    match kind {
        EvidenceKind::FinalFileInspection => "final_file_inspection",
        EvidenceKind::SyntaxCheck => "syntax_check",
        EvidenceKind::ProjectCheck => "project_check",
        EvidenceKind::RelevantTests => "relevant_tests",
        EvidenceKind::PreviewRender => "preview_render",
        EvidenceKind::VisualInspection => "visual_inspection",
        EvidenceKind::SemanticReview => "semantic_review",
    }
}

fn trusted_producer(kind: EvidenceKind, producer: EvidenceProducer) -> bool {
    if producer == EvidenceProducer::TestHarness {
        return true;
    }
    match kind {
        EvidenceKind::FinalFileInspection | EvidenceKind::VisualInspection => {
            matches!(
                producer,
                EvidenceProducer::Desktop | EvidenceProducer::Verifier
            )
        }
        EvidenceKind::SyntaxCheck
        | EvidenceKind::ProjectCheck
        | EvidenceKind::RelevantTests
        | EvidenceKind::PreviewRender => producer == EvidenceProducer::Sidecar,
        EvidenceKind::SemanticReview => producer == EvidenceProducer::Verifier,
    }
}

fn fingerprint(value: &Value) -> String {
    hex::encode(Sha256::digest(
        serde_json::to_vec(value).unwrap_or_default(),
    ))
}
