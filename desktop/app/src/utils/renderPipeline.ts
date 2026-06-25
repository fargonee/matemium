import type { SidecarEventPayload } from "../api/types";

export type PipelinePhase =
  | "idle"
  | "linting"
  | "checking"
  | "compiling"
  | "layout"
  | "rendering"
  | "complete"
  | "cancelled"
  | "error";

export type PipelineStepId = "compile" | "layout" | "render" | "finish";

export interface RenderPipelineState {
  phase: PipelinePhase;
  jobKind: "idle" | "lint" | "render";
  label: string | null;
  scene: string | null;
  quality: string | null;
  orientation: string | null;
  elementCount: number | null;
  durationEstimate: number | null;
  progress: number;
  message: string | null;
  renderSection: string | null;
  partialIndex: number | null;
  partialTotal: number | null;
  completedPartialCount: number;
  encodingPartialIndex: number | null;
  frame: number | null;
  totalFrames: number | null;
  segmentProgress: number | null;
  /** Per-segment source: cache hit (yellow) vs fresh encode (blue). */
  partialSegmentSources: Array<"cache" | "encode">;
  startedAt: number | null;
  completedAt: number | null;
  error: string | null;
  videoPath: string | null;
}

export const INITIAL_PIPELINE_STATE: RenderPipelineState = {
  phase: "idle",
  jobKind: "idle",
  label: null,
  scene: null,
  quality: null,
  orientation: null,
  elementCount: null,
  durationEstimate: null,
  progress: 0,
  message: null,
  renderSection: null,
  partialIndex: null,
  partialTotal: null,
  completedPartialCount: 0,
  encodingPartialIndex: null,
  frame: null,
  totalFrames: null,
  segmentProgress: null,
  partialSegmentSources: [],
  startedAt: null,
  completedAt: null,
  error: null,
  videoPath: null,
};

export const PIPELINE_STEPS: Array<{
  id: PipelineStepId;
  title: string;
  caption: string;
}> = [
  { id: "compile", title: "Compile", caption: "Import scene & build DSL" },
  { id: "layout", title: "Layout", caption: "Measure timeline & duration" },
  { id: "render", title: "Render", caption: "Manim encode & export" },
  { id: "finish", title: "Complete", caption: "Preview ready" },
];

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function asBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function isSegmentBeginMessage(message: string | null): boolean {
  if (!message) return false;
  return (
    message.startsWith("Rendering segment") || message.startsWith("Using cached segment")
  );
}

function isSegmentDoneMessage(message: string | null): boolean {
  if (!message) return false;
  return message.startsWith("Finished segment") || message.startsWith("Cached segment");
}

function isCachedSegmentBeginMessage(message: string | null): boolean {
  return message?.startsWith("Using cached segment") ?? false;
}

/** Progress within the active partial movie only (frame encode), not across all partials. */
function currentPartialMovieProgress(
  state: RenderPipelineState,
  input: {
    section: string | null;
    frame: number | null;
    totalFrames: number | null;
    eventMessage: string | null;
    partialCached: boolean | null;
    encodingPartialIndex: number | null;
    sameEncodingSegment: boolean;
  },
): number {
  if (input.section === "combine") {
    return 0;
  }

  if (isSegmentDoneMessage(input.eventMessage)) {
    return 100;
  }

  if (
    isCachedSegmentBeginMessage(input.eventMessage) ||
    (input.partialCached === true && isSegmentBeginMessage(input.eventMessage))
  ) {
    return 100;
  }

  if (isSegmentBeginMessage(input.eventMessage)) {
    if (input.frame !== null && input.totalFrames !== null && input.totalFrames > 0) {
      return Math.round(Math.min(100, (input.frame / input.totalFrames) * 100));
    }
    return 0;
  }

  if (
    input.frame !== null &&
    input.totalFrames !== null &&
    input.totalFrames > 0 &&
    input.encodingPartialIndex !== null
  ) {
    const raw = Math.round(Math.min(100, (input.frame / input.totalFrames) * 100));
    return input.sameEncodingSegment
      ? Math.max(state.segmentProgress ?? 0, raw)
      : raw;
  }

  if (input.sameEncodingSegment && input.encodingPartialIndex !== null) {
    return state.segmentProgress ?? 0;
  }

  return 0;
}

function recordPartialSegmentSource(
  sources: Array<"cache" | "encode">,
  index: number,
  cached: boolean,
): Array<"cache" | "encode"> {
  if (index <= 0) return sources;
  const next = sources.slice();
  const slot = index - 1;
  const source: "cache" | "encode" = cached ? "cache" : "encode";
  if (slot >= next.length) {
    next.length = slot + 1;
  }
  next[slot] = source;
  return next;
}

