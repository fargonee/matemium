import { Link } from "react-router-dom";

const PLATFORMS = [
  {
    platform: "Linux",
    detail: "Ubuntu 22.04+ · x86_64",
    status: "Early access",
    statusClass: "available",
    body: "The complete desktop studio and bundled local rendering engine.",
  },
  {
    platform: "Windows",
    detail: "Windows 10/11 · x86_64",
    status: "In progress",
    statusClass: "progress",
    body: "Native installer work is underway. Follow the roadmap for release progress.",
  },
  {
    platform: "macOS",
    detail: "Apple Silicon & Intel",
    status: "In progress",
    statusClass: "progress",
    body: "Universal desktop packaging is planned after the Windows release path.",
  },
];

export function DownloadPage() {
  return (
    <>
      <section className="page-hero">
        <p className="section-kicker">Get Matemium</p>
        <h1>Free to create.<br /><span className="text-gradient italic">Built to stay local.</span></h1>
        <p>
          Matemium has no subscription, paid tier, or in-app AI credits. Rendering
          happens on your computer; optional AI uses your provider account or local model.
        </p>
      </section>
      <section className="section-shell pt-0">
        <div className="grid gap-5 md:grid-cols-3">
          {PLATFORMS.map((item) => (
            <article key={item.platform} className="download-card">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-semibold">{item.platform}</h2>
                  <p className="mt-1 text-xs text-text-subtle">{item.detail}</p>
                </div>
                <span className={`release-status ${item.statusClass}`}>{item.status}</span>
              </div>
              <p className="mt-8 min-h-20 leading-7 text-text-muted">{item.body}</p>
              {item.platform === "Linux" ? (
                <Link to="/login?next=/dashboard/downloads" className="button-primary mt-8 w-full">
                  Sign in for installer <span aria-hidden>→</span>
                </Link>
              ) : (
                <Link to="/roadmap" className="button-secondary mt-8 w-full">Follow progress</Link>
              )}
            </article>
          ))}
        </div>
        <div className="mt-12 grid gap-8 border-t border-border pt-12 md:grid-cols-3">
          {[
            ["Everything local", "Project files, Manim rendering, LaTeX, and video encoding remain on your machine."],
            ["Bring your own AI", "Connect OpenRouter or another supported provider, or use a compatible local model."],
            ["Source-available", "Inspect the implementation, learn from it, modify privately, and contribute upstream."],
          ].map(([title, body]) => (
            <div key={title}>
              <h3 className="font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-text-muted">{body}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
