import { useEffect, useState, useCallback, useRef } from "react";
import { open, save } from "@tauri-apps/plugin-dialog";
import * as api from "../api/tauri";
import type {
  BundledExampleOpen,
  BundledExampleSummary,
  ProjectSummary,
} from "../api/types";
import { formatRelativeTime } from "../utils/formatDate";
import { videoAssetSrc } from "../utils/videoAsset";

interface ProjectsLandingProps {
  examples: BundledExampleSummary[];
  projects: ProjectSummary[];
  newName: string;
  busy: boolean;
  onNewNameChange: (value: string) => void;
  onCreate: () => void;
  onCreateExample: (exampleId: string) => void;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
  onExportArchive: (projectId: string, destination: string) => Promise<void>;
  onImportArchive: (source: string) => Promise<void>;
  readinessMessage?: string;
}

interface GalleryItem {
  id: string;
  title: string;
  description?: string;
  youtube_id?: string;
  video_src?: string;
  video_webm_src?: string;
  poster_src?: string;
  orientation?: "portrait" | "landscape";
  tags?: string[];
  author_name?: string;
  status?: string;
}

const FLAGSHIP_OUTCOMES: GalleryItem[] = [
  {
    id: "flagship-orbital-mechanics",
    title: "Why an Orbit Is a Continuous Fall",
    description: "Tangent velocity, inward gravity, and three launch speeds inside one persistent 3D world.",
    video_src: "/showcase/orbital-mechanics.mp4",
    video_webm_src: "/showcase/orbital-mechanics.webm",
    poster_src: "/showcase/orbital-mechanics.jpg",
    orientation: "portrait",
    tags: ["physics", "3D world"],
    author_name: "Matemium",
    status: "Flagship outcome",
  },
  {
    id: "flagship-sn2-reaction",
    title: "Inside an SN2 Reaction",
    description: "Backside attack, simultaneous bond change, and inversion held in one stable molecular view.",
    video_src: "/showcase/sn2-reaction.mp4",
    video_webm_src: "/showcase/sn2-reaction.webm",
    poster_src: "/showcase/sn2-reaction.jpg",
    orientation: "portrait",
    tags: ["chemistry", "3D molecule"],
    author_name: "Matemium",
    status: "Flagship outcome",
  },
  {
    id: "flagship-dna-to-protein",
    title: "From DNA to Protein",
    description: "A multiscale journey through transcription, RNA processing, export, and translation.",
    video_src: "/showcase/dna-to-protein.mp4",
    video_webm_src: "/showcase/dna-to-protein.webm",
    poster_src: "/showcase/dna-to-protein.jpg",
    orientation: "landscape",
    tags: ["biology", "multiscale"],
    author_name: "Matemium",
    status: "Flagship outcome",
  },
  {
    id: "flagship-feedback-control",
    title: "How Feedback Stabilizes a System",
    description: "Cruise control connects a physical disturbance to measurement, correction, and recovery.",
    video_src: "/showcase/feedback-control.mp4",
    video_webm_src: "/showcase/feedback-control.webm",
    poster_src: "/showcase/feedback-control.jpg",
    orientation: "landscape",
    tags: ["engineering", "systems"],
    author_name: "Matemium",
    status: "Flagship outcome",
  },
];

const ENHANCED_EXAMPLE_IDS = new Set([
  "physics/orbital-mechanics",
  "chemistry/sn2-reaction",
  "engineering/feedback-control",
  "biology/dna-to-protein",
]);

function matchesGallerySearch(item: GalleryItem, query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return (
    item.title.toLowerCase().includes(normalized) ||
    (item.description || "").toLowerCase().includes(normalized) ||
    (item.tags || []).some((tag) => tag.toLowerCase().includes(normalized))
  );
}

function isFlagshipCloudDuplicate(item: GalleryItem) {
  const identity = `${item.id} ${item.title}`.toLowerCase();
  return (
    identity.includes("orbital") ||
    identity.includes("sn2") ||
    identity.includes("feedback") ||
    (identity.includes("dna") && identity.includes("protein"))
  );
}

