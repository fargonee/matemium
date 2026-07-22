import { useState } from "react";

import type { SectionItem } from "../api/types";
import type { ProjectFile } from "../utils/workspacePrefs";
import { SectionOutline } from "./SectionOutline";

export type SidebarView = "project";
export type WorkspaceItem = ProjectFile | `tape:${string}` | "media-images" | "media-video" | "media-audio" | "renders";

interface ProjectSidebarProps {
  projectName: string;
  activeItem: WorkspaceItem;
  dirtyFiles: Record<ProjectFile, boolean>;
  validationErrors: Partial<Record<ProjectFile, string>>;
  sections: SectionItem[];
  productionPath: "mute_video" | "tts" | "custom_audio" | null;
  tapeSlugs: string[];
  onSelect: (item: WorkspaceItem) => void;
  onJump: (line: number) => void;
  onCreateTape: () => void;
}

const SHARED_BRIEF_FILES: Array<{ id: ProjectFile; label: string; kind: string }> = [
  { id: "description", label: "Description", kind: "MD" },
  { id: "passport", label: "Passport", kind: "JSON" },
  { id: "roadmap", label: "Roadmap", kind: "JSON" },
];

const CONTENT_FILES: Array<{ id: ProjectFile; label: string; kind: string }> = [
  { id: "tape_content", label: "Tape content", kind: "MD" },
  { id: "orchestration", label: "Orchestration", kind: "MD" },
];

const TTS_FILES: Array<{ id: ProjectFile; label: string; kind: string }> = [
  { id: "tts_narration", label: "TTS narration", kind: "MD" },
  { id: "tts_style", label: "TTS style", kind: "MD" },
];

const CUSTOM_AUDIO_FILES: Array<{ id: ProjectFile; label: string; kind: string }> = [
  { id: "audio_description", label: "Audio description", kind: "MD" },
  { id: "custom_narration", label: "Custom narration", kind: "MD" },
  { id: "transcript", label: "Verified transcript", kind: "MD" },
  { id: "timestamps", label: "Timestamps", kind: "JSON" },
];

export function ProjectSidebar({
  projectName,
  activeItem,
  dirtyFiles,
  validationErrors,
  sections,
  productionPath,
  tapeSlugs,
  onSelect,
  onJump,
  onCreateTape,
}: ProjectSidebarProps) {
  const [openGroups, setOpenGroups] = useState({ brief: true, media: true, renders: true });
  const toggle = (group: keyof typeof openGroups) =>
    setOpenGroups((current) => ({ ...current, [group]: !current[group] }));
  const briefFiles = [
    ...SHARED_BRIEF_FILES,
    ...(productionPath ? CONTENT_FILES : []),
    ...(productionPath === "tts" ? TTS_FILES : []),
    ...(productionPath === "custom_audio" ? CUSTOM_AUDIO_FILES : []),
  ];

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
            <span className="tree-count">{briefFiles.length + Math.max(0, tapeSlugs.length - 1)}</span>
          </button>
          {openGroups.brief ? <div className="project-tree-children">
            {briefFiles.map((file) => <div key={file.id}>
              {file.id === "tape_content" ? <>
                {fileButton(file.id, "Tape · main", file.kind)}
                {tapeSlugs.filter((slug) => slug !== "main").map((slug) => (
                  <button key={slug} type="button" className={`project-tree-item ${activeItem === `tape:${slug}` ? "active" : ""}`} onClick={() => onSelect(`tape:${slug}`)}>
                    <span className="file-kind file-kind-md">MD</span><span className="project-tree-label">Tape · {slug}</span>
                  </button>
                ))}
                <button type="button" className="project-tree-item" onClick={onCreateTape} title="Add another tape-content file">
                  <span className="file-kind">+</span><span className="project-tree-label">Add tape</span>
                </button>
              </> : fileButton(file.id, file.label, file.kind)}
            </div>)}
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