function stepIndex(phase: PipelinePhase): number {
  switch (phase) {
    case "compiling":
      return 0;
    case "layout":
      return 1;
    case "rendering":
      return 2;
    case "complete":
      return 3;
    case "checking":
      return 0;
    default:
      return -1;
  }
}

function failureStepIndex(state: RenderPipelineState): number {
  if (state.progress < 20) return 0;
  if (state.progress < 36) return 1;
  if (state.progress < 45) return 2;
  return 3;
}

export function stepStatus(
  stepId: PipelineStepId,
  state: RenderPipelineState,
): "pending" | "active" | "done" | "error" {
  if (state.phase === "error") {
    const idx = PIPELINE_STEPS.findIndex((step) => step.id === stepId);
    const failIdx = failureStepIndex(state);
    if (idx < failIdx) return "done";
    if (idx === failIdx) return "error";
    return "pending";
  }
  if (state.phase === "idle" || state.phase === "linting") return "pending";
  if (state.phase === "complete") return "done";

  const idx = PIPELINE_STEPS.findIndex((step) => step.id === stepId);
  const active = stepIndex(state.phase);
  if (idx < active) return "done";
  if (idx === active) return "active";
  return "pending";
}

export function beginLintJob(): RenderPipelineState {
  const now = Date.now();
  return {
    ...INITIAL_PIPELINE_STATE,
    phase: "linting",
    jobKind: "lint",
    label: "Linting project",
    progress: 12,
    message: "Running diagnostics on scenes.py",
    startedAt: now,
  };
}

export function beginRenderJob(input: {
  scene?: string;
  quality: string;
  orientation: string;
}): RenderPipelineState {
  const now = Date.now();
  const scene = input.scene?.trim() || "Scene";
  return {
    ...INITIAL_PIPELINE_STATE,
    phase: "checking",
    jobKind: "render",
    label: `Rendering ${scene}`,
    scene,
    quality: input.quality,
    orientation: input.orientation,
    progress: 4,
    message: "Validating scene import",
    startedAt: now,
  };
}

export function failPipeline(
  state: RenderPipelineState,
  message: string,
): RenderPipelineState {
  return {
    ...state,
    phase: "error",
    progress: Math.max(state.progress, 5),
    message,
    error: message,
    completedAt: Date.now(),
  };
}

export function cancelRenderJob(state: RenderPipelineState): RenderPipelineState {
  return {
    ...state,
    phase: "cancelled",
    message: "Render cancelled by user",
    error: null,
    completedAt: Date.now(),
  };
}

export function isRenderActive(state: RenderPipelineState): boolean {
  return (
    state.jobKind === "render" &&
    state.phase !== "idle" &&
    state.phase !== "complete" &&
    state.phase !== "error" &&
    state.phase !== "cancelled"
  );
}