interface Collection {
  id: string;
  name: string;
  projectIds: string[];
}

function getAuthorInitials(author?: string) {
  if (!author) return "M";
  return author
    .split(" ")
    .map((w) => w.charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();
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

function archiveFileName(project: ProjectSummary) {
  const base = project.name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
  return `${base || "matemium-project"}.matemium.zip`;
}

export function ProjectsLanding({
  examples,
  projects,
  newName,
  busy,
  onNewNameChange,
  onCreate,
  onCreateExample,
  onOpen,
  onDelete,
  onExportArchive,
  onImportArchive,
  readinessMessage,
}: ProjectsLandingProps) {
  // Gallery and basic states
  const [galleryItems, setGalleryItems] = useState<GalleryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedVideo, setSelectedVideo] = useState<GalleryItem | null>(null);
  const [selectedExampleSource, setSelectedExampleSource] = useState<BundledExampleOpen | null>(null);
  const [exampleSourceFile, setExampleSourceFile] = useState("scenes");
  const [exampleSourceLoading, setExampleSourceLoading] = useState<string | null>(null);
  const [exampleSourceError, setExampleSourceError] = useState<string | null>(null);
  const [showExampleLibrary, setShowExampleLibrary] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<{id: string, name: string} | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [archiveBusy, setArchiveBusy] = useState<string | null>(null);
  const [archiveError, setArchiveError] = useState<string | null>(null);

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
  
  // Naming Modal Collection Target
  const [targetCollectionId, setTargetCollectionId] = useState<string | null>(null);

  const inspectExample = async (exampleId: string) => {
    setExampleSourceLoading(exampleId);
    setExampleSourceError(null);
    try {
      const source = await api.exampleOpenSource(exampleId);
      setSelectedExampleSource(source);
      setExampleSourceFile("scenes");
    } catch (sourceError) {
      setExampleSourceError(String(sourceError));
    } finally {
      setExampleSourceLoading(null);
    }
  };

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
    if (targetCollectionId === id) {
      setTargetCollectionId(null);
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

  const handleExportArchive = async (project: ProjectSummary) => {
    setArchiveError(null);
    const destination = await save({
      defaultPath: archiveFileName(project),
      filters: [{ name: "Matemium project archive", extensions: ["zip"] }],
    });
    if (!destination) return;

    setArchiveBusy(`export:${project.id}`);
    try {
      await onExportArchive(project.id, destination);
    } catch (exportError) {
      setArchiveError(String(exportError));
    } finally {
      setArchiveBusy(null);
    }
  };

  const handleImportArchive = async () => {
    setArchiveError(null);
    const selected = await open({
      multiple: false,
      directory: false,
      filters: [{ name: "Matemium project archive", extensions: ["zip"] }],
    });
    if (!selected || Array.isArray(selected)) return;

    setArchiveBusy("import");
    try {
      await onImportArchive(selected);
    } catch (importError) {
      setArchiveError(String(importError));
    } finally {
      setArchiveBusy(null);
    }
  };

  // Auto-associate newly created project with the selected target collection
  const projectsRef = useRef<string[]>(projects.map((p) => p.id));
  const [prevProjectsCount, setPrevProjectsCount] = useState(projects.length);
  const pendingCollectionIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (projects.length > prevProjectsCount) {
      if (pendingCollectionIdRef.current) {
        const prevIds = new Set(projectsRef.current);
        const newProject = projects.find((p) => !prevIds.has(p.id));
        if (newProject) {
          handleToggleProjectInCollection(pendingCollectionIdRef.current, newProject.id, true);
        }
      }
      pendingCollectionIdRef.current = null;
    }
    setPrevProjectsCount(projects.length);
    projectsRef.current = projects.map((p) => p.id);
  }, [projects, prevProjectsCount, handleToggleProjectInCollection]);

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

  const flagshipItems = FLAGSHIP_OUTCOMES.filter((item) =>
    matchesGallerySearch(item, searchQuery),
  );
  const earlierItems = galleryItems.filter(
    (item) => !isFlagshipCloudDuplicate(item) && matchesGallerySearch(item, searchQuery),
  );

  // Filter projects list by active collection
  const activeCollection = collections.find((c) => c.id === activeCollectionId);
  const filteredProjects = activeCollection
    ? projects.filter((p) => activeCollection.projectIds.includes(p.id))
    : projects;

  return (
    <div className="projects-landing-page-modern" onClick={() => setManagingProjectId(null)}>
      {/* 1. Product promise */}
      <div className="projects-landing-hero-modern-unified">
        <p className="projects-landing-eyebrow-modern">Agentic visual reasoning studio</p>
        <h2 className="projects-landing-heading-modern">Turn complex ideas into structured visual stories.</h2>
        <p className="projects-landing-lead-modern">
          Build staged explanations for mathematics, science, computing, engineering, and any subject that benefits from diagrams, motion, and spatial reasoning.
        </p>
      </div>

      {/* 2. Compact launcher for bundled, source-only examples */}
      <section className="example-library-modern">
        <button
          type="button"
          className="example-library-launch-modern"
          onClick={() => setShowExampleLibrary(true)}
          aria-haspopup="dialog"
        >
          <span className="example-library-launch-icon-modern" aria-hidden>✦</span>
          <span className="example-library-launch-copy-modern">
            <span className="example-library-kicker-modern">
              {examples.length} subjects · source only
            </span>
            <strong>Explore the Bundled Example Library</strong>
            <small>Project briefs and clean authoring templates, ready to open as editable copies.</small>
          </span>
          <span className="example-library-symbols-modern" aria-hidden>
            {examples.slice(0, 5).map((example) => (
              <span key={example.id}>{example.symbol}</span>
            ))}
            {examples.length > 5 && <span>+{examples.length - 5}</span>}
          </span>
          <span className="example-library-open-modern">
            Open library <span aria-hidden>↗</span>
          </span>
        </button>
      </section>

      {/* 3. Dual-Pane Layout */}
      <div className="dashboard-layout-grid-modern">
        {/* Left Column: Your Projects Workspace */}
        <section className="workspace-pane-modern">
          <div className="pane-header-modern">
            <div className="pane-header-title-container">
              <h3 className="pane-title-modern">Your Projects</h3>
              <span className="count-badge-modern">{filteredProjects.length}</span>
            </div>
            <button
              type="button"
              className="btn btn-secondary project-import-archive-modern"
              disabled={archiveBusy !== null}
              onClick={() => void handleImportArchive()}
            >
              {archiveBusy === "import" ? "Importing..." : "Import Project"}
            </button>
          </div>

          {archiveError && (
            <div className="project-archive-error-modern">
              {archiveError}
            </div>
          )}

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
                setTargetCollectionId(activeCollectionId);
                setShowCreateModal(true);
              }}
              title="Click to start a new visual project"
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

                <button
                  type="button"
                  className="project-card-export-modern"
                  title="Export project archive"
                  disabled={archiveBusy !== null}
                  onClick={(e) => {
                    e.stopPropagation();
                    void handleExportArchive(project);
                  }}
                >
                  {archiveBusy === `export:${project.id}` ? "…" : "⇩"}
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
                    setProjectToDelete({ id: project.id, name: project.name });
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
              <h3 className="pane-title-modern">Explore</h3>
              <span className="flagship-count-modern">4 FLAGSHIPS</span>
            </div>
            <input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="inspiration-search-input-modern"
            />
          </div>

          {error && (
            <div style={{ color: "var(--text-muted)", fontSize: "0.74rem", marginBottom: "12px", background: "rgba(255,255,255,0.02)", padding: "6px 10px", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
              Community feed unavailable. Flagship outcomes remain available offline.
            </div>
          )}

          <div className="inspiration-content-scroll-modern">
              <div className="flagship-section-heading-modern">
                <div>
                  <span className="flagship-kicker-modern">Made with Matemium</span>
                  <h4>Flagship outcomes</h4>
                </div>
                <p>Our strongest project worlds, rendered from the bundled editable source.</p>
              </div>

              <div className="flagship-grid-modern">
                {flagshipItems.map((item) => (
                  <article
                    key={item.id}
                    className={`flagship-card-modern flagship-${item.orientation}`}
                    onClick={() => setSelectedVideo(item)}
                    onMouseEnter={(event) => {
                      const video = event.currentTarget.querySelector("video");
                      if (video) void video.play().catch(() => undefined);
                    }}
                    onMouseLeave={(event) => {
                      const video = event.currentTarget.querySelector("video");
                      if (video) {
                        video.pause();
                        video.currentTime = 0;
                      }
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedVideo(item);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    title={`Watch ${item.title}`}
                  >
                    <div className="flagship-media-modern">
                      <video
                        poster={item.poster_src}
                        muted
                        loop
                        playsInline
                        preload="metadata"
                        aria-label={`${item.title} outcome preview`}
                      >
                        {item.video_webm_src && <source src={item.video_webm_src} type="video/webm" />}
                        {item.video_src && <source src={item.video_src} type="video/mp4" />}
                      </video>
                      <span className="flagship-badge-modern">FLAGSHIP</span>
                      <div className="inspiration-play-overlay-modern">
                        <div className="play-button-ring-modern">
                          <svg viewBox="0 0 24 24" width="16" height="16" className="svg-play-triangle-modern">
                            <path fill="currentColor" d="M8 5v14l11-7z" />
                          </svg>
                        </div>
                      </div>
                    </div>
                    <div className="flagship-card-body-modern">
                      <span>{item.tags?.[0]}</span>
                      <h4>{item.title}</h4>
                      <p>{item.description}</p>
                    </div>
                  </article>
                ))}
              </div>

              {loading ? (
                <div className="inspiration-loading-modern inspiration-loading-compact-modern">
                  <div className="spinner-modern"></div>
                  <span>Loading earlier studies...</span>
                </div>
              ) : (
                <>
                  {earlierItems.length > 0 && (
                    <div className="earlier-studies-heading-modern">
                      <div>
                        <h4>Earlier studies</h4>
                        <span>{earlierItems.length} tape-based explorations</span>
                      </div>
                      <p>Useful references from the engine’s earlier visual language.</p>
                    </div>
                  )}

                  <div className="inspiration-grid-modern earlier-studies-grid-modern">
                    {earlierItems.map((item) => {
                      const yt = item.youtube_id || (item as any).youtubeId || "";
                      const tags = item.tags || [];
                      const author = item.author_name || (item as any).author;
                      return (
                        <div
                          key={item.id}
                          className="inspiration-card-modern earlier-study-card-modern"
                          onClick={() => setSelectedVideo(item)}
                          title="Watch earlier study"
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
                              <div className="play-button-ring-modern">
                                <svg viewBox="0 0 24 24" width="16" height="16" className="svg-play-triangle-modern">
                                  <path fill="currentColor" d="M8 5v14l11-7z" />
                                </svg>
                              </div>
                            </div>
                            <span className="earlier-study-label-modern">STUDY</span>
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
                              {author && (
                                <span className="inspiration-author-modern">
                                  <span className="avatar-circle-small-modern">{getAuthorInitials(author)}</span>
                                  {author}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                    {flagshipItems.length === 0 && earlierItems.length === 0 && (
                      <div className="inspiration-empty-modern">
                        No matches for "{searchQuery}". Try physics, algorithms, biology, history, or algebra.
                      </div>
                    )}
                  </div>
                </>
              )}
          </div>
        </section>
      </div>

      {/* Bundled Example Library */}
      {showExampleLibrary && (
        <div
          className="gallery-modal example-library-overlay-modern"
          onClick={() => setShowExampleLibrary(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="example-library-title"
        >
          <div
            className="modal-content example-library-modal-modern"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="modal-close"
              onClick={() => setShowExampleLibrary(false)}
              aria-label="Close example library"
            >
              ✕
            </button>
            <div className="example-library-header-modern">
              <div>
                <p className="example-library-kicker-modern">
                  Eleven example projects · complete editable source
                </p>
                <h3 id="example-library-title">Bundled Example Library</h3>
                <p>
                  Every project includes authored scenes, reusable helpers, and
                  its complete workflow brief. Inspect the source or open an
                  independent editable copy. The four enhanced flagships match
                  the polished outcome videos in Explore.
                </p>
              </div>
              <span className="example-library-count-modern">
                SOURCE ONLY · {examples.length}
              </span>
            </div>

            {exampleSourceError && (
              <div className="example-library-error-modern">{exampleSourceError}</div>
            )}

            <div className="example-library-grid-modern">
              {examples.map((example) => (
                <article
                  className={`example-card-modern example-${example.subject}${ENHANCED_EXAMPLE_IDS.has(example.id) ? " example-card-enhanced-modern" : ""}`}
                  key={example.id}
                >
                  {ENHANCED_EXAMPLE_IDS.has(example.id) && (
                    <div className="example-flagship-seal-modern">
                      <span className="example-flagship-emblem-modern" aria-hidden>
                        <span>✦</span>
                      </span>
                      <span className="example-flagship-seal-copy-modern">
                        <strong>Enhanced flagship</strong>
                        <small>Polished showcase outcome</small>
                      </span>
                      <span className="example-flagship-seal-mark-modern" aria-hidden>M</span>
                    </div>
                  )}
                  <div className="example-card-top-modern">
                    <span className="example-symbol-modern" aria-hidden>{example.symbol}</span>
                    <div>
                      <span className="example-subject-modern">{example.subjectLabel}</span>
                      <h4>{example.title}</h4>
                    </div>
                    <div className="example-card-badges-modern">
                      <span className="example-stage-modern">
                        {example.stage === "source-ready" ? "Source ready" : example.stage}
                      </span>
                    </div>
                  </div>
                  <p className="example-question-modern">{example.question}</p>
                  <p className="example-description-modern">{example.description}</p>
                  <div className="example-capabilities-modern">
                    {example.capabilities.slice(0, 4).map((capability) => (
                      <span key={capability}>{capability}</span>
                    ))}
                  </div>
                  <div className="example-card-actions-modern">
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={busy || !!readinessMessage}
                      onClick={() => onCreateExample(example.id)}
                    >
                      Create editable copy
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={exampleSourceLoading === example.id}
                      onClick={() => void inspectExample(example.id)}
                    >
                      {exampleSourceLoading === example.id ? "Opening…" : "Inspect source"}
                    </button>
                  </div>
                  <div className="example-card-footnote-modern">
                    Complete editable source
                    {" · "}{(example.sourceBytes / 1024).toFixed(0)} KB · No video bundled
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 4. Small Modal to Input Project Name */}
      {showCreateModal && (
        <div className="gallery-modal" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content create-modal-content-modern" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowCreateModal(false)}>✕</button>
            <h3 className="create-modal-title-modern">Initialize Your Project</h3>
            <p className="create-modal-subtitle-modern">Give your visual explanation a descriptive name to start your editing workspace.</p>
            
            <div className="create-modal-input-group-modern">
              <input
                value={newName}
                placeholder="e.g., Orbital Motion, Sorting Algorithms, Cell Division..."
                onChange={(e) => onNewNameChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newName.trim() && !busy && !readinessMessage) {
                    pendingCollectionIdRef.current = targetCollectionId;
                    onCreate();
                    setShowCreateModal(false);
                  }
                }}
                className="create-input-modern create-modal-input-modern"
                autoFocus
              />

              {collections.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "0.76rem", color: "var(--text-secondary)", fontWeight: 500 }}>
                    Add to Collection (Optional)
                  </label>
                  <select
                    value={targetCollectionId || ""}
                    onChange={(e) => setTargetCollectionId(e.target.value || null)}
                    className="create-input-modern create-modal-input-modern"
                    style={{ cursor: "pointer", backgroundColor: "rgba(10, 12, 20, 0.7)" }}
                  >
                    <option value="">No Collection</option>
                    {collections.map((coll) => (
                      <option key={coll.id} value={coll.id}>
                        {coll.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              
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
                    pendingCollectionIdRef.current = targetCollectionId;
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
            <p className="create-modal-subtitle-modern">Group and organize projects by course, subject, audience, or series.</p>
            
            <div className="create-modal-input-group-modern">
              <input
                value={newCollectionName}
                placeholder="e.g., Mechanics, Algorithms, Biology..."
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

      {/* Example source inspector */}
      {selectedExampleSource && (
        <div className="gallery-modal" onClick={() => setSelectedExampleSource(null)}>
          <div
            className="modal-content example-source-modal-modern"
            onClick={(event) => event.stopPropagation()}
          >
            <button className="modal-close" onClick={() => setSelectedExampleSource(null)}>✕</button>
            <span className="example-subject-modern">
              {selectedExampleSource.summary.subjectLabel} · Source preview
            </span>
            <h3 className="modal-video-title-modern">{selectedExampleSource.summary.title}</h3>
            <p className="example-source-question-modern">
              {selectedExampleSource.summary.question}
            </p>
            <div className="example-source-tabs-modern">
              {Object.keys(selectedExampleSource.files).map((file) => (
                <button
                  type="button"
                  className={exampleSourceFile === file ? "active" : ""}
                  key={file}
                  onClick={() => setExampleSourceFile(file)}
                >
                  {file === "description"
                    ? "description.md"
                    : file === "scenes" || file === "helpers"
                      ? `${file}.py`
                      : file === "passport" || file === "roadmap"
                        ? `${file}.json`
                        : file === "tape_content"
                          ? "tapes/main.md"
                          : `${file}.md`}
                </button>
              ))}
            </div>
            <pre className="example-source-code-modern">
              <code>{selectedExampleSource.files[exampleSourceFile] ?? ""}</code>
            </pre>
            <div className="example-source-actions-modern">
              <span>This opens a new copy. The bundled source remains unchanged.</span>
              <button
                type="button"
                className="btn btn-primary"
                disabled={busy || !!readinessMessage}
                onClick={() => onCreateExample(selectedExampleSource.summary.id)}
              >
                Create editable copy
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. Video Lightbox Modal */}
      {selectedVideo && (
        <div className="gallery-modal" onClick={() => setSelectedVideo(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedVideo(null)}>✕</button>
            <h3 className="modal-video-title-modern">{selectedVideo.title}</h3>
            <div className="video-wrapper">
              {selectedVideo.video_src ? (
                <video
                  className={`flagship-modal-video-modern flagship-modal-${selectedVideo.orientation}`}
                  poster={selectedVideo.poster_src}
                  controls
                  autoPlay
                  muted
                  playsInline
                >
                  {selectedVideo.video_webm_src && <source src={selectedVideo.video_webm_src} type="video/webm" />}
                  <source src={selectedVideo.video_src} type="video/mp4" />
                </video>
              ) : (
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
              )}
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
              <span>
                {selectedVideo.video_src
                  ? "Bundled flagship outcome • Rendered with Matemium • Plays offline"
                  : "Public community animation • Powered by YouTube"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {projectToDelete && (
        <div className="gallery-modal" onClick={() => setProjectToDelete(null)}>
          <div className="modal-content create-modal-content-modern" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setProjectToDelete(null)}>✕</button>
            <h3 className="create-modal-title-modern">Delete Project</h3>
            <p className="create-modal-subtitle-modern" style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
              Are you sure you want to permanently delete <strong>{projectToDelete.name}</strong>? This action cannot be undone.
            </p>
            
            <div className="create-modal-actions-modern" style={{ marginTop: "24px" }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setProjectToDelete(null)}
                disabled={busy}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary create-modal-submit-btn-modern"
                disabled={busy}
                onClick={() => {
                  onDelete(projectToDelete.id);
                  setProjectToDelete(null);
                }}
                style={{ background: "var(--error)", borderColor: "var(--error)", color: "#fff" }}
              >
                Delete Project
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
