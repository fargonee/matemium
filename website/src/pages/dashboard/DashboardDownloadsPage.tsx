import { Card } from "@/components/ui/card";

const PLATFORMS = [
  {
    id: "linux",
    name: "Linux",
    meta: "Ubuntu 22.04+ · x86_64",
    status: "Early access",
    note: "Native installer with bundled rendering engine.",
  },
  {
    id: "windows",
    name: "Windows",
    meta: "Windows 10/11 · x86_64",
    status: "Coming soon",
    note: "Signed MSI/EXE installer with bundled engine.",
  },
  {
    id: "macos",
    name: "macOS",
    meta: "Apple Silicon & Intel",
    status: "Coming soon",
    note: "Universal DMG with native engine binaries.",
  },
];

export function DashboardDownloadsPage() {
  return (
    <div className="space-y-5">
      <Card>
        <h2 className="text-lg font-semibold">Installers</h2>
        <p className="mt-2 text-sm text-text-muted">
          Matemium is free to use. Installers are distributed to signed-in accounts while
          builds are staged for each platform.
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
              <span className="rounded-full bg-warning/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-warning">
                {platform.status}
              </span>
            </div>
            <p className="mt-3 text-sm text-text-muted">{platform.note}</p>
            <button
              type="button"
              disabled
              className="mt-5 w-full rounded-[10px] border border-border-strong px-4 py-2.5 text-sm font-semibold text-text-muted opacity-60"
            >
              Notify when ready
            </button>
          </Card>
        ))}
      </div>
    </div>
  );
}