export function applySidecarEvent(
  state: RenderPipelineState,
  payload: SidecarEventPayload,
): RenderPipelineState {
  const data = payload.data;
  const message = asString(data.message) ?? asString(data.code);
  const now = Date.now();

  switch (payload.event) {
    case "lint_started":
      return {
        ...state,
        phase: "linting",
        jobKind: "lint",
        label: "Linting project",
        progress: Math.max(state.progress, 10),
        message: message ?? "Running diagnostics",
        startedAt: state.startedAt ?? now,
      };

    case "lint_complete":
      if (state.jobKind === "render") return state;
      return {
        ...state,
        phase: "complete",
        jobKind: "lint",
        label: "Lint complete",
        progress: 100,
        message: message ?? "Diagnostics finished",
        completedAt: now,
      };

    case "check_complete":
      if (state.jobKind !== "render") return state;
      return {
        ...state,
        phase: data.ok === false ? "error" : "compiling",
        progress: data.ok === false ? state.progress : 12,
        message:
          data.ok === false
            ? "Scene check failed"
            : message ?? "Scene import validated",
        error: data.ok === false ? "Scene check failed" : null,
        completedAt: data.ok === false ? now : null,
      };

    case "compile_started":
      return {
        ...state,
        phase: "compiling",
        jobKind: state.jobKind === "idle" ? "render" : state.jobKind,
        label: state.label ?? "Compiling scene",
        elementCount: asNumber(data.element_count),
        progress: Math.max(state.progress, 18),
        message: message ?? "Building sheet timeline",
        startedAt: state.startedAt ?? now,
      };

    case "layout_done": {
      const animationCount = asNumber(data.animation_count);
      return {
        ...state,
        phase: "layout",
        durationEstimate: asNumber(data.duration_estimate),
        progress: Math.max(state.progress, 34),
        message: message ?? "Layout and duration estimate ready",
        partialTotal: animationCount ?? state.partialTotal,
      };
    }

    case "render_started": {
      const animationCount = asNumber(data.animation_count);
      const fallbackEstimate =
        state.elementCount !== null ? Math.max(2, state.elementCount + 2) : null;
      const partialTotal = animationCount ?? state.partialTotal ?? fallbackEstimate;
      return {
        ...state,
        phase: "rendering",
        quality: asString(data.quality) ?? state.quality,
        progress: Math.max(state.progress, 42),
        message: message ?? "Starting Manim render",
        renderSection: "animate",
        partialIndex: 0,
        partialTotal,
        completedPartialCount: 0,
        encodingPartialIndex: null,
        frame: 0,
        totalFrames: null,
        segmentProgress: 0,
        partialSegmentSources: [],
      };
    }

    case "render_progress": {
      const pct = asNumber(data.pct);
      const scaled =
        pct === null ? state.progress : Math.round(40 + pct * 58);
      const frame = asNumber(data.frame);
      const totalFrames = asNumber(data.total_frames);
      const partialIndex = asNumber(data.partial_index);
      const partialTotal = asNumber(data.partial_total);
      const section = asString(data.section);
      const partialCached = asBoolean(data.partial_cached);
      const eventMessage = message ?? state.message;

      let encodingPartialIndex = state.encodingPartialIndex;
      let completedPartialCount = state.completedPartialCount;
      let resolvedPartialIndex = state.partialIndex;

      if (partialIndex !== null) {
        if (isSegmentBeginMessage(eventMessage)) {
          encodingPartialIndex = partialIndex;
          resolvedPartialIndex = partialIndex;
        } else if (isSegmentDoneMessage(eventMessage)) {
          completedPartialCount = Math.max(completedPartialCount, partialIndex);
          resolvedPartialIndex = partialIndex;
          encodingPartialIndex = null;
        } else if (encodingPartialIndex !== null) {
          resolvedPartialIndex = encodingPartialIndex;
        } else if (
          partialIndex >= (state.partialIndex ?? 0) ||
          state.partialIndex === null
        ) {
          resolvedPartialIndex = partialIndex;
        }
      }

      const sameEncodingSegment =
        encodingPartialIndex !== null &&
        encodingPartialIndex === state.encodingPartialIndex;

      const segmentProgress = currentPartialMovieProgress(state, {
        section,
        frame,
        totalFrames,
        eventMessage,
        partialCached,
        encodingPartialIndex,
        sameEncodingSegment,
      });

      const resolvedFrame =
        section === "combine"
          ? null
          : isSegmentBeginMessage(eventMessage)
            ? frame ?? 0
            : isSegmentDoneMessage(eventMessage)
              ? (totalFrames ?? state.totalFrames ?? frame)
              : frame ?? state.frame;

      const resolvedTotalFrames =
        section === "combine"
          ? null
          : isSegmentBeginMessage(eventMessage)
            ? totalFrames ?? state.totalFrames
            : isSegmentDoneMessage(eventMessage)
              ? (totalFrames ?? state.totalFrames)
              : totalFrames ?? state.totalFrames;

      const partialSegmentSources =
        partialCached !== null && resolvedPartialIndex !== null
          ? recordPartialSegmentSource(
              state.partialSegmentSources,
              resolvedPartialIndex,
              partialCached,
            )
          : state.partialSegmentSources;
      return {
        ...state,
        phase: "rendering",
        progress: Math.max(state.progress, Math.min(99, scaled)),
        message: eventMessage,
        renderSection: section ?? state.renderSection,
        partialIndex: resolvedPartialIndex,
        partialTotal:
          partialTotal === null
            ? state.partialTotal
            : Math.max(partialTotal, resolvedPartialIndex ?? 0, state.partialTotal ?? 0),
        completedPartialCount,
        encodingPartialIndex,
        frame: resolvedFrame,
        totalFrames: resolvedTotalFrames,
        segmentProgress,
        partialSegmentSources,
      };
    }

    case "render_complete":
      return {
        ...state,
        phase: "complete",
        progress: 100,
        message: message ?? "Render complete",
        videoPath: asString(data.video),
        error: null,
        completedAt: now,
      };

    case "error":
      return failPipeline(state, message ?? "Engine error");

    default:
      return state;
  }
}

export function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes > 0) return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
  return `${seconds}s`;
}

export function formatDurationEstimate(seconds: number | null): string | null {
  if (seconds === null) return null;
  if (seconds < 60) return `~${Math.round(seconds)}s reel`;
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return remainder > 0 ? `~${minutes}m ${remainder}s reel` : `~${minutes}m reel`;
}