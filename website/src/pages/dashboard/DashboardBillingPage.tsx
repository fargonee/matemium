import { Link } from "react-router-dom";

import { Card } from "@/components/ui/card";

export function DashboardBillingPage() {
  return (
    <div className="max-w-2xl">
      <Card>
        <h2 className="text-lg font-semibold">No billing required</h2>
        <p className="mt-2 text-sm text-text-muted">
          Matemium is free to use. There are no subscriptions, paid tiers, or
          Matemium AI credits.
        </p>
        <p className="mt-3 text-sm text-text-muted">
          External AI uses your connected provider account. OpenRouter is the
          default provider, and local models remain available for offline use.
        </p>
        <Link to="/dashboard/account" className="mt-5 inline-block text-sm font-medium">
          Manage provider keys →
        </Link>
      </Card>
    </div>
  );
}
