import { Link } from "react-router-dom";
import { useSelector } from "react-redux";

import { useGetMeQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import type { RootState } from "@/store";

export function DashboardOverviewPage() {
  const user = useSelector((state: RootState) => state.auth.user);
  const { data: account } = useGetMeQuery(undefined, { skip: !user });
  const plan = account?.profile.plan ?? "free";

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
        <p className="text-sm text-text-subtle">Desktop app</p>
        <p className="mt-1 text-2xl font-bold">Licensed</p>
        <Link to="/dashboard/downloads" className="mt-4 inline-block text-sm font-medium">
          Get installers →
        </Link>
      </Card>
      <Card>
        <p className="text-sm text-text-subtle">Account email</p>
        <p className="mt-1 text-lg font-medium">{user?.email}</p>
      </Card>
    </div>
  );
}