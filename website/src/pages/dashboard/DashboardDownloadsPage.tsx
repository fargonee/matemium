import { Card } from "@/components/ui/card";

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
];

export function DashboardDownloadsPage() {
  return (
    <div className="space-y-5">
      <Card>
        <h2 className="text-lg font-semibold">Installers</h2>
        <p className="mt-2 text-sm text-text-muted">
          Matemium is free to use. Linux, Windows, Apple Silicon macOS, and Intel
          macOS installers all publish with the launch release. GitHub Releases is
          authoritative for artifacts currently available to download.
        </p>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        {PLATFORMS.map((platform) => (
          <Card key={platform.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold">{platform.name}</h3>
                <p className="text-xs text-text-subtle">{platform.meta}</p>
              </div>
              <span className="rounded-full bg-success/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-success">
                {platform.status}
              </span>
            </div>
            <p className="mt-3 text-sm text-text-muted">{platform.note}</p>
            <a
              href="https://github.com/fargonee/math/releases"
              target="_blank"
              rel="noreferrer"
              className="mt-5 block w-full rounded-[10px] border border-border-strong px-4 py-2.5 text-center text-sm font-semibold text-text-muted hover:border-accent hover:text-text"
            >
              Check releases ↗
            </a>
          </Card>
        ))}
      </div>
    </div>
  );
}
