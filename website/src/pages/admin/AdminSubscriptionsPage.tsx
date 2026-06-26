import { useGetAdminSubscriptionsQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";

export function AdminSubscriptionsPage() {
  const { data: rows = [], error } = useGetAdminSubscriptionsQuery();

  if (error) {
    return (
      <Card className="border-red-500/40 bg-red-500/5 p-4 text-sm text-red-300">
        Failed to load subscriptions. Admin access required on the backend.
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-border bg-bg-elevated text-text-subtle">
            <tr>
              <th className="px-4 py-3 font-medium">User ID</th>
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Lemon sub</th>
              <th className="px-4 py-3 font-medium">Period end</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-border/70">
                <td className="px-4 py-3 font-mono text-xs">{row.user_id.slice(0, 8)}…</td>
                <td className="px-4 py-3 capitalize">{row.plan}</td>
                <td className="px-4 py-3 capitalize">{row.status}</td>
                <td className="px-4 py-3 font-mono text-xs">
                  {row.lemon_subscription_id?.slice(0, 14) ?? "—"}…
                </td>
                <td className="px-4 py-3 text-text-muted">
                  {row.current_period_end
                    ? new Date(row.current_period_end).toLocaleDateString()
                    : "—"}
                </td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-muted">
                  No subscriptions yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </Card>
  );
}