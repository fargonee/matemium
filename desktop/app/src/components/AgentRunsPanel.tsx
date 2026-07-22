import { useMemo, useState } from "react";

import type { AgentRunState, AgentStreamEvent } from "../api/types";

interface Props {
  runs: AgentRunState[];
  selectedRunId?: string | null;
  events: AgentStreamEvent[];
  busy?: boolean;
  onSelect: (runId: string) => void;
  onCancel: (runId: string) => Promise<void> | void;
  onResume: (runId: string) => Promise<void> | void;
  onProvideInput: (runId: string, content: string) => Promise<void> | void;
  onApprove: (runId: string, actionId: string, approved: boolean) => Promise<void> | void;
}

const TERMINAL = new Set(["completed", "failed", "cancelled"]);
const ACTIVE = new Set(["received", "understanding", "planning", "executing", "verifying", "recovering"]);

export function agentRunStatusLabel(status: AgentRunState["status"]): string {
  switch (status) {
    case "completed": return "Completed and verified";
    case "blocked": return "Waiting for input";
    case "failed": return "Failed honestly";
    case "cancelled": return "Cancelled";
    case "verifying": return "Verifying evidence";
    case "recovering": return "Recovering";
    default: return status[0].toUpperCase() + status.slice(1);
  }
}

function eventLabel(type: string): string {
  return type
    .replace(/^agent_/, "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function eventTone(event: AgentStreamEvent): "ok" | "warn" | "error" | "info" {
  const type = event.event_type.toLowerCase();
  const status = String(event.payload.status ?? event.payload.outcome ?? "").toLowerCase();
  if (type.includes("approval") || type.includes("blocked") || type.includes("budget")) return "warn";
  if (type.includes("fail") || type.includes("error") || status.includes("fail") || status.includes("denied")) return "error";
  if (type.includes("complete") || type.includes("verified") || status.includes("pass") || status.includes("approved")) return "ok";
  return "info";
}

function statusTone(status: AgentRunState["status"]): "ok" | "warn" | "error" | "info" {
  if (status === "completed") return "ok";
  if (status === "failed" || status === "cancelled") return "error";
  if (status === "blocked" || status === "recovering") return "warn";
  return "info";
}

function compactValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(compactValue).filter(Boolean).join(", ");
  return "";
}

function payloadText(event: AgentStreamEvent): string {
  const payload = event.payload;
  return (
    compactValue(payload.summary) ||
    compactValue(payload.rationale) ||
    compactValue(payload.message) ||
    compactValue(payload.command) ||
    compactValue(payload.path) ||
    compactValue(payload.file) ||
    "Event recorded"
  );
}

function payloadList(payload: Record<string, unknown>, keys: string[]): string[] {
  for (const key of keys) {
    const value = payload[key];
    if (Array.isArray(value)) return value.map(compactValue).filter(Boolean);
    const text = compactValue(value);
    if (text) return [text];
  }
  return [];
}

function collectEvidence(events: AgentStreamEvent[]) {
  const commands: string[] = [];
  const files: string[] = [];
  const checks: string[] = [];

  events.forEach((event) => {
    commands.push(...payloadList(event.payload, ["command", "commands", "shell_command"]));
    files.push(...payloadList(event.payload, ["file", "files", "path", "paths", "edited_files"]));
    checks.push(...payloadList(event.payload, ["check", "checks", "test", "tests", "verification", "validator"]));
  });

  return {
    commands: Array.from(new Set(commands)).slice(0, 8),
    files: Array.from(new Set(files)).slice(0, 10),
    checks: Array.from(new Set(checks)).slice(0, 8),
  };
}

function formatCount(value: unknown): string {
  if (typeof value === "number") return value.toLocaleString();
  return "0";
}

