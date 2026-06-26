import { useGetAdminUsersQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";

export function AdminUsersPage() {
  const { data: rows = [], error } = useGetAdminUsersQuery();

  if (error) {
    return (
      <Card className="border-red-500/40 bg-red-500/5 p-4 text-sm text-red-300">
        Failed to load users. You may not have admin access on the server (MATEMIUM_ADMIN_EMAILS) or the API token is not being sent.
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-border bg-bg-elevated text-text-subtle">
            <tr>
              <th className="px-4 py-3 font-medium">Email</th>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Joined</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-border/70">
                <td className="px-4 py-3">{row.email}</td>
                <td className="px-4 py-3">{row.full_name ?? "—"}</td>
                <td className="px-4 py-3 capitalize">{row.plan}</td>
                <td className="px-4 py-3 capitalize">{row.role}</td>
                <td className="px-4 py-3 text-text-muted">
                  {row.created_at ? new Date(row.created_at).toLocaleDateString() : "—"}
                </td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-muted">
                  No users yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </Card>
  );
}