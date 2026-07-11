import { useEffect, useState, useCallback, useRef } from "react";
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

interface Collection {
  id: string;
  name: string;
  projectIds: string[];
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
  // Gallery and basic states
  const [galleryItems, setGalleryItems] = useState<GalleryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedVideo, setSelectedVideo] = useState<GalleryItem | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Collections state
  const [collections, setCollections] = useState<Collection[]>(() => {
    try {
      const raw = localStorage.getItem("matemium-collections");
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const [activeCollectionId, setActiveCollectionId] = useState<string | null>(null);
  const [showNewCollectionModal, setShowNewCollectionModal] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [managingProjectId, setManagingProjectId] = useState<string | null>(null);

  // Helper to save collections
  const saveCollections = useCallback((updated: Collection[]) => {
    setCollections(updated);
    localStorage.setItem("matemium-collections", JSON.stringify(updated));
  }, []);

  // Collection Handlers
  const handleCreateCollection = () => {
    if (!newCollectionName.trim()) return;
    const newColl: Collection = {
      id: Date.now().toString(),
      name: newCollectionName.trim(),
      projectIds: [],
    };
    const updated = [...collections, newColl];
    saveCollections(updated);
    setNewCollectionName("");
    setShowNewCollectionModal(false);
    setActiveCollectionId(newColl.id); // Switch to newly created collection
  };

  const handleDeleteCollection = (id: string) => {
    const updated = collections.filter((c) => c.id !== id);
    saveCollections(updated);
    if (activeCollectionId === id) {
      setActiveCollectionId(null);
    }
  };

  const handleToggleProjectInCollection = useCallback(
    (collectionId: string, projectId: string, forceState?: boolean) => {
      const updated = collections.map((coll) => {
        if (coll.id === collectionId) {
          const alreadyHas = coll.projectIds.includes(projectId);
          const shouldHave = forceState !== undefined ? forceState : !alreadyHas;

          let newProjectIds = coll.projectIds;
          if (shouldHave && !alreadyHas) {
            newProjectIds = [...coll.projectIds, projectId];
          } else if (!shouldHave && alreadyHas) {
            newProjectIds = coll.projectIds.filter((id) => id !== projectId);
          }

          return { ...coll, projectIds: newProjectIds };
        }
        return coll;
      });
      saveCollections(updated);
    },
    [collections, saveCollections],
  );

  // Auto-associate newly created project with active collection
  const projectsRef = useRef<string[]>(projects.map((p) => p.id));
  const [prevProjectsCount, setPrevProjectsCount] = useState(projects.length);

  useEffect(() => {
    if (projects.length > prevProjectsCount) {
      if (activeCollectionId) {
        const prevIds = new Set(projectsRef.current);
        const newProject = projects.find((p) => !prevIds.has(p.id));
        if (newProject) {
          handleToggleProjectInCollection(activeCollectionId, newProject.id, true);
        }
      }
    }
    setPrevProjectsCount(projects.length);
    projectsRef.current = projects.map((p) => p.id);
  }, [projects, activeCollectionId, prevProjectsCount, handleToggleProjectInCollection]);

  // Gallery Loader
  const loadGallery = useCallback(async (q?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listGallery(q);
      const list = (res.items || res || []) as GalleryItem[];
      setGalleryItems(list);
    } catch (e: any) {
      setError(String(e));
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

  // Filter projects list by active collection
  const activeCollection = collections.find((c) => c.id === activeCollectionId);
  const filteredProjects = activeCollection
    ? projects.filter((p) => activeCollection.projectIds.includes(p.id))
    : projects;

  return (
    <div className="projects-landing-page-modern" onClick={() => setManagingProjectId(null)}>
      {/* 1. Stunning Hero Section */}
      <div className="projects-landing-hero-modern-unified">
        <p className="projects-landing-eyebrow-modern">Professional Math Animation Studio</p>
        <h2 className="projects-landing-heading-modern">Transform mathematical equations into stunning motion.</h2>
        <p className="projects-landing-lead-modern">
          Empower your teaching, presentations, and social feeds with professional-grade math visuals. AI-assisted scripting, real-time previews, and zero setup.
        </p>
      </div>

      {/* 2. Dual-Pane Layout */}
      <div className="dashboard-layout-grid-modern">
        {/* Left Column: Your Projects Workspace */}
        <section className="workspace-pane-modern">
          <div className="pane-header-modern">
            <div className="pane-header-title-container">
              <h3 className="pane-title-modern">Your Projects</h3>
              <span className="count-badge-modern">{filteredProjects.length}</span>
            </div>
          </div>

          {/* Collections filter row */}
          <div className="collections-filter-row-modern" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className={`collection-pill-modern ${activeCollectionId === null ? "active" : ""}`}
              onClick={() => setActiveCollectionId(null)}
            >
              All Projects
            </button>

            {collections.map((coll) => (
              <div key={coll.id} className="collection-pill-wrapper-modern">
                <button
                  type="button"
                  className={`collection-pill-modern ${activeCollectionId === coll.id ? "active" : ""}`}
                  onClick={() => setActiveCollectionId(coll.id)}
                >
                  📁 {coll.name}
                </button>
                <button
                  type="button"
                  className="collection-pill-delete-modern"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteCollection(coll.id);
                  }}
                  title={`Delete collection "${coll.name}" (does not delete projects)`}
                >
                  ✕
                </button>
              </div>
            ))}

            <button
              type="button"
              className="collection-pill-modern collection-pill-create-modern"
              onClick={() => setShowNewCollectionModal(true)}
            >
              + Create Collection
            </button>
          </div>

          <div className="project-card-grid-modern">
            {/* The First Item: Giant "+" Creation Card */}
            <article
              className="project-card-modern create-new-card-modern"
              onClick={(e) => {
                e.stopPropagation();
                setShowCreateModal(true);
              }}
              title="Click to start a new mathematical project"
            >
              <div className="project-card-thumb-container-modern create-new-thumb-container-modern">
                <div className="create-new-plus-modern">+</div>
              </div>
              <div className="project-card-body-modern">
                <h3 className="create-new-title-text-modern">New Project</h3>
                <div className="project-card-footer-modern">
                  <span className="project-card-scene-modern">
                    {activeCollection ? `Add to ${activeCollection.name}` : "Start a new creation"}
                  </span>
                </div>
              </div>
            </article>

            {/* Existing projects list */}
            {filteredProjects.map((project) => (
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

                {/* Collection manager trigger button */}
                <button
                  type="button"
                  className={`project-card-collection-btn-modern ${managingProjectId === project.id ? "active" : ""}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setManagingProjectId(managingProjectId === project.id ? null : project.id);
                  }}
                  title="Manage collections"
                >
                  📁
                </button>

                {/* Collection membership toggle popover */}
                {managingProjectId === project.id && (
                  <div className="collection-popover-modern" onClick={(e) => e.stopPropagation()}>
                    <div className="popover-header-modern">
                      <span>Collections</span>
                      <button className="popover-close-modern" onClick={() => setManagingProjectId(null)}>✕</button>
                    </div>
                    <div className="popover-list-modern">
                      {collections.map((coll) => {
                        const isMember = coll.projectIds.includes(project.id);
                        return (
                          <label key={coll.id} className="popover-item-modern">
                            <input
                              type="checkbox"
                              checked={isMember}
                              onChange={() => handleToggleProjectInCollection(coll.id, project.id)}
                            />
                            <span>{coll.name}</span>
                          </label>
                        );
                      })}
                      {collections.length === 0 && (
                        <p className="popover-empty-modern">No collections yet. Create one above!</p>
                      )}
                    </div>
                  </div>
                )}

                <button
                  type="button"
                  className="project-card-delete-modern btn btn-ghost btn-danger"
                  title="Delete project"
                  disabled={busy}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(project.id);
                  }}
                >
                  ✕
                </button>
              </article>
            ))}
          </div>
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

      {/* 3. Small Modal to Input Project Name */}
      {showCreateModal && (
        <div className="gallery-modal" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content create-modal-content-modern" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowCreateModal(false)}>✕</button>
            <h3 className="create-modal-title-modern">Initialize Your Project</h3>
            <p className="create-modal-subtitle-modern">Give your math scene/visual a descriptive name to start your editing workspace.</p>
            
            <div className="create-modal-input-group-modern">
              <input
                value={newName}
                placeholder="e.g., Fourier Series Epicycles, Inscribed Sphere..."
                onChange={(e) => onNewNameChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newName.trim() && !busy && !readinessMessage) {
                    onCreate();
                    setShowCreateModal(false);
                  }
                }}
                className="create-input-modern create-modal-input-modern"
                autoFocus
              />
              
              {readinessMessage && (
                <div className="readiness-banner-modern" style={{ marginTop: "8px" }}>
                  <span className="readiness-pulse">●</span> {readinessMessage}
                </div>
              )}

              <div className="create-modal-actions-modern">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary create-modal-submit-btn-modern"
                  disabled={busy || !newName.trim() || !!readinessMessage}
                  onClick={() => {
                    onCreate();
                    setShowCreateModal(false);
                  }}
                >
                  Create Project
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Collection Modal */}
      {showNewCollectionModal && (
        <div className="gallery-modal" onClick={() => setShowNewCollectionModal(false)}>
          <div className="modal-content create-modal-content-modern" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowNewCollectionModal(false)}>✕</button>
            <h3 className="create-modal-title-modern">Create New Collection</h3>
            <p className="create-modal-subtitle-modern">Group and organize your mathematical projects (e.g. Calculus, Physics, Waves proofs).</p>
            
            <div className="create-modal-input-group-modern">
              <input
                value={newCollectionName}
                placeholder="e.g., Linear Algebra, Calculus..."
                onChange={(e) => setNewCollectionName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newCollectionName.trim()) {
                    handleCreateCollection();
                  }
                }}
                className="create-input-modern"
                autoFocus
              />
              
              <div className="create-modal-actions-modern">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setShowNewCollectionModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary create-modal-submit-btn-modern"
                  disabled={!newCollectionName.trim()}
                  onClick={handleCreateCollection}
                >
                  Create Collection
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. Video Lightbox Modal */}
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