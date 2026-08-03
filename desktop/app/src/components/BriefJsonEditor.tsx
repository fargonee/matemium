import type { CSSProperties } from "react";
import type { ProjectFile } from "../utils/workspacePrefs";

interface BriefJsonEditorProps {
  file: "passport" | "roadmap";
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
}

type JsonObject = Record<string, unknown>;
type RoadmapPreviewPhase = {
  id: string;
  title: string;
  notes: string;
  route: RoadmapRoute;
  locked: true;
};

type RoadmapRoute = "mute_video" | "tts" | "custom_audio";

const ROUTE_META: Record<RoadmapRoute, { label: string; eyebrow: string; description: string; glyph: string }> = {
  mute_video: { label: "Mute film", eyebrow: "Visual-first", description: "A finished mathematical film, ready for your own sound.", glyph: "◇" },
  tts: { label: "Voice synthesis", eyebrow: "End-to-end TTS", description: "Narration, timing, animation, and final assembly in one journey.", glyph: "◉" },
  custom_audio: { label: "Custom voice", eyebrow: "Audio-led", description: "The approved performance becomes the clock for every visual.", glyph: "≈" },
};

function encode(value: JsonObject): string {
  return `${JSON.stringify(value, null, 2)}\n`;
}

const LOCKED_ROADMAP_PREVIEW: RoadmapPreviewPhase[] = [
  { id: "preview-mute-video-tape-content", route: "mute_video", title: "Tape content", notes: "Approve exactly what appears on the mathematical reasoning tape.", locked: true },
  { id: "preview-mute-video-orchestration", route: "mute_video", title: "Orchestration", notes: "Approve the world, tapes, camera, reveals, transitions, and pacing intent.", locked: true },
  { id: "preview-mute-video-authoring", route: "mute_video", title: "Scene authoring", notes: "Create scenes.py and helpers.py from approved creative artifacts.", locked: true },
  { id: "preview-mute-video-render-repair", route: "mute_video", title: "Render and visual repair", notes: "Render, inspect visual evidence, and fix unexpected behavior.", locked: true },
  { id: "preview-mute-video-delivery", route: "mute_video", title: "Mute video delivery", notes: "Deliver the validated animation without a final audio track.", locked: true },
  { id: "preview-tts-tape-content", route: "tts", title: "Tape content", notes: "Approve exactly what appears on the mathematical reasoning tape.", locked: true },
  { id: "preview-tts-orchestration", route: "tts", title: "Orchestration", notes: "Approve the world, tapes, camera, reveals, transitions, and pacing intent.", locked: true },
  { id: "preview-tts-narration", route: "tts", title: "TTS narration and provisional timing", notes: "Write narration, optional style direction, and deliberate provisional timing.", locked: true },
  { id: "preview-tts-authoring", route: "tts", title: "Scene authoring", notes: "Create scenes.py and helpers.py against approved narration timing.", locked: true },
  { id: "preview-tts-render-repair", route: "tts", title: "Render and visual repair", notes: "Render, inspect visual evidence, and repair the animation.", locked: true },
  { id: "preview-tts-timing-regulation", route: "tts", title: "Final timing regulation", notes: "Regulate authoring and narration timing against the validated render before TTS.", locked: true },
  { id: "preview-tts-generation", route: "tts", title: "TTS generation", notes: "Generate and approve the final narration audio.", locked: true },
  { id: "preview-tts-final-assembly", route: "tts", title: "Final assembly", notes: "Attach approved audio without avoidable video quality loss.", locked: true },
  { id: "preview-custom-audio-tape-content", route: "custom_audio", title: "Tape content", notes: "Approve exactly what appears on the mathematical reasoning tape.", locked: true },
  { id: "preview-custom-audio-orchestration", route: "custom_audio", title: "Orchestration", notes: "Approve the world, tapes, camera, reveals, transitions, and pacing intent.", locked: true },
  { id: "preview-custom-audio-specification", route: "custom_audio", title: "Custom audio specification", notes: "Define narration, holds, pace, silence, emphasis, and acceptance criteria.", locked: true },
  { id: "preview-custom-audio-generation", route: "custom_audio", title: "Custom audio generation", notes: "Generate distinguishable audio attempts through the configured external service.", locked: true },
  { id: "preview-custom-audio-transcription", route: "custom_audio", title: "Transcription and validation", notes: "Extract fresh transcript/timestamps and regenerate until the audio is approved.", locked: true },
  { id: "preview-custom-audio-reconciliation", route: "custom_audio", title: "Post-audio content reconciliation", notes: "Adapt tape content and orchestration to the verified audio wording and timing.", locked: true },
  { id: "preview-custom-audio-authoring", route: "custom_audio", title: "Scene authoring", notes: "Create scenes.py and helpers.py only after audio reconciliation.", locked: true },
  { id: "preview-custom-audio-render-repair", route: "custom_audio", title: "Render and synchronization repair", notes: "Render against approved timing and repair visual or synchronization defects.", locked: true },
  { id: "preview-custom-audio-final-assembly", route: "custom_audio", title: "Final assembly", notes: "Attach approved audio without avoidable video quality loss.", locked: true },
];

