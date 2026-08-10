import { Link } from "react-router-dom";

import { OutputCard } from "@/components/output-card";
import { SHOWCASE_PROJECTS, SUBJECT_AREAS, subjectById } from "@/content/showcase";

const WORKFLOW = [
  ["01", "Describe", "Begin with the idea, audience, and the understanding you want to create."],
  ["02", "Choose a path", "Create a mute film, synthesize a voice, or build around your own performance."],
  ["03", "Shape with the agent", "Approve the structure and answer focused creative decisions before generation."],
  ["04", "Render & repair", "Render locally, inspect the evidence, and correct visual problems in context."],
  ["05", "Deliver", "Export portrait reels, landscape lessons, or the entire reasoning tape as a study sheet."],
];

const VALUES = [
  ["Local by design", "Rendering, LaTeX, video encoding, and project files stay on your machine."],
  ["Knowledge in space", "Lay ideas out like a document, then move through them like a film—across 2D and 3D."],
  ["Your work is yours", "Keep and publish the lessons, videos, images, and scripts you create, including commercially."],
];

const SHIPPED_FEATURES = [
  "Portrait + landscape rendering",
  "Multiple camera-facing tapes",
  "2D, data visuals, and 3D worlds",
  "Live replay preview",
  "Full-tape PNG/PDF export",
  "Portable project archives",
  "11 editable subject examples",
  "BYO-provider or local AI",
];

function ArrowIcon() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" className="h-4 w-4" fill="none">
      <path d="M4 10h12M11 5l5 5-5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" className="h-4 w-4" fill="none">
      <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.4" />
      <path d="m8.3 6.9 5 3.1-5 3.1V6.9Z" fill="currentColor" />
    </svg>
  );
}

