import { Link } from "react-router-dom";

const COMPLETE = [
  "Infinite-sheet layout and animation engine",
  "2D, data visuals, multiple tapes, and persistent 3D worlds",
  "Desktop editor, durable project workspaces, media, and output history",
  "Local portrait/landscape rendering and live replay preview",
  "Full-tape PNG/PDF export and portable project archives",
  "Agent chat, project roadmap, and three production paths",
  "Launch installers for Linux, Windows, Apple Silicon, and Intel macOS",
];

const NOW = [
  "Cross-platform launch validation, signing, notarization, and coordinated publishing",
  "Strengthen autonomous project planning",
  "Render evidence inspection and visual repair",
  "Production-path orchestration",
  "Agent evaluation across varied subjects and visual languages",
  "Generalized project catalog and subject-aware examples",
];

const NEXT = [
  "Deeper narration and custom-audio production",
  "Community project publishing",
  "More polished example projects and learning material",
  "Reusable subject kits for domain-specific visual primitives",
];

export function RoadmapPage() {
  return (
    <>
      <section className="page-hero">
        <p className="section-kicker">Project roadmap</p>
        <h1>Built foundation.<br /><span className="text-gradient italic">Ambitious next act.</span></h1>
        <p>
          Matemium is not a concept awaiting an engine. The core creation and rendering
          system exists. The focus now is making the complete production journey more
          autonomous, reliable, and accessible across mathematics, science, computing,
          engineering, humanities, language, and general education.
        </p>
      </section>
      <section className="section-shell pt-0">
        <div className="roadmap-public">
          {[
            ["01", "Built", "The working foundation", COMPLETE, "complete"],
            ["02", "Now", "Launch readiness and agentic production", NOW, "now"],
            ["03", "Next", "Reach and refinement", NEXT, "next"],
          ].map(([number, label, title, items, state]) => (
            <article key={label as string} className={`roadmap-column roadmap-${state}`}>
              <div className="roadmap-column-head">
                <span>{number as string}</span>
                <div><small>{label as string}</small><h2>{title as string}</h2></div>
              </div>
              <ul>
                {(items as string[]).map((item) => <li key={item}><i />{item}</li>)}
              </ul>
            </article>
          ))}
        </div>
        <div className="mt-8 rounded-2xl border border-success/30 bg-success/8 p-6">
          <p className="text-sm leading-6 text-text-muted">
            <strong className="text-text">Cross-platform launch commitment:</strong>{" "}
            the launch release includes Linux <code>.deb</code> and <code>.AppImage</code>,
            Windows <code>.exe</code> and <code>.msi</code>, and separate Apple Silicon
            and Intel macOS <code>.dmg</code> installers. Windows and macOS are launch
            platforms—not post-launch roadmap items.
          </p>
        </div>
        <div className="mt-12 flex flex-wrap items-center justify-between gap-5 rounded-2xl border border-accent/30 bg-accent/8 p-6">
          <p className="max-w-2xl text-sm leading-6 text-text-muted">
            The “Now” stage is where contributions have the greatest effect: agent runs,
            evaluation, visual inspection, and automation require recurring AI resources.
          </p>
          <Link to="/support" className="button-primary">Support this work <span aria-hidden>→</span></Link>
        </div>
      </section>
    </>
  );
}
