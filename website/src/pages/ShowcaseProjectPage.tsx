import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";

import { projectBySlug, subjectById } from "@/content/showcase";

type ViewMode = "watch" | "making";

export function ShowcaseProjectPage() {
  const { slug = "" } = useParams();
  const project = projectBySlug(slug);
  const [searchParams, setSearchParams] = useSearchParams();
  const viewMode: ViewMode = searchParams.get("view") === "making" ? "making" : "watch";

  const setViewMode = (mode: ViewMode) => {
    setSearchParams(mode === "making" ? { view: "making" } : {}, { replace: true });
  };

  if (!project) return <Navigate to="/showcase" replace />;

  const subject = subjectById(project.subject);

  return (
    <>
      <section className="project-hero">
        <div className="mx-auto max-w-7xl px-5">
          <Link to="/showcase" className="text-link">← Back to showcase</Link>
          <div className="mt-10 grid gap-12 lg:grid-cols-[0.75fr_1.25fr] lg:items-end">
            <div>
              <p className="section-kicker">{subject.name} · {project.productionPath}</p>
              <h1>{project.title}</h1>
              <p className="project-question">{project.question}</p>
              <p className="mt-5 max-w-xl leading-7 text-text-muted">{project.description}</p>
              <div className="mt-7 flex flex-wrap gap-2">
                {project.capabilities.map((capability) => (
                  <span key={capability} className="capability-chip">{capability}</span>
                ))}
              </div>
            </div>
            <div className="project-meta">
              <div><span>Format</span><strong>{project.orientation}</strong></div>
              <div><span>Duration</span><strong>{project.duration}</strong></div>
              <div><span>Rendered</span><strong>Locally</strong></div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-24 md:pb-32">
        <div className="project-view-tabs" role="tablist" aria-label="Project presentation">
          <button
            type="button"
            role="tab"
            aria-selected={viewMode === "watch"}
            className={viewMode === "watch" ? "active" : ""}
            onClick={() => setViewMode("watch")}
          >
            <span>▶</span> Watch
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={viewMode === "making"}
            className={viewMode === "making" ? "active" : ""}
            onClick={() => setViewMode("making")}
          >
            <span>&lt;/&gt;</span> How it was made
          </button>
        </div>

        {viewMode === "watch" ? (
          <div className="project-watch-panel">
            <video controls autoPlay muted playsInline poster={project.poster}>
              <source src={project.video} type="video/mp4" />
            </video>
            <div>
              <p className="section-kicker">The idea</p>
              <h2>Explanation before spectacle.</h2>
              <p>
                This project begins with a conceptual question and preserves the
                relationship between each visual step. The camera moves through the
                reasoning instead of replacing it with disconnected scenes.
              </p>
              <dl>
                <div><dt>Subject</dt><dd>{subject.name}</dd></div>
                <div><dt>Production path</dt><dd>{project.productionPath}</dd></div>
                <div><dt>Output</dt><dd>{project.orientation} video</dd></div>
              </dl>
            </div>
          </div>
        ) : (
          <div className="making-panel">
            <div className="making-copy">
              <p className="section-kicker">Under the surface</p>
              <h2>A structured idea becomes a scene.</h2>
              <p>
                This is a curated excerpt from the real project—not generated sample
                code. The complete authoring file remains available in the source repository.
              </p>
              <div className="mt-8">
                <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-text-subtle">Capabilities used</span>
                <div className="mt-3 flex flex-wrap gap-2">
                  {project.capabilities.map((capability) => (
                    <span key={capability} className="capability-chip">{capability}</span>
                  ))}
                </div>
              </div>
              <a href={project.sourceUrl} target="_blank" rel="noreferrer" className="button-secondary mt-9">
                View complete source <span aria-hidden>↗</span>
              </a>
            </div>
            <div className="source-window">
              <div className="source-window-bar">
                <span>{project.sourcePath}</span>
                <i>Python</i>
              </div>
              <pre><code>{project.sourceExcerpt}</code></pre>
            </div>
          </div>
        )}
      </section>

      <section className="border-t border-border px-5 py-20 text-center">
        <p className="section-kicker justify-center">Your idea, next</p>
        <h2 className="mx-auto mt-4 max-w-3xl font-display text-4xl md:text-6xl">
          Build an explanation with the same visual language.
        </h2>
        <Link to="/download" className="button-primary mt-8">Get Matemium <span aria-hidden>→</span></Link>
      </section>
    </>
  );
}