const SHARED_PHASES = [
  { id: "project_creation", title: "Project creation", notes: "The workspace and initial idea are preserved." },
  { id: "description", title: "Project description", notes: "Settle the rare-changing description through collaboration." },
  { id: "passport", title: "Passport and production path", notes: "Resolve the production identity and explicitly select a production path." },
];

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
    const fields: Array<{ key: string; label: string; type?: string; wide?: boolean }> = [
      { key: "title", label: "Project title" },
      { key: "status", label: "Status", type: "status" },
      { key: "objective", label: "Objective", type: "textarea", wide: true },
      { key: "central_message", label: "Central message", type: "textarea", wide: true },
      { key: "audience", label: "Audience" },
      { key: "assumed_knowledge", label: "Assumed knowledge" },
      { key: "viewer_takeaway", label: "Viewer takeaway", type: "textarea", wide: true },
      { key: "platform", label: "Platform" },
      { key: "duration_seconds", label: "Target duration", type: "number" },
      { key: "orientation", label: "Orientation", type: "orientation" },
      { key: "language", label: "Language" },
      { key: "mathematical_depth", label: "Mathematical depth" },
      { key: "visual_direction", label: "Visual direction", type: "textarea", wide: true },
      { key: "tone", label: "Tone" },
      { key: "pacing", label: "Pacing" },
      { key: "production_path", label: "Production path", type: "production_path", wide: true },
      { key: "audio_direction", label: "Audio direction", type: "textarea", wide: true },
    ];
    return <div className="brief-form"><div className="brief-form-grid">
      {fields.map(({ key, label, type, wide }) => <label key={key} className={wide ? "wide" : ""}>
        <span>{label}</span>
        {type === "textarea" ? <textarea value={String(data[key] ?? "")} readOnly={readOnly} onChange={(event) => setField(key, event.target.value)} />
          : type === "status" ? <select value={String(data[key] ?? "discovery")} disabled={readOnly} onChange={(event) => setField(key, event.target.value)}><option value="discovery">Discovery</option><option value="ready">Ready</option><option value="production">Production</option><option value="review">Review</option><option value="complete">Complete</option></select>
            : type === "orientation" ? <select value={String(data[key] ?? "portrait")} disabled={readOnly} onChange={(event) => setField(key, event.target.value)}><option value="portrait">Portrait</option><option value="landscape">Landscape</option></select>
              : type === "production_path" ? <select value={String(data[key] ?? "")} disabled={readOnly} onChange={(event) => setField(key, event.target.value || null)}><option value="">Choose with the AI…</option><option value="mute_video">Mute video — add audio yourself</option><option value="tts">End-to-end with TTS</option><option value="custom_audio">End-to-end with custom audio</option></select>
              : <input type={type ?? "text"} value={String(data[key] ?? "")} readOnly={readOnly} onChange={(event) => setField(key, type === "number" ? Number(event.target.value) : event.target.value)} />}
      </label>)}
      {([ ["required_elements", "Required elements"], ["avoid", "Avoid"], ["factual_constraints", "Factual constraints"], ["success_criteria", "Success criteria"], ["assumptions", "AI assumptions"] ] as const).map(([key, label]) => <label className="wide" key={key}><span>{label} (one per line)</span><textarea value={Array.isArray(data[key]) ? data[key].join("\n") : ""} readOnly={readOnly} onChange={(event) => setField(key, event.target.value.split("\n").map((line) => line.trim()).filter(Boolean))} /></label>)}
    </div></div>;
  }

  const savedPhases = Array.isArray(data.phases) ? data.phases as JsonObject[] : [];
  const savedById = new Map(savedPhases.map((phase) => [String(phase.id), phase]));
  const canonicalPhase = (phase: { id: string; title: string; notes: string }): JsonObject => {
    const saved = savedById.get(phase.id) ?? {};
    const savedStatus = String(saved.status ?? (phase.id === "project_creation" ? "done" : "todo"));
    const status = savedStatus === "complete" ? "done" : savedStatus === "pending" ? "todo" : savedStatus;
    return {
      ...saved,
      id: phase.id,
      title: phase.title,
      notes: phase.notes,
      status,
      progress: saved.progress ?? (status === "done" ? 100 : 0),
    };
  };
  const trunkPhases = SHARED_PHASES.map(canonicalPhase);
  const canonicalBranch = data.production_path === "mute_video" || data.production_path === "tts" || data.production_path === "custom_audio"
    ? LOCKED_ROADMAP_PREVIEW.filter((phase) => phase.route === data.production_path).map(canonicalPhase)
    : [];
  const phases = [...trunkPhases, ...canonicalBranch];
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
  const productionPath = data.production_path === "mute_video" ? "Mute video" : data.production_path === "tts" ? "TTS" : data.production_path === "custom_audio" ? "Custom audio" : "Path not selected";
  const blockers = Array.isArray(data.blockers) ? data.blockers.map(String) : [];
  const invalidated = Array.isArray(data.invalidated_phases) ? data.invalidated_phases.map(String) : [];
  const hasConcretePath = data.production_path === "mute_video" || data.production_path === "tts" || data.production_path === "custom_audio";
  const concretePath = hasConcretePath ? data.production_path as RoadmapRoute : null;
  const actualBranch = canonicalBranch;
  const routePhases = (route: RoadmapRoute): Array<JsonObject | RoadmapPreviewPhase> => {
    if (route === concretePath) return actualBranch;
    return LOCKED_ROADMAP_PREVIEW.filter((phase) => phase.route === route);
  };
  const statusLabel = (status: string) => status === "in_progress" ? "In progress" : status === "done" ? "Complete" : status === "locked" ? "Awaiting decision" : "Coming next";
  const renderPhase = (phase: JsonObject | RoadmapPreviewPhase, index: number, _route?: RoadmapRoute) => {
    const phaseId = String(phase.id ?? `phase-${index + 1}`);
    const isLocked = "locked" in phase && phase.locked === true;
    const status = isLocked ? "locked" : String((phase as JsonObject).status ?? "todo");
    const progress = isLocked ? 0 : phaseProgress(phase as JsonObject);
    const isCurrent = phaseId === currentPhase;
    return <div
      className={`roadmap-cloud roadmap-cloud-${status} ${isCurrent ? "is-current" : ""}`}
      key={phaseId}
      aria-label={`${String(phase.title ?? "Untitled phase")}, ${statusLabel(status)}`}
      title={String(phase.title ?? "Untitled phase")}
      style={{ "--phase-progress": `${progress * 3.6}deg`, "--phase-index": index } as CSSProperties}
    >
      <span className="roadmap-cloud-icon" aria-hidden>{String(index + 1).padStart(2, "0")}</span>
      <span className="roadmap-cloud-copy">
        <strong>{String(phase.title ?? "Untitled phase")}</strong>
        <p>{String(phase.notes || "No description added yet.")}</p>
      </span>
    </div>;
  };
  return <div className="brief-form roadmap-form">
    <header className="roadmap-overview">
      <div className="roadmap-overview-copy">
        <span className="roadmap-kicker">Production roadmap</span>
        <strong>Project phases</strong>
        <span>{productionPath} <i /> {completedPhases} of {phases.length} phases complete</span>
      </div>
      <div className="roadmap-overall-progress" aria-label={`Overall progress ${overallProgress}%`} style={{ "--overall-progress": `${overallProgress * 3.6}deg` } as CSSProperties}>
        <span><strong>{overallProgress}</strong><small>%</small></span>
        <p>Overall<br />progress</p>
      </div>
      <div className="roadmap-current-summary"><span>Current phase</span><strong>{currentPhaseTitle}</strong><i aria-hidden /></div>
    </header>

    <main className="roadmap-world">
        <section className="roadmap-trunk" aria-label="Foundation phases">
          <div className="roadmap-trunk-heading"><span>Shared foundation</span><strong>Every project begins here</strong></div>
          <div className="roadmap-trunk-line" aria-hidden><i /></div>
          {trunkPhases.map((phase, index) => <div className="roadmap-trunk-stop" key={String(phase.id)}>{renderPhase(phase, index)}</div>)}
          <div className="roadmap-fork" aria-hidden><span /><span /><span /><i /></div>
        </section>

        <section className={`roadmap-branches ${concretePath ? "has-chosen-route" : "is-unresolved"}`} aria-label="Production paths">
          <div className="roadmap-branches-heading"><span>Production branches</span><strong>Continue along one path</strong></div>
        {(["mute_video", "tts", "custom_audio"] as RoadmapRoute[]).map((route) => {
          const meta = ROUTE_META[route];
          const isChosen = route === concretePath;
          return <article className={`roadmap-branch roadmap-branch-${route} ${isChosen ? "is-chosen" : "is-dormant"}`} key={route}>
            <header className="roadmap-branch-heading">
              <div className="roadmap-route-enter">
                <span className="roadmap-branch-glyph" aria-hidden>{meta.glyph}</span>
                <span><small>{meta.eyebrow}</small><strong>{meta.label}</strong><span className="roadmap-route-description">{meta.description}</span></span>
              </div>
              <em>{isChosen ? "Selected path" : concretePath ? "Not selected" : "Awaiting decision"}</em>
            </header>
            <div className="roadmap-branch-stream">
              <span className="roadmap-branch-line" aria-hidden />
              {routePhases(route).map((phase, index) => renderPhase(phase, index + 3, route))}
            </div>
          </article>;
        })}
        </section>
    </main>

    {blockers.length > 0 || invalidated.length > 0 ? <section className="roadmap-signals">
      {blockers.length > 0 ? <div><strong>Production is waiting</strong><ul>{blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul></div> : null}
      {invalidated.length > 0 ? <div><strong>Needs reconciliation</strong><p>{invalidated.join(", ")}</p></div> : null}
    </section> : null}
  </div>;
}

export const STRUCTURED_BRIEF_FILES: ProjectFile[] = ["passport", "roadmap"];
