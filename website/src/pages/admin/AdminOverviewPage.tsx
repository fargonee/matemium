import { useGetAdminStatsQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";

export function AdminOverviewPage() {
  const { data: stats } = useGetAdminStatsQuery();

  return (
    <div className="grid gap-4 md:grid-cols-3">
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
    </div>
  );
}