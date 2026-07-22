import { useSelector } from "react-redux";

import { useGetMeQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/error-alert";
import { Spinner } from "@/components/ui/spinner";
import type { RootState } from "@/store";

export function DashboardUsagePage() {
  const user = useSelector((state: RootState) => state.auth.user);
  const { data: account, isLoading, error, refetch } = useGetMeQuery(undefined, { skip: !user });

  const usage = account?.usage;
  const ai = usage?.ai_calls_count ?? 0;

  const limit = 500;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted">
        <Spinner /> Loading usage…
      </div>
    );
  }

  if (error) {
    return <ErrorAlert onRetry={() => void refetch()}>Failed to load usage data.</ErrorAlert>;
  }

  return (
    <div className="grid gap-5 md:grid-cols-2">
      <Card>
        <p className="text-sm text-text-subtle">AI access</p>
        <p className="mt-2 text-4xl font-bold tabular-nums">BYO</p>
        <p className="text-xs text-text-muted mt-1">External AI uses your connected provider account. Local models run on your computer.</p>
      </Card>

      <Card>
        <p className="text-sm text-text-subtle">AI interactions (legacy counter)</p>
        <p className="mt-2 text-4xl font-bold tabular-nums">{ai}</p>
        <p className="mt-1 text-sm text-text-muted">
          of ~{limit} this period (approximate). Rate limiting protects the shared service, not paid tiers.
        </p>
        <div className="mt-4 h-2 w-full rounded bg-border">
          <div
            className="h-2 rounded bg-accent"
            style={{ width: `${Math.min(100, Math.round((ai / Math.max(1, limit)) * 100))}%` }}
          />
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold">How usage works</h3>
        <ul className="mt-3 space-y-2 text-sm text-text-muted">
          <li>• Each AI chat turn in the desktop increments the counter.</li>
          <li>• Limits are soft guidance; hard rate-limiting protects the service.</li>
          <li>• Usage data is refreshed from your account on each dashboard load.</li>
          <li>• Provider costs and limits are controlled by your chosen AI provider.</li>
        </ul>
        <a href="/dashboard/account" className="mt-4 inline-block text-sm font-medium">
          Manage provider keys →
        </a>
      </Card>
    </div>
  );
}
