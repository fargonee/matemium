import type { ProjectSummary } from "../api/types";
import { formatRelativeTime } from "../utils/formatDate";
import { videoAssetSrc } from "../utils/videoAsset";

interface ProjectsLandingProps {
  projects: ProjectSummary[];
  newName: string;
  busy: boolean;
  onNewNameChange: (value: string) => void;
  onCreate: () => void;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
  readinessMessage?: string;
}

function ProjectThumbnail({ previewVideo, sceneClass }: { previewVideo?: string | null; sceneClass: string }) {
  if (previewVideo) {
    return (
      <video
        className="project-card-thumb"
        src={videoAssetSrc(previewVideo)}
        muted
        playsInline
        preload="metadata"
        onMouseEnter={(e) => {
          void e.currentTarget.play().catch(() => undefined);
        }}
        onMouseLeave={(e) => {
          e.currentTarget.pause();
          e.currentTarget.currentTime = 0;
        }}
      />
    );
  }

  const initial = sceneClass.trim().charAt(0).toUpperCase() || "M";
  return (
    <div className="project-card-thumb project-card-thumb-empty">
      <span className="project-card-initial">{initial}</span>
      <span className="project-card-thumb-hint">No render yet</span>
    </div>
  );
}

export function ProjectsLanding({
  projects,
  newName,
  busy,
  onNewNameChange,
  onCreate,
  onOpen,
  onDelete,
  readinessMessage,
}: ProjectsLandingProps) {
  return (
    <div className="projects-landing-page">
      <div className="projects-landing-hero">
        <div>
          <p className="projects-landing-eyebrow">Professional Math Animation Studio</p>
          <h2 className="projects-landing-heading">Your projects</h2>
          <p className="projects-landing-lead">
            Create sophisticated math visualizations with AI-assisted authoring. All computation runs locally.
          </p>
        </div>
        <div className="projects-landing-create">
          <input
            value={newName}
            placeholder="Name your new project"
            onChange={(e) => onNewNameChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onCreate();
            }}
            disabled={!!readinessMessage}
          />
          <button type="button" className="btn btn-primary" disabled={busy} onClick={onCreate}>
            New project
          </button>
        </div>
        {readinessMessage && (
          <div className="readiness-banner" style={{ marginTop: 12, padding: 8, background: "#222", color: "#0ff", fontSize: 13 }}>
            {readinessMessage}
          </div>
        )}
      </div>

      {projects.length === 0 ? (
        <div className="projects-landing-empty">
          <div className="projects-landing-empty-card">
            <h3>Start your first project</h3>
            <p>Create a project to edit scenes.py, render portrait reels, and preview outputs.</p>
          </div>
        </div>
      ) : (
        <div className="project-card-grid">
          {projects.map((project) => (
            <article key={project.id} className="project-card">
              <button
                type="button"
                className="project-card-open"
                onClick={() => onOpen(project.id)}
              >
                <ProjectThumbnail
                  previewVideo={project.preview_video}
                  sceneClass={project.scene_class}
                />
                <div className="project-card-body">
                  <h3>{project.name}</h3>
                  <p className="project-card-scene">{project.scene_class}</p>
                  <p className="project-card-meta">{formatRelativeTime(project.updated_at)}</p>
                </div>
              </button>
              <button
                type="button"
                className="project-card-delete btn btn-ghost btn-danger"
                title="Delete project"
                disabled={busy}
                onClick={() => onDelete(project.id)}
              >
                Delete
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}