import { useEffect, useState } from "react";

import {
  formatReleaseDate,
  getPlatformLinks,
  getReleasesUrl,
  loadLatestRelease,
  type DownloadPlatform,
  type DownloadLink,
  type LatestRelease,
} from "@/lib/githubReleases";

const PLATFORMS = [
  {
    id: "linux",
    platform: "Linux",
    detail: "Ubuntu 24.04+ · x86_64",
    body: "At launch: .deb and .AppImage installers with the Matemium UI, Rust shell, and native sidecar.",
  },
  {
    id: "windows",
    platform: "Windows",
    detail: "Windows 10/11 · x86_64",
    body: "At launch: native NSIS .exe and .msi installers. Unsigned builds may show a SmartScreen warning.",
  },
  {
    id: "macos",
    platform: "macOS",
    detail: "macOS 12+ · Apple Silicon & Intel",
    body: "At launch: separate .dmg installers for Apple Silicon and Intel. Notarization depends on release credentials.",
  },
] satisfies Array<{
  id: DownloadPlatform;
  platform: string;
  detail: string;
  body: string;
}>;

export function DownloadPage() {
  const [release, setRelease] = useState<LatestRelease | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    loadLatestRelease().then((latest) => {
      if (!active) return;
      setRelease(latest);
      setLoaded(true);
    });
    return () => {
      active = false;
    };
  }, []);

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
        <div className="mx-auto mb-8 max-w-3xl rounded-3xl border border-border bg-bg-card p-5 text-center">
          <p className="text-sm font-semibold">
            {release ? `Latest release: ${release.name}` : loaded ? "Downloads publish through GitHub Releases" : "Checking latest release..."}
          </p>
          <p className="mt-2 text-xs text-text-subtle">
            {release?.publishedAt
              ? `Published ${formatReleaseDate(release.publishedAt)}. Links below update automatically from release assets.`
              : "If direct links are not shown yet, use GitHub Releases while the release is being published."}
          </p>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {PLATFORMS.map((item) => {
            const links = getPlatformLinks(release, item.id);
            return (
            <article key={item.platform} className="download-card">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-semibold">{item.platform}</h2>
                  <p className="mt-1 text-xs text-text-subtle">{item.detail}</p>
                </div>
                <span className={`release-status ${links.length ? "available" : "progress"}`}>
                  {links.length ? "Available" : "Release"}
                </span>
              </div>
              <p className="mt-8 min-h-20 leading-7 text-text-muted">{item.body}</p>
              <DownloadLinks links={links} fallbackHref={release?.htmlUrl || getReleasesUrl()} />
            </article>
            );
          })}
        </div>
        <p className="mx-auto mt-6 max-w-3xl text-center text-xs leading-5 text-text-subtle">
          Direct download buttons are generated from the latest published GitHub
          Release assets. Draft releases and Actions artifacts are intentionally
          not exposed as stable public downloads.
        </p>
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

function DownloadLinks({
  links,
  fallbackHref,
}: {
  links: DownloadLink[];
  fallbackHref: string;
}) {
  if (!links.length) {
    return (
      <a
        href={fallbackHref}
        target="_blank"
        rel="noreferrer"
        className="button-primary mt-8 w-full"
      >
        Check GitHub releases <span aria-hidden>↗</span>
      </a>
    );
  }

  return (
    <div className="mt-8 grid gap-2">
      {links.map((link) => (
        <a
          key={link.href}
          href={link.href}
          className="download-link"
          rel="noreferrer"
        >
          <span>{link.label}</span>
          {link.sizeLabel ? <small>{link.sizeLabel}</small> : null}
        </a>
      ))}
    </div>
  );
}
