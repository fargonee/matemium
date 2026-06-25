import { useEffect, useMemo, useState } from "react";

import type { RenderPipelineState } from "../utils/renderPipeline";
import {
  formatDurationEstimate,
  formatElapsed,
  PIPELINE_STEPS,
  stepStatus,
} from "../utils/renderPipeline";

interface RenderProgressPanelProps {
  pipeline: RenderPipelineState;
}

function phaseLabel(phase: RenderPipelineState["phase"], pipeline: RenderPipelineState): string {
  if (phase === "rendering") {
    if (pipeline.renderSection === "combine") return "Combining";
    if (pipeline.partialIndex !== null && pipeline.partialTotal !== null) {
      return `Segment ${pipeline.partialIndex}/${pipeline.partialTotal}`;
    }
    return "Rendering";
  }
  switch (phase) {
    case "idle":
      return "Ready";
    case "linting":
      return "Linting";
    case "checking":
      return "Checking";
    case "compiling":
      return "Compiling";
    case "layout":
      return "Layout";
    case "complete":
      return "Complete";
    case "cancelled":
      return "Cancelled";
    case "error":
      return "Failed";
    default:
      return "Working";
  }
}

function statusTone(phase: RenderPipelineState["phase"]): string {
  if (phase === "complete") return "ok";
  if (phase === "cancelled") return "cancelled";
  if (phase === "error") return "error";
  if (phase === "idle") return "idle";
  return "busy";
}

function partialStripCount(partialTotal: number | null): number {
  if (partialTotal === null || partialTotal <= 0) return 0;
  return Math.min(partialTotal, 28);
}

