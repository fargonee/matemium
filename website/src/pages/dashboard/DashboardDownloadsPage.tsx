import { useEffect, useState } from "react";

import { Card } from "@/components/ui/card";
import {
  formatReleaseDate,
  getPlatformLinks,
  getReleasesUrl,
  loadLatestRelease,
  type DownloadPlatform,
  type LatestRelease,
} from "@/lib/githubReleases";

const PLATFORMS = [
  {
    id: "linux",
    name: "Linux",
    meta: "Ubuntu 24.04+ · x86_64",
    status: "At launch",
    note: ".deb and .AppImage installers with the native sidecar.",
  },
  {
    id: "windows",
    name: "Windows",
    meta: "Windows 10/11 · x86_64",
    status: "At launch",
    note: "Native NSIS .exe and .msi installers; unsigned builds may trigger SmartScreen.",
  },
  {
    id: "macos",
    name: "macOS",
    meta: "macOS 12+ · Apple Silicon & Intel",
    status: "At launch",
    note: "Separate Apple Silicon and Intel .dmg installers.",
  },
] satisfies Array<{
  id: DownloadPlatform;
  name: string;
  meta: string;
  status: string;
  note: string;
}>;

export function DashboardDownloadsPage() {
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
    <div className="space-y-5">
      <Card>
        <h2 className="text-lg font-semibold">Installers</h2>
        <p className="mt-2 text-sm text-text-muted">
          Matemium is free to use. This page reads the latest published GitHub
          Release and lists the assets currently available to download.
        </p>
        <p className="mt-3 text-xs text-text-subtle">
          {release
            ? `Latest release: ${release.name}${release.publishedAt ? ` · ${formatReleaseDate(release.publishedAt)}` : ""}`
            : loaded
              ? "No published release assets found yet."
              : "Checking latest release..."}
        </p>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        {PLATFORMS.map((platform) => {
          const links = getPlatformLinks(release, platform.id);
          return (
          <Card key={platform.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold">{platform.name}</h3>
                <p className="text-xs text-text-subtle">{platform.meta}</p>
              </div>
              <span className="rounded-full bg-success/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-success">
                {links.length ? "Available" : platform.status}
              </span>
            </div>
            <p className="mt-3 text-sm text-text-muted">{platform.note}</p>
            <div className="mt-5 grid gap-2">
              {links.length ? links.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  rel="noreferrer"
                  className="block w-full rounded-[10px] border border-border-strong px-4 py-2.5 text-center text-sm font-semibold text-text-muted hover:border-accent hover:text-text"
                >
                  {link.label}{link.sizeLabel ? ` · ${link.sizeLabel}` : ""}
                </a>
              )) : (
                <a
                  href={release?.htmlUrl || getReleasesUrl()}
                  target="_blank"
                  rel="noreferrer"
                  className="block w-full rounded-[10px] border border-border-strong px-4 py-2.5 text-center text-sm font-semibold text-text-muted hover:border-accent hover:text-text"
                >
                  Check releases ↗
                </a>
              )}
            </div>
          </Card>
          );
        })}
      </div>
    </div>
  );
}
