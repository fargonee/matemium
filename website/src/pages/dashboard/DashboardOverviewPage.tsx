import { Link } from "react-router-dom";
import { useSelector } from "react-redux";

import { useGetMeQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/error-alert";
import { Spinner } from "@/components/ui/spinner";
import type { RootState } from "@/store";

export function DashboardOverviewPage() {
  const user = useSelector((state: RootState) => state.auth.user);
  const { data: account, isLoading, error, refetch } = useGetMeQuery(undefined, { skip: !user });
  const plan = account?.profile.plan ?? "free";
  const aiCalls = account?.usage?.ai_calls_count ?? 0;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted">
        <Spinner /> Loading…
      </div>
    );
  }

  if (error) {
    return <ErrorAlert onRetry={() => void refetch()}>Failed to load dashboard.</ErrorAlert>;
  }

  return (
    <div className="grid gap-5 md:grid-cols-3">
      <Card>
        <p className="text-sm text-text-subtle">Current plan</p>
        <p className="mt-1 text-2xl font-bold capitalize">{plan}</p>
        <Link to="/dashboard/billing" className="mt-4 inline-block text-sm font-medium">
          Manage billing →
        </Link>
      </Card>
      <Card>
        <p className="text-sm text-text-subtle">AI interactions</p>
        <p className="mt-1 text-2xl font-bold tabular-nums">{aiCalls}</p>
        <Link to="/dashboard/usage" className="mt-4 inline-block text-sm font-medium">
          View usage →
        </Link>
      </Card>
      <Card>
        <p className="text-sm text-text-subtle">Desktop app</p>
        <p className="mt-1 text-2xl font-bold">Licensed</p>
        <Link to="/dashboard/downloads" className="mt-4 inline-block text-sm font-medium">
          Get installers →
        </Link>
      </Card>
      <Card className="md:col-span-3">
        <p className="text-sm text-text-subtle">Account email</p>
        <p className="mt-1 text-lg font-medium">{user?.email}</p>
      </Card>
    </div>
  );
}