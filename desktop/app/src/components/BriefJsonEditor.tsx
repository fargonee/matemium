import type { ProjectFile } from "../utils/workspacePrefs";

interface BriefJsonEditorProps {
  file: "passport" | "roadmap";
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
}

type JsonObject = Record<string, unknown>;

function encode(value: JsonObject): string {
  return `${JSON.stringify(value, null, 2)}\n`;
}

export function BriefJsonEditor({ file, value, onChange, readOnly = false }: BriefJsonEditorProps) {
  let data: JsonObject;
  try {
    data = JSON.parse(value) as JsonObject;
  } catch {
    return (
      <div className="brief-json-error">
        <strong>This document contains invalid JSON.</strong>
        <p>{file === "roadmap" ? "Ask the AI to repair the roadmap data." : "Repair it in the source editor before using the structured form."}</p>
        <textarea value={value} onChange={(event) => onChange(event.target.value)} readOnly={readOnly || file === "roadmap"} spellCheck={false} />
      </div>
    );
  }

  const setField = (key: string, next: unknown) => onChange(encode({ ...data, [key]: next }));
  if (file === "passport") {
    const fields: Array<{ key: string; label: string; type?: string }> = [
      { key: "title", label: "Project title" },
      { key: "status", label: "Status" },
      { key: "audience", label: "Audience" },
      { key: "learning_goal", label: "Learning goal" },
      { key: "duration_seconds", label: "Target duration", type: "number" },
      { key: "orientation", label: "Orientation" },
      { key: "language", label: "Language" },
      { key: "tone", label: "Tone" },
    ];
    return <div className="brief-form"><div className="brief-form-grid">
      {fields.map(({ key, label, type }) => <label key={key} className={key === "learning_goal" ? "wide" : ""}>
        <span>{label}</span>
        <input type={type ?? "text"} value={String(data[key] ?? "")} readOnly={readOnly} onChange={(event) => setField(key, type === "number" ? Number(event.target.value) : event.target.value)} />
      </label>)}
      <label className="wide"><span>Constraints (one per line)</span><textarea value={Array.isArray(data.constraints) ? data.constraints.join("\n") : ""} readOnly={readOnly} onChange={(event) => setField("constraints", event.target.value.split("\n").map((line) => line.trim()).filter(Boolean))} /></label>
    </div></div>;
  }

  const phases = Array.isArray(data.phases) ? data.phases as JsonObject[] : [];
  const currentPhase = String(data.current_phase ?? "");
  const phaseProgress = (phase: JsonObject) => {
    const value = Number(phase.progress ?? 0);
    return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
  };
  const overallProgress = phases.length > 0
    ? Math.round(phases.reduce((total, phase) => total + phaseProgress(phase), 0) / phases.length)
    : 0;
  const completedPhases = phases.filter((phase) => phase.status === "done").length;
  const currentPhaseTitle = String(
    phases.find((phase) => String(phase.id) === currentPhase)?.title ?? "Not assigned",
  );
  return <div className="brief-form roadmap-form">
    <header className="roadmap-overview">
      <div className="roadmap-overview-copy">
        <span className="roadmap-kicker">Production roadmap</span>
        <strong>{overallProgress}% complete</strong>
        <span>{completedPhases} of {phases.length} phases delivered</span>
      </div>
      <div className="roadmap-overall-meter" aria-label={`Overall progress ${overallProgress}%`}>
        <span style={{ width: `${overallProgress}%` }} />
      </div>
      <div className="roadmap-current-summary"><span>Working point</span><strong>{currentPhaseTitle}</strong></div>
    </header>

    <div className="roadmap-route">{phases.map((phase, index) => {
      const phaseId = String(phase.id ?? `phase-${index + 1}`);
      const status = String(phase.status ?? "todo");
      const progress = phaseProgress(phase);
      const isCurrent = phaseId === currentPhase;
      return <section className={`roadmap-step roadmap-step-${status} ${isCurrent ? "is-current" : ""}`} key={phaseId}>
        <article className="roadmap-island">
          <div className="roadmap-island-topline">
            <span className="roadmap-phase-number">Phase {String(index + 1).padStart(2, "0")}</span>
            {isCurrent ? <span className="roadmap-current-badge">Current</span> : null}
            <span className={`roadmap-status-badge roadmap-status-${status}`}>{status === "in_progress" ? "In progress" : status === "done" ? "Done" : "To do"}</span>
          </div>
          <h3 className="roadmap-phase-title">{String(phase.title ?? "Untitled phase")}</h3>
          <label className="roadmap-progress-label"><span>Completion</span><output>{progress}%</output></label>
          <div className="roadmap-progress">
            <span className="roadmap-progress-track" aria-hidden><span style={{ width: `${progress}%` }} /></span>
          </div>
          <p className={`roadmap-phase-notes ${phase.notes ? "" : "is-empty"}`}>{String(phase.notes || "No phase notes")}</p>
        </article>
        <div className="roadmap-node" title={isCurrent ? "Current working phase" : undefined} aria-label={isCurrent ? "Current working phase" : undefined}>
          <span>{status === "done" ? "✓" : index + 1}</span>
        </div>
      </section>;
    })}</div>
  </div>;
}

export const STRUCTURED_BRIEF_FILES: ProjectFile[] = ["passport", "roadmap"];