export function HomePage() {
  return (
    <>
      <section className="hero-grid relative isolate overflow-hidden border-b border-border px-5 pb-20 pt-12 md:pb-28 md:pt-20">
        <div className="hero-glow pointer-events-none absolute inset-0 -z-10" aria-hidden />
        <div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div className="max-w-2xl">
            <div className="eyebrow mb-6">
              <span className="status-dot" />
              Free, source-available desktop studio
            </div>
            <h1 className="font-display text-[clamp(3.5rem,8vw,7.2rem)] leading-[0.86] tracking-[-0.055em]">
              Give complex ideas <span className="text-gradient italic">motion.</span>
            </h1>
            <p className="mt-8 max-w-xl text-lg leading-8 text-text-muted md:text-xl">
              Matemium turns structured knowledge into visual stories—from mathematics
              and science to algorithms, history, language, and beyond.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to="/download" className="button-primary">
                Get Matemium <ArrowIcon />
              </Link>
              <Link to="/showcase" className="button-secondary">
                <PlayIcon /> Watch the work
              </Link>
            </div>
            <div className="mt-9 flex flex-wrap gap-x-7 gap-y-3 text-sm text-text-subtle">
              <span className="flex items-center gap-2"><span className="check">✓</span> Local rendering</span>
              <span className="flex items-center gap-2"><span className="check">✓</span> No subscription</span>
              <span className="flex items-center gap-2"><span className="check">✓</span> Creator-owned output</span>
            </div>
            <p className="mt-7 max-w-lg border-l border-accent/60 pl-4 text-sm leading-6 text-text-subtle">
              Built first for mathematics, where clarity and precision are non-negotiable.
              Designed for every complex idea that deserves a clear explanation.
            </p>
          </div>

          <div className="hero-stage mx-auto w-full max-w-[740px]">
            <div className="studio-window" aria-hidden>
              <div className="studio-titlebar">
                <div className="flex gap-1.5"><i /><i /><i /></div>
                <span>Matemium</span>
                <span className="engine-pill">Engine connected</span>
              </div>
              <div className="studio-body">
                <div className="studio-sidebar">
                  <b>quadratic_graphs</b>
                  <span>scenes.py</span><span>helpers.py</span>
                  <small>BRIEF</small>
                  <span>Description</span><span>Passport</span><span className="active">Roadmap</span>
                </div>
                <div className="studio-roadmap">
                  <small>PRODUCTION ROADMAP</small>
                  <strong>Project phases</strong>
                  <div className="phase-line">
                    <div><i>01</i><span>Project creation<small>Complete</small></span></div>
                    <div className="current"><i>02</i><span>Project description<small>We are here</small></span></div>
                    <div><i>03</i><span>Production path<small>Coming next</small></span></div>
                  </div>
                  <div className="path-grid">
                    <span>◇ Visual-first</span><span>◉ Voice synthesis</span><span>≈ Custom voice</span>
                  </div>
                </div>
                <div className="studio-agent">
                  <b>Agent</b>
                  <p>How should the graph comparison unfold?</p>
                  <span className="choice active">Compare coefficients side by side</span>
                  <span className="choice">Build one graph at a time</span>
                </div>
              </div>
            </div>

            <div className="portrait-player">
              <video
                autoPlay
                muted
                loop
                playsInline
                poster="/media/quadratic-graphs.jpg"
                preload="metadata"
                aria-label="Matemium quadratic graphs animation"
              >
                <source src="/media/quadratic-graphs.mp4" type="video/mp4" />
              </video>
              <div className="player-label">
                <span>Rendered locally</span>
                <span>9:16</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-border bg-bg-elevated/60 px-5">
        <div className="mx-auto grid max-w-7xl divide-y divide-border py-2 md:grid-cols-4 md:divide-x md:divide-y-0">
          {[
            ["Infinite sheet", "Document-like composition"],
            ["2D + 3D", "One continuous visual world"],
            ["Project-aware agent", "Durable briefs, decisions, and repair"],
            ["Portable projects", "Archive, move, and reopen whole workspaces"],
          ].map(([title, body]) => (
            <div key={title} className="px-0 py-5 first:pl-0 md:px-7">
              <strong className="block text-sm text-text">{title}</strong>
              <span className="mt-1 block text-xs text-text-subtle">{body}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="section-shell" id="showcase">
        <div className="section-heading">
          <div>
            <p className="section-kicker">Made with Matemium</p>
            <h2>See the reasoning.<br /><span className="text-text-muted">Then see the tool.</span></h2>
          </div>
          <div className="max-w-md">
            <p>
              Every example below is rendered by the Matemium engine. Hover or tap to
              watch equations, plots, fields, and spatial objects become a continuous explanation.
            </p>
            <Link to="/showcase" className="text-link mt-5">Explore the showcase <ArrowIcon /></Link>
          </div>
        </div>
        <div className="showcase-grid mt-12">
          {SHOWCASE_PROJECTS
            .filter((project) => project.featured)
            .sort((left, right) => Number(left.orientation === "Landscape") - Number(right.orientation === "Landscape"))
            .map((project) => (
              <OutputCard
                key={project.slug}
                {...project}
                subjectLabel={subjectById(project.subject).name}
              />
            ))}
        </div>
      </section>

      <section className="subjects-section border-y border-border px-5 py-24 md:py-32">
        <div className="mx-auto max-w-7xl">
          <div className="section-heading">
            <div>
              <p className="section-kicker">Beyond one subject</p>
              <h2>One studio.<br /><span className="text-text-muted">Every field of thought.</span></h2>
            </div>
            <div className="max-w-md">
              <p>
                Matemium is built for ideas that benefit from diagrams, staged explanation,
                spatial relationships, transformation, and motion. Published work is only
                the beginning of the library.
              </p>
              <Link to="/showcase" className="text-link mt-5">Follow the expanding showcase <ArrowIcon /></Link>
            </div>
          </div>
          <div className="subject-constellation mt-14">
            {SUBJECT_AREAS.map((subject) => (
              <article
                key={subject.id}
                className={`subject-card ${subject.status === "published" ? "published" : ""}`}
              >
                {subject.status === "published" ? (
                  <Link
                    to={`/showcase?subject=${subject.id}`}
                    className="absolute inset-0 z-10"
                    aria-label={`Explore ${subject.name} projects`}
                  />
                ) : null}
                <div className="subject-card-top">
                  <span className="subject-symbol">{subject.symbol}</span>
                  <span className={`subject-status ${subject.status}`}>
                    {subject.status === "published" ? "Published" : "In production"}
                  </span>
                </div>
                <h3>{subject.name}</h3>
                <p>{subject.scope}</p>
              </article>
            ))}
          </div>
          <div className="manifesto-line">
            <span>If it can be reasoned through,</span>
            <strong>it can be staged.</strong>
          </div>
        </div>
      </section>

      <section className="border-y border-border bg-bg-elevated/50 px-5 py-24 md:py-32">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-3xl">
            <p className="section-kicker">The production journey</p>
            <h2 className="section-title">A creative process,<br />not a prompt box.</h2>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-text-muted">
              Matemium’s agent does not rush from one sentence to generated code. It helps
              establish intent, asks for meaningful decisions, and follows the work through
              rendering and visual repair.
            </p>
          </div>
          <div className="workflow-line mt-16">
            {WORKFLOW.map(([number, title, description]) => (
              <article key={number} className="workflow-step">
                <span>{number}</span>
                <h3>{title}</h3>
                <p>{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="feature-evidence-section border-y border-border px-5 py-24 md:py-32" id="features">
        <div className="mx-auto max-w-7xl">
          <div className="section-heading">
            <div>
              <p className="section-kicker">In the studio now</p>
              <h2>From working source<br /><span className="text-text-muted">to durable deliverables.</span></h2>
            </div>
            <div className="max-w-md">
              <p>
                Matemium keeps the explanation, production decisions, media, and
                output together. These are current desktop controls captured from
                the same code that ships in the app.
              </p>
              <a href="https://docs.matemium.fargonee.space/desktop/import-export/" className="text-link mt-5">
                Read the import and export guide <ArrowIcon />
              </a>
            </div>
          </div>

          <div className="feature-proof-grid mt-12">
            <article className="feature-proof-card feature-proof-tape">
              <div className="feature-proof-copy">
                <span className="feature-proof-number">01</span>
                <div>
                  <p className="section-kicker">Full-tape documents</p>
                  <h3>Keep the whole line of reasoning.</h3>
                  <p>
                    Inspect the saved scene, choose any populated tape, then export
                    its natural uncropped proportions as PNG or PDF at native or fixed detail.
                  </p>
                </div>
              </div>
              <div className="feature-proof-shot">
                <img
                  src="/media/features/tape-export.png"
                  alt="Matemium Export full tape dialog showing three tapes, PNG and PDF formats, and resolution controls"
                  width="1600"
                  height="1000"
                  loading="lazy"
                />
              </div>
            </article>

            <article className="feature-proof-card feature-proof-projects">
              <div className="feature-proof-copy">
                <span className="feature-proof-number">02</span>
                <div>
                  <p className="section-kicker">Project portability</p>
                  <h3>Move the workspace, not just the movie.</h3>
                  <p>
                    Export a complete <code>.matemium.zip</code> archive, including
                    source, briefs, media, and output history. Importing creates a new
                    local project and opens it ready to continue.
                  </p>
                </div>
              </div>
              <div className="feature-proof-shot">
                <img
                  src="/media/features/project-portability.png"
                  alt="Matemium project library with Import Project, project archive controls, 11 bundled subjects, and four flagship outcomes"
                  width="1600"
                  height="1000"
                  loading="lazy"
                />
              </div>
            </article>
          </div>

          <div className="shipped-feature-list mt-8" aria-label="Current Matemium features">
            {SHIPPED_FEATURES.map((feature) => <span key={feature}>{feature}</span>)}
          </div>
        </div>
      </section>

      <section className="section-shell overflow-hidden">
        <div className="grid items-center gap-16 lg:grid-cols-[0.85fr_1.15fr]">
          <div>
            <p className="section-kicker">The infinite reasoning tape</p>
            <h2 className="section-title">Lay it out like a document. Move through it like a film.</h2>
            <p className="mt-6 text-lg leading-8 text-text-muted">
              Traditional animation starts with a timeline. Matemium starts with the logic
              of the explanation. Ideas remain spatially connected while the camera reveals,
              revisits, compares, and inspects them.
            </p>
            <div className="mt-9 grid gap-7 sm:grid-cols-2">
              <div>
                <span className="metric">9:16</span>
                <p className="mt-2 text-sm text-text-subtle">Portrait lessons and reels by default.</p>
              </div>
              <div>
                <span className="metric">∞</span>
                <p className="mt-2 text-sm text-text-subtle">A continuous sheet instead of disconnected slides.</p>
              </div>
            </div>
          </div>
          <div className="tape-visual">
            <div className="tape-rail" />
            {[
              ["01", "Define the idea", "ax² + bx + c = 0"],
              ["02", "Compare", "How does each coefficient move the graph?"],
              ["03", "Inspect in motion", "Trace • focus • transform"],
              ["04", "Keep the reasoning", "Export video or the entire sheet"],
            ].map(([number, title, body], index) => (
              <div key={number} className={`tape-card tape-card-${index + 1}`}>
                <span>{number}</span><div><strong>{title}</strong><p>{body}</p></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-border bg-bg-elevated/50 px-5 py-24 md:py-32">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-px overflow-hidden rounded-3xl border border-border bg-border md:grid-cols-3">
            {VALUES.map(([title, body], index) => (
              <article key={title} className="bg-bg-card p-8 md:p-10">
                <span className={`value-mark value-mark-${index + 1}`}>{index + 1}</span>
                <h3 className="mt-12 text-xl font-semibold">{title}</h3>
                <p className="mt-3 leading-7 text-text-muted">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section-shell">
        <div className="support-panel">
          <div className="support-orbit" aria-hidden />
          <div className="relative z-10 max-w-3xl">
            <p className="section-kicker text-[#b7adff]">Built freely. Sustained together.</p>
            <h2 className="font-display text-4xl tracking-tight md:text-6xl">
              Help build the agentic experience Matemium deserves.
            </h2>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[#c6c1db]">
              The desktop studio and rendering engine are built. The next level—deeper
              planning, automated visual repair, evaluation, and voice workflows—requires
              ongoing AI resources that one maintainer cannot sustainably fund alone.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to="/support" className="button-light">Support Matemium <ArrowIcon /></Link>
              <Link to="/roadmap" className="button-on-dark">See what support enables</Link>
            </div>
            <p className="mt-6 text-sm text-[#9791ae]">
              Contributions do not unlock a paid tier. They keep Matemium available and move
              the shared project forward.
            </p>
          </div>
        </div>
      </section>

      <section className="border-t border-border px-5 py-24 md:py-32">
        <div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="section-kicker">Ready when you are</p>
            <h2 className="font-display max-w-4xl text-5xl leading-[0.95] tracking-tight md:text-7xl">
              Your next visual explanation can start here.
            </h2>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to="/download" className="button-primary">Get Matemium <ArrowIcon /></Link>
            <a href="https://github.com/fargonee/math" target="_blank" rel="noreferrer" className="button-secondary">
              View source
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
