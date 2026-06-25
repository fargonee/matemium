import type { SectionItem } from "../api/types";
import type { MediaPreviewItem } from "../utils/mediaPreview";
import { OutputsExplorer } from "./OutputsExplorer";
import { SectionOutline } from "./SectionOutline";

export type SidebarView = "sections" | "outputs";

interface ProjectSidebarProps {
  view: SidebarView;
  onViewChange: (view: SidebarView) => void;
  sections: SectionItem[];
  projectId: string;
  busy: boolean;
  outputsRefreshToken: number;
  onJump: (line: number) => void;
  onStatus: (message: string, kind?: "ok" | "error") => void;
  onPreviewMedia?: (item: MediaPreviewItem) => void;
}

export function ProjectSidebar({
  view,
  onViewChange,
  sections,
  projectId,
  busy,
  outputsRefreshToken,
  onJump,
  onStatus,
  onPreviewMedia,
}: ProjectSidebarProps) {
  return (
    <div className="project-sidebar">
      <div className="sidebar-view-tabs">
        <button
          type="button"
          className={`sidebar-view-tab ${view === "sections" ? "active" : ""}`}
          onClick={() => onViewChange("sections")}
        >
          Sections
        </button>
        <button
          type="button"
          className={`sidebar-view-tab ${view === "outputs" ? "active" : ""}`}
          onClick={() => onViewChange("outputs")}
        >
          Outputs
        </button>
      </div>

      {view === "sections" ? (
        <div className="sidebar-sections-panel">
          <SectionOutline sections={sections} embedded onJump={onJump} />
        </div>
      ) : (
        <OutputsExplorer
          embedded
          projectId={projectId}
          busy={busy}
          refreshToken={outputsRefreshToken}
          onStatus={onStatus}
          onPreviewMedia={onPreviewMedia}
        />
      )}
    </div>
  );
}