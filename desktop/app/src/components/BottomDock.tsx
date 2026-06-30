import type { BottomDockTab } from "../api/types";
import type { RenderPipelineState } from "../utils/renderPipeline";
import { isRenderActive } from "../utils/renderPipeline";
import { RenderProgressPanel } from "./RenderProgressPanel";
import { TerminalOutput } from "./TerminalOutput";
import { LiveMeasurementPreview } from "./LiveMeasurementPreview";

interface BottomDockProps {
  tab: BottomDockTab;
  onTabChange: (tab: BottomDockTab) => void;
  log: string;
  pipeline: RenderPipelineState;
  renderActive: boolean;
  onCancelRender: () => void;
  projectId?: string;
  onMaximize?: () => void;
}

export function BottomDock({
  tab,
  onTabChange,
  log,
  pipeline,
  renderActive,
  onCancelRender,
  projectId,
  onMaximize,
}: BottomDockProps) {
  const pipelineActive = isRenderActive(pipeline);

  return (
    <div className="bottom-dock">
      <div className="bottom-dock-toolbar" onDoubleClick={onMaximize}>
        <div className="bottom-tabs" role="tablist" aria-label="Bottom panel views">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "progress"}
            className={`bottom-tab ${tab === "progress" ? "active" : ""}`}
            onClick={() => onTabChange("progress")}
          >
            Progress
            {pipelineActive ? <span className="bottom-tab-live" aria-label="Live" /> : null}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "output"}
            className={`bottom-tab ${tab === "output" ? "active" : ""}`}
            onClick={() => onTabChange("output")}
          >
            Output
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "preview"}
            className={`bottom-tab ${tab === "preview" ? "active" : ""}`}
            onClick={() => onTabChange("preview")}
          >
            Live Preview
          </button>
        </div>
        <div className="bottom-dock-toolbar-actions">
          {renderActive ? (
            <button
              type="button"
              className="btn btn-cancel-render"
              onClick={onCancelRender}
            >
              Cancel render
            </button>
          ) : (
            <span className="bottom-dock-hint">
              {tab === "progress"
                ? "Structured pipeline view"
                : "Raw sidecar stream"}
            </span>
          )}
        </div>
      </div>

      <div
        className="bottom-dock-body"
        role="tabpanel"
        aria-label={tab === "progress" ? "Render progress" : tab === "output" ? "Terminal output" : "Live preview"}
      >
        {tab === "progress" ? (
          <RenderProgressPanel pipeline={pipeline} />
        ) : tab === "output" ? (
          <TerminalOutput text={log} />
        ) : (
          <LiveMeasurementPreview projectId={projectId} />
        )}
      </div>
    </div>
  );
}