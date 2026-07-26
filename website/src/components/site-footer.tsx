import { Link } from "react-router-dom";

const GROUPS = [
  {
    title: "Explore",
    links: [["Showcase", "/showcase"], ["Download", "/download"], ["Roadmap", "/roadmap"], ["Support", "/support"]],
  },
  {
    title: "Project",
    links: [["Source & license", "/source"], ["GitHub", "https://github.com/fargonee/math"], ["Contributing", "https://github.com/fargonee/math/blob/main/CONTRIBUTING.md"], ["Sign in", "/login"]],
  },
  {
    title: "Legal",
    links: [["Privacy", "/privacy"], ["Terms", "/terms"], ["Refunds", "/refund"], ["Software license", "/license"], ["Acceptable use", "/acceptable-use"]],
  },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-[#080a0e] px-5 py-16">
      <div className="mx-auto grid max-w-7xl gap-12 md:grid-cols-[1.25fr_2fr]">
        <div>
          <Link to="/" className="brand-link">
            <img src="/assets/matemium-logo-180.png" alt="" width={34} height={34} />
            <span>Matemium</span>
          </Link>
          <p className="mt-5 max-w-sm text-sm leading-6 text-text-subtle">
            A free, source-available agentic studio for turning complex ideas into
            structured visual stories.
          </p>
          <p className="mt-8 text-xs text-text-subtle">© 2026 Matemium contributors.</p>
        </div>
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
          {GROUPS.map((group) => (
            <div key={group.title}>
              <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">{group.title}</h2>
              <div className="flex flex-col gap-3">
                {group.links.map(([label, href]) =>
                  href.startsWith("http") ? (
                    <a key={label} href={href} target="_blank" rel="noreferrer" className="footer-link">{label}</a>
                  ) : (
                    <Link key={label} to={href} className="footer-link">{label}</Link>
                  ),
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </footer>
  );
}
