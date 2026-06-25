import type { BottomDockTab } from "../api/types";
import type { RenderPipelineState } from "../utils/renderPipeline";
import { isRenderActive } from "../utils/renderPipeline";
import { RenderProgressPanel } from "./RenderProgressPanel";
import { TerminalOutput } from "./TerminalOutput";

interface BottomDockProps {
  tab: BottomDockTab;
  onTabChange: (tab: BottomDockTab) => void;
  log: string;
  pipeline: RenderPipelineState;
  renderActive: boolean;
  onCancelRender: () => void;
}

export function BottomDock({
  tab,
  onTabChange,
  log,
  pipeline,
  renderActive,
  onCancelRender,
}: BottomDockProps) {
  const pipelineActive = isRenderActive(pipeline);

  return (
    <div className="bottom-dock">
      <div className="bottom-dock-toolbar">
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
        aria-label={tab === "progress" ? "Render progress" : "Terminal output"}
      >
        {tab === "progress" ? (
          <RenderProgressPanel pipeline={pipeline} />
        ) : (
          <TerminalOutput text={log} />
        )}
      </div>
    </div>
  );
}