export function RenderProgressPanel({ pipeline }: RenderProgressPanelProps) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (pipeline.phase === "idle" || pipeline.phase === "complete" || pipeline.phase === "error") {
      return;
    }
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, [pipeline.phase]);

  const elapsed =
    pipeline.startedAt === null
      ? null
      : formatElapsed((pipeline.completedAt ?? now) - pipeline.startedAt);
  const durationHint = formatDurationEstimate(pipeline.durationEstimate);
  const isActive =
    pipeline.phase !== "idle" &&
    pipeline.phase !== "complete" &&
    pipeline.phase !== "error" &&
    pipeline.phase !== "cancelled";
  const showRenderDetail = pipeline.phase === "rendering";

  const stripCells = useMemo(() => {
    const total = partialStripCount(pipeline.partialTotal);
    if (total <= 0) return [];
    const completed = Math.max(
      0,
      Math.min(total, pipeline.completedPartialCount),
    );
    const activeIndex =
      pipeline.renderSection === "combine"
        ? null
        : pipeline.encodingPartialIndex;
    return Array.from({ length: total }, (_, index) => {
      const cell = index + 1;
      const source = pipeline.partialSegmentSources[index];
      let status: "done" | "active" | "pending" = "pending";
      if (cell <= completed) status = "done";
      else if (
        activeIndex !== null &&
        cell === activeIndex &&
        pipeline.renderSection !== "combine"
      ) {
        status = "active";
      } else if (pipeline.renderSection === "combine" && cell <= completed) {
        status = "done";
      }
      return { status, source };
    });
  }, [
    pipeline.completedPartialCount,
    pipeline.encodingPartialIndex,
    pipeline.partialTotal,
    pipeline.partialSegmentSources,
    pipeline.renderSection,
  ]);

  const activePartial =
    pipeline.encodingPartialIndex ?? pipeline.partialIndex ?? null;

  const segmentLabel =
    pipeline.renderSection === "combine"
      ? "Combining partial movies into final MP4"
      : activePartial !== null && pipeline.partialTotal !== null
        ? `Partial movie ${activePartial} of ${pipeline.partialTotal}`
        : "Encoding Manim segments";

  const frameLabel =
    pipeline.renderSection === "combine"
      ? "Stitching segments"
      : pipeline.frame !== null && pipeline.totalFrames !== null
        ? `${pipeline.frame} / ${pipeline.totalFrames} frames in this partial`
        : activePartial !== null
          ? `Partial movie ${activePartial}`
          : "Waiting for partial movie";

  const showPartialMovieBar =
    pipeline.renderSection !== "combine" && activePartial !== null;

  return (
    <div className="render-progress-panel">
      <div className="render-progress-header">
        <div className="render-progress-title-block">
          <div className="render-progress-eyebrow">Render pipeline</div>
          <div className="render-progress-title">
            {pipeline.label ?? "Waiting for a render job"}
          </div>
        </div>
        <div className={`render-status-pill render-status-pill-${statusTone(pipeline.phase)}`}>
          <span className="render-status-dot" aria-hidden />
          {phaseLabel(pipeline.phase, pipeline)}
        </div>
      </div>

      <div className="render-progress-bar-shell" aria-hidden={pipeline.phase === "idle"}>
        <div className="render-progress-bar-label">Overall</div>
        <div className="render-progress-bar-track">
          <div
            className={`render-progress-bar-fill ${isActive ? "is-active" : ""} ${
              pipeline.phase === "complete" ? "is-complete" : ""
            } ${pipeline.phase === "error" ? "is-error" : ""} ${
              pipeline.phase === "cancelled" ? "is-cancelled" : ""
            }`}
            style={{ width: `${Math.max(0, Math.min(100, pipeline.progress))}%` }}
          />
        </div>
        <div className="render-progress-percent">{Math.round(pipeline.progress)}%</div>
      </div>

      {showRenderDetail ? (
        <div className="render-detail-card" aria-live="polite">
          <div className="render-detail-header">
            <div>
              <div className="render-detail-eyebrow">Manim encode</div>
              <div className="render-detail-title">{segmentLabel}</div>
            </div>
            <div className="render-detail-frame">{frameLabel}</div>
          </div>

          {showPartialMovieBar ? (
            <div className="render-segment-progress">
              <div className="render-segment-progress-label">
                <span>Current partial movie</span>
                <span className="render-segment-progress-value">
                  {Math.round(pipeline.segmentProgress ?? 0)}%
                </span>
              </div>
              <div className="render-segment-bar-track render-segment-bar-track-lg">
                <div
                  className={`render-segment-bar-fill ${isActive ? "is-active" : ""}`}
                  style={{
                    width: `${Math.max(
                      0,
                      Math.min(100, pipeline.segmentProgress ?? 0),
                    )}%`,
                  }}
                />
              </div>
            </div>
          ) : null}

          {stripCells.length > 0 ? (
            <div className="render-partial-strip-wrap">
              <div className="render-partial-strip" aria-label="Partial movie segments">
                {stripCells.map((cell, index) => {
                  const sourceClass =
                    cell.source === "cache"
                      ? "render-partial-cell-cached"
                      : cell.source === "encode"
                        ? "render-partial-cell-encode"
                        : "";
                  const title =
                    cell.source === "cache"
                      ? `Segment ${index + 1} — cached`
                      : cell.source === "encode"
                        ? `Segment ${index + 1} — encoding`
                        : `Segment ${index + 1}`;
                  return (
                    <div
                      key={`partial-${index + 1}`}
                      className={`render-partial-cell render-partial-cell-${cell.status} ${sourceClass}`}
                      title={title}
                    />
                  );
                })}
                {pipeline.partialTotal !== null && pipeline.partialTotal > stripCells.length ? (
                  <span className="render-partial-overflow">
                    +{pipeline.partialTotal - stripCells.length}
                  </span>
                ) : null}
              </div>
              <div className="render-partial-legend" aria-hidden>
                <span className="render-partial-legend-item">
                  <span className="render-partial-legend-swatch render-partial-cell-cached" />
                  Cached
                </span>
                <span className="render-partial-legend-item">
                  <span className="render-partial-legend-swatch render-partial-cell-encode" />
                  Encoding
                </span>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="render-step-rail" role="list" aria-label="Render steps">
        {PIPELINE_STEPS.map((step, index) => {
          const status = stepStatus(step.id, pipeline);
          return (
            <div
              key={step.id}
              className={`render-step render-step-${status}`}
              role="listitem"
            >
              <div className="render-step-marker" aria-hidden>
                {status === "done" ? "✓" : status === "error" ? "!" : index + 1}
              </div>
              <div className="render-step-copy">
                <div className="render-step-title">{step.title}</div>
                <div className="render-step-caption">{step.caption}</div>
              </div>
              {index < PIPELINE_STEPS.length - 1 ? (
                <div className={`render-step-connector render-step-connector-${status}`} aria-hidden />
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="render-progress-meta">
        <div className="render-meta-card">
          <span className="render-meta-label">Scene</span>
          <span className="render-meta-value">{pipeline.scene ?? "—"}</span>
        </div>
        <div className="render-meta-card">
          <span className="render-meta-label">Quality</span>
          <span className="render-meta-value">{pipeline.quality ?? "—"}</span>
        </div>
        <div className="render-meta-card">
          <span className="render-meta-label">Format</span>
          <span className="render-meta-value">{pipeline.orientation ?? "—"}</span>
        </div>
        <div className="render-meta-card">
          <span className="render-meta-label">Segment</span>
          <span className="render-meta-value">
            {pipeline.partialIndex !== null && pipeline.partialTotal !== null
              ? `${pipeline.partialIndex} / ${pipeline.partialTotal}`
              : "—"}
          </span>
        </div>
        <div className="render-meta-card">
          <span className="render-meta-label">Frame</span>
          <span className="render-meta-value">
            {pipeline.frame !== null && pipeline.totalFrames !== null
              ? `${pipeline.frame} / ${pipeline.totalFrames}`
              : "—"}
          </span>
        </div>
        <div className="render-meta-card">
          <span className="render-meta-label">Elapsed</span>
          <span className="render-meta-value">{elapsed ?? "—"}</span>
        </div>
        <div className="render-meta-card">
          <span className="render-meta-label">Estimate</span>
          <span className="render-meta-value">{durationHint ?? "—"}</span>
        </div>
      </div>

      <div className="render-progress-message" role="status" aria-live="polite">
        {pipeline.error ? (
          <span className="render-progress-message-error">{pipeline.error}</span>
        ) : (
          pipeline.message ?? "Start a render to see live pipeline status here."
        )}
      </div>

      {pipeline.videoPath ? (
        <div className="render-progress-footnote">
          Output: <span className="render-progress-path">{pipeline.videoPath}</span>
        </div>
      ) : null}
    </div>
  );
}