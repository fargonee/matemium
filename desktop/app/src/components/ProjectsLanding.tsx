import { useEffect, useState, useCallback } from "react";
import * as api from "../api/tauri";
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

interface GalleryItem {
  id: string;
  title: string;
  description?: string;
  youtube_id?: string;
  tags?: string[];
  author_name?: string;
  status?: string;
}

function ProjectThumbnail({ previewVideo, sceneClass }: { previewVideo?: string | null; sceneClass: string }) {
  if (previewVideo) {
    return (
      <video
        className="project-card-thumb-modern"
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
    <div className="project-card-thumb-modern project-card-thumb-empty-modern">
      <span className="project-card-initial-modern">{initial}</span>
      <span className="project-card-thumb-hint-modern">No render yet</span>
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
  const [galleryItems, setGalleryItems] = useState<GalleryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedVideo, setSelectedVideo] = useState<GalleryItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadGallery = useCallback(async (q?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listGallery(q);
      const list = (res.items || res || []) as GalleryItem[];
      setGalleryItems(list);
    } catch (e: any) {
      setError(String(e));
      // Fallback with rich, inspiring math animations
      setGalleryItems([
        {
          id: "demo-quadratic",
          title: "Quadratic Factoring Visualized",
          description: "Geometric proof of binomial expansion and quadratic factoring.",
          youtube_id: "M7lc1UVf-VE",
          tags: ["algebra", "geometry"],
          author_name: "Matemium Demo",
        },
        {
          id: "demo-waves",
          title: "3D Electromagnetic Waves",
          description: "Visualization of oscillating electric and magnetic field vectors propagate in 3D.",
          youtube_id: "jNQXAC9IVRw",
          tags: ["physics", "electromagnetism"],
          author_name: "Community",
        },
        {
          id: "demo-fourier",
          title: "Fourier Series Expansion",
          description: "Deconstructing periodic functions into rotating epicycles and orbits.",
          youtube_id: "r6SgUyBeA_k",
          tags: ["calculus", "fourier"],
          author_name: "3Blue1Brown Series",
        },
        {
          id: "demo-matrices",
          title: "Linear Transformations & Matrices",
          description: "Visualizing the geometric transformation of 2D space under linear maps.",
          youtube_id: "fNk_zzaMoEs",
          tags: ["linear-algebra"],
          author_name: "3Blue1Brown Series",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadGallery();
  }, [loadGallery]);

  useEffect(() => {
    const t = setTimeout(() => {
      void loadGallery(searchQuery);
    }, 300);
    return () => clearTimeout(t);
  }, [searchQuery, loadGallery]);

  const filteredGallery = galleryItems.filter((item) => {
    const q = searchQuery.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      (item.description || "").toLowerCase().includes(q) ||
      ((item.tags || []) as string[]).some((t) => t.toLowerCase().includes(q))
    );
  });

  return (
    <div className="projects-landing-page-modern">
      {/* 1. Stunning Hero Section */}
      <div className="projects-landing-hero-modern">
        <div className="hero-left-modern">
          <p className="projects-landing-eyebrow-modern">Professional Math Animation Studio</p>
          <h2 className="projects-landing-heading-modern">Transform mathematical equations into stunning motion.</h2>
          <p className="projects-landing-lead-modern">
            Empower your teaching, presentations, and social feeds with professional-grade math visuals. AI-assisted scripting, real-time previews, and zero setup.
          </p>
        </div>
        <div className="hero-right-modern">
          <div className="projects-landing-create-card-modern">
            <h3 className="create-card-title-modern">Initialize New Project</h3>
            <div className="create-input-group-modern">
              <input
                value={newName}
                placeholder="Name your mathematical creation..."
                onChange={(e) => onNewNameChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onCreate();
                }}
                disabled={!!readinessMessage}
                className="create-input-modern"
              />
              <button
                type="button"
                className="btn btn-primary create-button-modern"
                disabled={busy || !newName.trim()}
                onClick={onCreate}
              >
                Create &amp; Author
              </button>
            </div>
            {readinessMessage && (
              <div className="readiness-banner-modern">
                <span className="readiness-pulse">●</span> {readinessMessage}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. Dual-Pane Layout */}
      <div className="dashboard-layout-grid-modern">
        {/* Left Column: Your Projects Workspace */}
        <section className="workspace-pane-modern">
          <div className="pane-header-modern">
            <div className="pane-header-title-container">
              <h3 className="pane-title-modern">Your Projects</h3>
              <span className="count-badge-modern">{projects.length}</span>
            </div>
          </div>

          {projects.length === 0 ? (
            <div className="projects-landing-empty-modern">
              <div className="projects-landing-empty-card-modern">
                <div className="empty-icon-modern">🪄</div>
                <h3>Your workspace is clean and quiet</h3>
                <p>Type a name above to kickstart your first math scene, or browse the community inspiration feed on the right to see what is possible.</p>
              </div>
            </div>
          ) : (
            <div className="project-card-grid-modern">
              {projects.map((project) => (
                <article key={project.id} className="project-card-modern">
                  <button
                    type="button"
                    className="project-card-open-modern"
                    onClick={() => onOpen(project.id)}
                  >
                    <div className="project-card-thumb-container-modern">
                      <ProjectThumbnail
                        previewVideo={project.preview_video}
                        sceneClass={project.scene_class}
                      />
                      <div className="project-card-badge-modern">Open Studio</div>
                    </div>
                    <div className="project-card-body-modern">
                      <h3>{project.name}</h3>
                      <div className="project-card-footer-modern">
                        <span className="project-card-scene-modern">{project.scene_class}</span>
                        <span className="project-card-meta-modern">{formatRelativeTime(project.updated_at)}</span>
                      </div>
                    </div>
                  </button>
                  <button
                    type="button"
                    className="project-card-delete-modern btn btn-ghost btn-danger"
                    title="Delete project"
                    disabled={busy}
                    onClick={() => onDelete(project.id)}
                  >
                    ✕
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>

        {/* Right Column: Live Inspiration Feed */}
        <section className="inspiration-pane-modern">
          <div className="pane-header-modern">
            <div className="pane-header-title-container">
              <h3 className="pane-title-modern">Community Inspiration</h3>
              <span className="live-indicator-modern">● LIVE FEED</span>
            </div>
            <input
              type="text"
              placeholder="Search inspiration..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="inspiration-search-input-modern"
            />
          </div>

          {error && (
            <div style={{ color: "var(--text-muted)", fontSize: "0.74rem", marginBottom: "12px", background: "rgba(255,255,255,0.02)", padding: "6px 10px", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
              Offline mode. Showing featured creations.
            </div>
          )}

          {loading ? (
            <div className="inspiration-loading-modern">
              <div className="spinner-modern"></div>
              <span>Connecting to Matemium hub...</span>
            </div>
          ) : (
            <div className="inspiration-grid-modern">
              {filteredGallery.map((item) => {
                const yt = item.youtube_id || (item as any).youtubeId || "";
                const tags = item.tags || [];
                const author = item.author_name || (item as any).author;
                return (
                  <div
                    key={item.id}
                    className="inspiration-card-modern"
                    onClick={() => setSelectedVideo(item)}
                    title="Click to watch this community math creation"
                  >
                    <div className="inspiration-thumb-container-modern">
                      {yt && (
                        <img
                          src={`https://img.youtube.com/vi/${yt}/hqdefault.jpg`}
                          alt={item.title}
                          onError={(e) => {
                            (e.target as HTMLImageElement).src =
                              "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='180'%3E%3Crect width='100%25' height='100%25' fill='%2310141e'/%3E%3Ctext x='50%25' y='50%25' fill='%235c6cf0' font-size='14' font-weight='600' font-family='sans-serif' text-anchor='middle'%3EMatemium Showcase%3C/text%3E%3C/svg%3E";
                          }}
                        />
                      )}
                      <div className="inspiration-play-overlay-modern">
                        <div className="play-triangle-modern">▶</div>
                      </div>
                    </div>
                    <div className="inspiration-card-body-modern">
                      <h4>{item.title}</h4>
                      <p className="inspiration-desc-modern">{item.description}</p>
                      <div className="inspiration-card-footer-modern">
                        <div className="inspiration-tags-modern">
                          {tags.slice(0, 2).map((tag) => (
                            <span key={tag} className="inspiration-tag-badge-modern">
                              #{tag}
                            </span>
                          ))}
                        </div>
                        {author && <span className="inspiration-author-modern">by {author}</span>}
                      </div>
                    </div>
                  </div>
                );
              })}
              {filteredGallery.length === 0 && (
                <div className="inspiration-empty-modern">
                  No matches for "{searchQuery}". Try searching for calculus, algebra, geometry or physics.
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      {/* 3. Gorgeous Video Lightbox Modal (Reuses elegant App.css overlay styles) */}
      {selectedVideo && (
        <div className="gallery-modal" onClick={() => setSelectedVideo(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedVideo(null)}>✕</button>
            <h3 className="modal-video-title-modern">{selectedVideo.title}</h3>
            <div className="video-wrapper">
              <iframe
                width="100%"
                height="440"
                src={`https://www.youtube.com/embed/${
                  selectedVideo.youtube_id || (selectedVideo as any).youtubeId
                }?autoplay=1`}
                title={selectedVideo.title}
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
            <div className="modal-meta-content-modern">
              <p className="modal-desc-modern">{selectedVideo.description}</p>
              <div className="modal-tags-modern">
                {selectedVideo.tags?.map((tag) => (
                  <span key={tag} className="modal-tag-badge-modern">#{tag}</span>
                ))}
              </div>
              {selectedVideo.author_name && (
                <div className="modal-author-modern">
                  Creator: <strong>{selectedVideo.author_name}</strong>
                </div>
              )}
            </div>
            <div className="meta-footer" style={{ marginTop: "16px" }}>
              <span>Public community animation • Powered by YouTube • Works fully before local engines are set up</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}