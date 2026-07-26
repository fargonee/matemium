import { Link } from "react-router-dom";

const COMPLETE = [
  "Infinite-sheet layout and animation engine",
  "2D and real 3D composition",
  "Desktop editor, project workspaces, and live preview",
  "Local rendering, static export, and reel cutting",
  "Agent chat, project roadmap, and decision workflow",
  "Linux packaging and bundled rendering engine",
];

const NOW = [
  "Strengthen autonomous project planning",
  "Render evidence inspection and visual repair",
  "Production-path orchestration",
  "Agent evaluation across varied subjects and visual languages",
  "Generalized project catalog and subject-aware examples",
];

const NEXT = [
  "Windows and macOS release paths",
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
            ["02", "Now", "Agentic production", NOW, "now"],
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
