import { Link } from "react-router-dom";

import { useGetAdminStatsQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/error-alert";
import { Spinner } from "@/components/ui/spinner";

export function AdminOverviewPage() {
  const { data: stats, error, isLoading, refetch } = useGetAdminStatsQuery();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted p-4">
        <Spinner /> Loading stats…
      </div>
    );
  }

  if (error) {
    return <ErrorAlert onRetry={() => void refetch()}>Failed to load admin stats.</ErrorAlert>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <p className="text-sm text-text-subtle">Total users</p>
        <p className="mt-1 text-3xl font-bold">{stats?.total_users ?? 0}</p>
      </Card>
      <Card>
        <p className="text-sm text-text-subtle">Pro accounts</p>
        <p className="mt-1 text-3xl font-bold">{stats?.pro_users ?? 0}</p>
      </Card>
      <Card>
        <p className="text-sm text-text-subtle">Active subscriptions</p>
        <p className="mt-1 text-3xl font-bold">{stats?.active_subscriptions ?? 0}</p>
      </Card>
      <Card>
        <p className="text-sm text-text-subtle">LLM &amp; Usage</p>
        <p className="mt-1 text-xl font-semibold">Manage integrations</p>
        <Link to="/admin/llm" className="mt-2 inline-block text-sm font-medium">Open LLM panel →</Link>
      </Card>
    </div>
  );
}