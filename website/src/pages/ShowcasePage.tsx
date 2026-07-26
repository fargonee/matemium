import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { OutputCard } from "@/components/output-card";
import {
  SHOWCASE_PROJECTS,
  SUBJECT_AREAS,
  subjectById,
  type SubjectId,
} from "@/content/showcase";

type Filter = "all" | SubjectId;

export function ShowcasePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const publishedSubjects = SUBJECT_AREAS.filter((subject) =>
    SHOWCASE_PROJECTS.some((project) => project.subject === subject.id),
  );
  const requestedFilter = searchParams.get("subject");
  const filter: Filter =
    requestedFilter && publishedSubjects.some((subject) => subject.id === requestedFilter)
      ? requestedFilter as SubjectId
      : "all";
  const setFilter = (nextFilter: Filter) => {
    setSearchParams(nextFilter === "all" ? {} : { subject: nextFilter }, { replace: true });
  };
  const visibleProjects = useMemo(
    () =>
      filter === "all"
        ? SHOWCASE_PROJECTS
        : SHOWCASE_PROJECTS.filter((project) => project.subject === filter),
    [filter],
  );

  return (
    <>
      <section className="page-hero">
        <p className="section-kicker">Made with Matemium</p>
        <h1>Complex ideas,<br /><span className="text-gradient italic">in motion.</span></h1>
        <p>
          Real output from the Matemium rendering engine—not concept art. Mathematics
          is where Matemium began; this library is growing across science, computing,
          engineering, the humanities, language, and general education.
        </p>
      </section>
      <section className="section-shell pt-0">
        <div className="subject-filters" role="group" aria-label="Filter showcase by subject">
          <button type="button" className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>
            All work <span>{SHOWCASE_PROJECTS.length}</span>
          </button>
          {publishedSubjects.map((subject) => (
            <button
              type="button"
              key={subject.id}
              className={filter === subject.id ? "active" : ""}
              onClick={() => setFilter(subject.id)}
            >
              {subject.shortName}
              <span>{SHOWCASE_PROJECTS.filter((project) => project.subject === subject.id).length}</span>
            </button>
          ))}
        </div>

        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {visibleProjects.map((project, index) => (
            <OutputCard
              key={project.slug}
              {...project}
              subjectLabel={subjectById(project.subject).name}
              eager={index === 0}
            />
          ))}
        </div>

        <div className="mt-20 rounded-3xl border border-border bg-bg-elevated p-8 md:p-12">
          <div className="grid gap-8 md:grid-cols-[0.8fr_1.2fr] md:items-end">
            <div>
              <span className="section-kicker">The expanding library</span>
              <h2 className="mt-3 font-display text-4xl md:text-5xl">More fields are entering production.</h2>
            </div>
            <p className="leading-7 text-text-muted">
              New demonstrations are being authored across chemistry, computer science,
              engineering, economics, biology, history, philosophy, language learning,
              and general education. A subject joins the filters above when its first
              polished, user-facing project is ready.
            </p>
          </div>
          <div className="mt-10 flex flex-wrap gap-2">
            {SUBJECT_AREAS.filter((subject) => subject.status === "in-production").map((subject) => (
              <span key={subject.id} className="future-subject-chip">
                {subject.symbol} {subject.shortName} <small>in production</small>
              </span>
            ))}
          </div>
        </div>

        <div className="mt-20 grid gap-6 rounded-3xl border border-border bg-bg-elevated p-8 md:grid-cols-3 md:p-12">
          <div>
            <span className="section-kicker">One engine</span>
            <h2 className="mt-3 font-display text-4xl">Many forms of explanation.</h2>
          </div>
          <p className="text-sm leading-7 text-text-muted">
            Start with a portrait reasoning tape for Shorts and Reels, or render the
            same kind of structured explanation for a landscape presentation.
          </p>
          <p className="text-sm leading-7 text-text-muted">
            Export the complete sheet as PNG or PDF when the reasoning should remain
            visible as reference material instead of disappearing with the timeline.
          </p>
        </div>
        <div className="mt-12 text-center">
          <Link to="/download" className="button-primary">Create with Matemium <span aria-hidden>→</span></Link>
        </div>
      </section>
    </>
  );
}
