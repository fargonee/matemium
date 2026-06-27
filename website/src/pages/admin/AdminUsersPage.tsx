import { useEffect, useState } from "react";

import {
  useGetAdminUsersQuery,
  useGetAdminUserQuery,
  useUpdateAdminUserMutation,
} from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/error-alert";
import { Spinner } from "@/components/ui/spinner";

const PLANS = ["free", "pro", "teams"] as const;
const ROLES = ["user", "admin"] as const;

export function AdminUsersPage() {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editPlan, setEditPlan] = useState<string>("");
  const [editRole, setEditRole] = useState<string>("");
  const [editCalls, setEditCalls] = useState<number>(0);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const { data: rows = [], error, isLoading, refetch } = useGetAdminUsersQuery();

  const { data: detail, isLoading: detailLoading } = useGetAdminUserQuery(
    { userId: selectedId! },
    { skip: !selectedId }
  );

  // Sync edit fields when detailed data arrives
  if (detail && selectedId === detail.id) {
    // Only sync once per selection to avoid loops
  }

  const [updateUser, { isLoading: updating }] = useUpdateAdminUserMutation();

  useEffect(() => {
    if (detail && selectedId === detail.id) {
      setEditCalls(detail.ai_calls_count ?? 0);
    }
  }, [detail, selectedId]);

  const filtered = search
    ? rows.filter(
        (r) =>
          (r.email || "").toLowerCase().includes(search.toLowerCase()) ||
          (r.full_name || "").toLowerCase().includes(search.toLowerCase())
      )
    : rows;

  function selectUser(id: string, currentPlan: string, currentRole: string, calls?: number) {
    setSelectedId(id);
    setEditPlan(currentPlan);
    setEditRole(currentRole);
    setEditCalls(calls ?? 0);
    setActionMsg(null);
  }

  async function saveChanges() {
    if (!selectedId) return;
    setActionMsg(null);
    try {
      await updateUser({
        userId: selectedId,
        updateUserRequest: {
          plan: editPlan,
          role: editRole,
          ai_calls_count: editCalls,
        },
      }).unwrap();
      setActionMsg("User updated successfully.");
      void refetch();
    } catch (e: any) {
      setActionMsg("Update failed: " + (e?.data?.detail || e?.message || "Unknown error"));
    }
  }

  async function resetUsage() {
    if (!selectedId) return;
    if (!confirm("Reset AI calls count to 0 for this user?")) return;
    setActionMsg(null);
    try {
      await updateUser({
        userId: selectedId,
        updateUserRequest: { ai_calls_count: 0 },
      }).unwrap();
      setEditCalls(0);
      setActionMsg("Usage reset to 0.");
      void refetch();
    } catch (e: any) {
      setActionMsg("Reset failed: " + (e?.data?.detail || "error"));
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted p-4">
        <Spinner /> Loading users…
      </div>
    );
  }

  if (error) {
    return <ErrorAlert onRetry={() => void refetch()}>Failed to load users.</ErrorAlert>;
  }

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-border bg-bg-elevated px-4 py-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search email or name…"
            className="w-64 rounded border border-border bg-bg px-3 py-1.5 text-sm placeholder:text-text-subtle focus:outline-none"
          />
          <span className="text-xs text-text-subtle">{filtered.length} shown</span>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-border bg-bg-elevated text-text-subtle">
              <tr>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Plan</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Joined</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => {
                const isSelected = selectedId === row.id;
                return (
                  <tr
                    key={row.id}
                    className={`border-b border-border/70 cursor-pointer hover:bg-bg-elevated/50 ${isSelected ? "bg-accent/10" : ""}`}
                    onClick={() => selectUser(row.id, row.plan, row.role, (row as any).ai_calls_count)}
                  >
                    <td className="px-4 py-3">{row.email}</td>
                    <td className="px-4 py-3">{row.full_name ?? "—"}</td>
                    <td className="px-4 py-3 capitalize">{row.plan}</td>
                    <td className="px-4 py-3 capitalize">{row.role}</td>
                    <td className="px-4 py-3 text-text-muted">
                      {row.created_at ? new Date(row.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        className="text-xs rounded border border-border-strong px-2 py-0.5 hover:bg-bg"
                        onClick={(e) => {
                          e.stopPropagation();
                          selectUser(row.id, row.plan, row.role, (row as any).ai_calls_count);
                        }}
                      >
                        Manage
                      </button>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-text-muted">
                    No matching users.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>

      {selectedId && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Manage User: {detail?.email || selectedId}</h3>
            {detailLoading && <Spinner />}
          </div>

          {detail && (
            <div className="grid gap-4 md:grid-cols-2 text-sm mb-4">
              <div>
                <div className="text-text-subtle">Current Plan</div>
                <div className="font-medium capitalize">{detail.plan}</div>
              </div>
              <div>
                <div className="text-text-subtle">Role</div>
                <div className="font-medium capitalize">{detail.role}</div>
              </div>
              <div>
                <div className="text-text-subtle">AI Calls</div>
                <div className="font-medium tabular-nums">{detail.ai_calls_count ?? 0}</div>
              </div>
              <div>
                <div className="text-text-subtle">Subscription</div>
                <div>{detail.subscription?.status ?? "—"} / {detail.subscription?.plan ?? "—"}</div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
            <div>
              <label className="block text-xs text-text-subtle mb-1">Plan</label>
              <select
                value={editPlan}
                onChange={(e) => setEditPlan(e.target.value)}
                className="w-full rounded border border-border bg-bg px-3 py-1.5 text-sm"
              >
                {PLANS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-subtle mb-1">Role</label>
              <select
                value={editRole}
                onChange={(e) => setEditRole(e.target.value)}
                className="w-full rounded border border-border bg-bg px-3 py-1.5 text-sm"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-subtle mb-1">AI Calls Count (override)</label>
              <input
                type="number"
                value={editCalls}
                onChange={(e) => setEditCalls(parseInt(e.target.value || "0"))}
                className="w-full rounded border border-border bg-bg px-3 py-1.5 text-sm"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={saveChanges}
              disabled={updating}
              className="rounded-full bg-accent px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {updating ? "Saving..." : "Save Changes"}
            </button>
            <button
              onClick={resetUsage}
              disabled={updating}
              className="rounded-full border border-warning px-4 py-1.5 text-sm font-medium hover:bg-warning/10"
            >
              Reset Usage to 0
            </button>
            <button onClick={() => setSelectedId(null)} className="text-sm text-text-muted">
              Close
            </button>
          </div>

          {actionMsg && (
            <div className="mt-3 text-sm text-success">{actionMsg}</div>
          )}
        </Card>
      )}
    </div>
  );
}