export function AgentRunsPanel({
  runs,
  selectedRunId,
  events,
  busy = false,
  onSelect,
  onCancel,
  onResume,
  onProvideInput,
  onApprove,
}: Props) {
  const [input, setInput] = useState("");
  const selected = runs.find((run) => run.run_id === selectedRunId) ?? runs[0];
  const pendingApprovals = useMemo(() => {
    const recorded = new Set(
      events
        .filter((event) => event.event_type === "approval_recorded")
        .map((event) => String(event.payload.action_id ?? "")),
    );
    return events.filter(
      (event) =>
        event.event_type === "approval_requested" &&
        !recorded.has(String(event.payload.action_id ?? "")),
    );
  }, [events]);
  const evidence = useMemo(() => collectEvidence(events), [events]);
  const liveEvents = events.slice(-5).reverse();

  return (
    <section className="agent-runs-panel" aria-label="Autonomous agent runs">
      <aside className="agent-run-history">
        <div className="agent-history-head">
          <h3>Sessions</h3>
          <span>{runs.length}</span>
        </div>
        {runs.length === 0 && (
          <p role="status" className="agent-empty-state">
            No durable agent sessions are stored for this project yet.
          </p>
        )}
        <div className="agent-run-list">
          {runs.map((run) => (
            <button
              key={run.run_id}
              type="button"
              className={`agent-run-item ${run.run_id === selected?.run_id ? "active" : ""}`}
              onClick={() => onSelect(run.run_id)}
            >
              <span className={`agent-status-dot ${statusTone(run.status)} ${ACTIVE.has(run.status) ? "live" : ""}`} />
              <span className="agent-run-item-copy">
                <strong>{run.objective}</strong>
                <small>{agentRunStatusLabel(run.status)} · {run.sequence} events</small>
              </span>
            </button>
          ))}
        </div>
      </aside>

      {selected && (
        <div className="agent-run-detail">
          <header className="agent-run-hero">
            <div>
              <span className="agent-eyebrow">Agent command center</span>
              <h3>{selected.objective}</h3>
              <div className="agent-run-meta">
                <span className={`agent-chip ${statusTone(selected.status)}`}>{agentRunStatusLabel(selected.status)}</span>
                <span className="agent-chip">Runtime {selected.runtime_version}</span>
                <span className="agent-chip">{events.length} trace events</span>
              </div>
            </div>
            <div className="agent-run-actions">
              {!TERMINAL.has(selected.status) && (
                <button disabled={busy} type="button" className="btn btn-danger" onClick={() => void onCancel(selected.run_id)}>
                  Stop
                </button>
              )}
              {selected.status === "recovering" && (
                <button disabled={busy} type="button" className="btn btn-primary" onClick={() => void onResume(selected.run_id)}>
                  Revalidate
                </button>
              )}
            </div>
          </header>

          {pendingApprovals.length > 0 && (
            <section className="agent-approval-stack" aria-label="Pending approvals">
              {pendingApprovals.map((event) => {
                const actionId = String(event.payload.action_id ?? "");
                return (
                  <div key={event.event_id} className="agent-approval" role="group" aria-label="Approval request">
                    <div>
                      <strong>Approval required</strong>
                      <p>{String(event.payload.summary ?? "The agent requested permission before continuing.")}</p>
                    </div>
                    <div className="agent-approval-actions">
                      <button disabled={busy} type="button" className="btn btn-primary" onClick={() => void onApprove(selected.run_id, actionId, true)}>Approve</button>
                      <button disabled={busy} type="button" className="btn" onClick={() => void onApprove(selected.run_id, actionId, false)}>Deny</button>
                    </div>
                  </div>
                );
              })}
            </section>
          )}

          <div className="agent-metrics-grid">
            <div className="agent-metric">
              <span>Plan</span>
              <strong>{selected.plan.filter((step) => step.status === "completed").length}/{selected.plan.length}</strong>
            </div>
            <div className="agent-metric">
              <span>Files Seen</span>
              <strong>{evidence.files.length}</strong>
            </div>
            <div className="agent-metric">
              <span>Commands</span>
              <strong>{evidence.commands.length}</strong>
            </div>
            <div className="agent-metric">
              <span>Tokens</span>
              <strong>{formatCount(selected.usage.tokens ?? selected.usage.total_tokens)}</strong>
            </div>
          </div>

          <section className="agent-workbench-grid">
            <div className="agent-plan-panel">
              <div className="agent-section-head">
                <h4>Plan</h4>
                <span>{selected.acceptance_criteria.length} acceptance checks</span>
              </div>
              <ol className="agent-plan-list">
                {selected.plan.map((step) => (
                  <li key={step.id} className={`agent-plan-step ${step.status.replaceAll("_", "-")}`}>
                    <span className="agent-plan-marker" />
                    <div>
                      <strong>{step.text}</strong>
                      <small>{step.status.replaceAll("_", " ")}</small>
                    </div>
                  </li>
                ))}
              </ol>
              {selected.acceptance_criteria.length > 0 && (
                <details className="agent-disclosure">
                  <summary>Acceptance criteria</summary>
                  <ul>
                    {selected.acceptance_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}
                  </ul>
                </details>
              )}
            </div>

            <div className="agent-evidence-panel">
              <div className="agent-section-head">
                <h4>Evidence</h4>
                <span>Inspectable actions</span>
              </div>
              <EvidenceGroup title="Files touched or inspected" empty="No file paths recorded yet." items={evidence.files} />
              <EvidenceGroup title="Commands run" empty="No shell commands recorded yet." items={evidence.commands} mono />
              <EvidenceGroup title="Validation" empty="No validation checks recorded yet." items={evidence.checks} />
            </div>
          </section>

          {selected.terminal_reason && <p className="agent-terminal-reason" role="status">{selected.terminal_reason}</p>}

          {selected.status === "blocked" && (
            <form
              className="agent-input-card"
              onSubmit={(event) => {
                event.preventDefault();
                if (input.trim()) void onProvideInput(selected.run_id, input.trim());
              }}
            >
              <label>
                Required input
                <textarea value={input} maxLength={16_384} onChange={(event) => setInput(event.target.value)} />
              </label>
              <button type="submit" className="btn btn-primary" disabled={busy || !input.trim()}>Continue run</button>
            </form>
          )}

          <section className="agent-timeline-panel">
            <div className="agent-section-head">
              <h4>Live Action Timeline</h4>
              <span>{events.length} events</span>
            </div>
            <ol className="agent-event-ledger">
              {events.length === 0 && <li className="agent-empty-state">No versioned events recorded for this run.</li>}
              {liveEvents.map((event) => (
                <li key={event.event_id} className={`agent-event-card ${eventTone(event)}`}>
                  <div className="agent-event-main">
                    <span className="agent-event-sequence">#{event.sequence}</span>
                    <div>
                      <strong>{eventLabel(event.event_type)}</strong>
                      <p>{payloadText(event)}</p>
                    </div>
                  </div>
                  <details className="agent-event-details">
                    <summary>Inspect payload</summary>
                    <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                  </details>
                </li>
              ))}
            </ol>
          </section>

          {(selected.completion_manifest || Object.keys(selected.budgets).length > 0) && (
            <section className="agent-manifest-panel">
              <details className="agent-disclosure">
                <summary>Verification manifest and budgets</summary>
                <pre>{JSON.stringify({ manifest: selected.completion_manifest, budgets: selected.budgets, usage: selected.usage }, null, 2)}</pre>
              </details>
            </section>
          )}
        </div>
      )}
    </section>
  );
}

function EvidenceGroup({
  title,
  empty,
  items,
  mono = false,
}: {
  title: string;
  empty: string;
  items: string[];
  mono?: boolean;
}) {
  return (
    <div className="agent-evidence-group">
      <h5>{title}</h5>
      {items.length === 0 ? (
        <p>{empty}</p>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item} className={mono ? "mono" : undefined}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
