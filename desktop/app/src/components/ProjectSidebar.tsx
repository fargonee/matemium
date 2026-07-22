import { useState } from "react";

import type { SectionItem } from "../api/types";
import type { ProjectFile } from "../utils/workspacePrefs";
import { SectionOutline } from "./SectionOutline";

export type SidebarView = "project";
export type WorkspaceItem = ProjectFile | "media-images" | "media-video" | "media-audio" | "renders";

interface ProjectSidebarProps {
  projectName: string;
  activeItem: WorkspaceItem;
  dirtyFiles: Record<ProjectFile, boolean>;
  validationErrors: Partial<Record<ProjectFile, string>>;
  sections: SectionItem[];
  onSelect: (item: WorkspaceItem) => void;
  onJump: (line: number) => void;
}

const BRIEF_FILES: Array<{ id: ProjectFile; label: string; kind: string }> = [
  { id: "passport", label: "Passport", kind: "JSON" },
  { id: "description", label: "Description", kind: "MD" },
  { id: "tape", label: "Tape", kind: "MD" },
  { id: "roadmap", label: "Roadmap", kind: "JSON" },
  { id: "narration", label: "Narration", kind: "MD" },
];

export function ProjectSidebar({
  projectName,
  activeItem,
  dirtyFiles,
  validationErrors,
  sections,
  onSelect,
  onJump,
}: ProjectSidebarProps) {
  const [openGroups, setOpenGroups] = useState({ brief: true, media: true, renders: true });
  const toggle = (group: keyof typeof openGroups) =>
    setOpenGroups((current) => ({ ...current, [group]: !current[group] }));

  const fileButton = (id: ProjectFile, label: string, kind: string) => (
    <button
      type="button"
      className={`project-tree-item ${activeItem === id ? "active" : ""}`}
      onClick={() => onSelect(id)}
      title={label}
    >
      <span className={`file-kind file-kind-${kind.toLowerCase()}`}>{kind}</span>
      <span className="project-tree-label">{label}</span>
      {validationErrors[id] ? <span className="project-tree-invalid" title={validationErrors[id]}>!</span> : dirtyFiles[id] ? <span className="project-tree-dirty" title="Unsaved changes" /> : null}
    </button>
  );

  return (
    <nav className="project-sidebar" aria-label="Project structure">
      <div className="project-tree-header">
        <span className="project-tree-eyebrow">Current project</span>
        <strong title={projectName}>{projectName}</strong>
      </div>
      <div className="project-tree-scroll">
        <div className="project-tree-group standalone">
          {fileButton("scenes", "scenes.py", "PY")}
          {activeItem === "scenes" && sections.length > 0 ? (
            <div className="project-tree-outline">
              <SectionOutline sections={sections} embedded onJump={onJump} />
            </div>
          ) : null}
          {fileButton("helpers", "helpers.py", "PY")}
        </div>

        <div className="project-tree-group">
          <button type="button" className="project-tree-group-button" onClick={() => toggle("brief")}>
            <span className="tree-chevron">{openGroups.brief ? "v" : ">"}</span>
            <span>Brief</span>
            <span className="tree-count">5</span>
          </button>
          {openGroups.brief ? <div className="project-tree-children">
            {BRIEF_FILES.map((file) => <div key={file.id}>{fileButton(file.id, file.label, file.kind)}</div>)}
          </div> : null}
        </div>

        <div className="project-tree-group">
          <button type="button" className="project-tree-group-button" onClick={() => toggle("media")}>
            <span className="tree-chevron">{openGroups.media ? "v" : ">"}</span>
            <span>Assets</span>
            <span className="tree-count">3</span>
          </button>
          {openGroups.media ? <div className="project-tree-children">
            {([ ["media-images", "Images", "IMG"], ["media-video", "Video", "VID"], ["media-audio", "Audio", "AUD"] ] as const).map(([id, label, kind]) => (
              <button key={id} type="button" className={`project-tree-item ${activeItem === id ? "active" : ""}`} onClick={() => onSelect(id)}>
                <span className="file-kind file-kind-media">{kind}</span><span className="project-tree-label">{label}</span>
              </button>
            ))}
          </div> : null}
        </div>

        <div className="project-tree-group">
          <button type="button" className="project-tree-group-button" onClick={() => toggle("renders")}>
            <span className="tree-chevron">{openGroups.renders ? "v" : ">"}</span><span>Renders</span>
          </button>
          {openGroups.renders ? <div className="project-tree-children">
            <button type="button" className={`project-tree-item ${activeItem === "renders" ? "active" : ""}`} onClick={() => onSelect("renders")}>
              <span className="file-kind file-kind-output">OUT</span><span className="project-tree-label">Output history</span>
            </button>
          </div> : null}
        </div>
      </div>
    </nav>
  );
}
