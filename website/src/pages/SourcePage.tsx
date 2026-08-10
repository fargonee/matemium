import { Link } from "react-router-dom";

const PERMITTED = [
  "Personal, educational, research, nonprofit, and internal organizational use",
  "Inspection and study of the source code",
  "Private modifications and experiments",
  "Forks made to prepare contributions to the official project",
  "Commercial use of the videos, lessons, and other content you create",
];

export function SourcePage() {
  return (
    <>
      <section className="page-hero">
        <p className="section-kicker">Source & license</p>
        <h1>Open to inspect.<br /><span className="text-gradient italic">Built to contribute.</span></h1>
        <p>
          Matemium’s implementation is visible under the Matemium Source-Available
          License. Learn from it, use it for permitted purposes, modify it privately,
          and help improve a visual reasoning engine designed to grow across subjects.
        </p>
        <div className="mt-9 flex flex-wrap justify-center gap-3">
          <a href="https://github.com/fargonee/matemium" target="_blank" rel="noreferrer" className="button-primary">
            Browse the repository <span aria-hidden>↗</span>
          </a>
          <Link to="/license" className="button-secondary">Read the full license</Link>
        </div>
      </section>
      <section className="section-shell pt-0">
        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <article className="rounded-3xl border border-border bg-bg-card p-8 md:p-12">
            <p className="section-kicker">In plain language</p>
            <h2 className="font-display text-4xl">What the license welcomes.</h2>
            <ul className="mt-8 space-y-4">
              {PERMITTED.map((item) => (
                <li key={item} className="flex gap-3 text-sm leading-6 text-text-muted">
                  <span className="check mt-0.5 shrink-0">✓</span>{item}
                </li>
              ))}
            </ul>
          </article>
          <article className="rounded-3xl border border-border bg-bg-elevated p-8 md:p-12">
            <p className="section-kicker">Important distinction</p>
            <h2 className="font-display text-4xl">Your creations remain yours.</h2>
            <p className="mt-6 leading-7 text-text-muted">
              The license restricts redistribution and commercial exploitation of the
              Matemium software itself. It does not claim ownership of the lessons, videos,
              scripts, images, or educational material you produce with Matemium.
            </p>
          </article>
        </div>
        <p className="mx-auto mt-10 max-w-3xl text-center text-xs leading-5 text-text-subtle">
          This summary is provided for orientation and does not replace the full license text.
        </p>
      </section>
    </>
  );
}
