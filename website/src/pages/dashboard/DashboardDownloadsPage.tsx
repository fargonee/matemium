import { useSelector } from "react-redux";

import { useGetMeQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import type { RootState } from "@/store";

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
  const user = useSelector((state: RootState) => state.auth.user);
  const { data: account } = useGetMeQuery(undefined, { skip: !user });
  const plan = account?.profile.plan ?? "free";
  const hasAccess = plan === "pro" || plan === "teams";

  return (
    <div className="space-y-5">
      <Card>
        <h2 className="text-lg font-semibold">Licensed installers</h2>
        <p className="mt-2 text-sm text-text-muted">
          Downloads are issued to signed-in accounts only. Installers are distributed
          through Matemium Cloud — not public code repositories.
        </p>
        {!hasAccess ? (
          <p className="mt-4 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm">
            Your current plan is <strong>{plan}</strong>. Upgrade to Pro to unlock
            licensed desktop installers when they become available.
          </p>
        ) : null}
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
              {hasAccess ? "Notify when ready" : "Requires Pro plan"}
            </button>
          </Card>
        ))}
      </div>
    </div>
  );
}