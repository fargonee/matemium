import { useState } from "react";

import {
  useGetAdminSubscriptionsQuery,
  useUpdateAdminSubscriptionMutation,
} from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/error-alert";
import { Spinner } from "@/components/ui/spinner";

export function AdminSubscriptionsPage() {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState("");
  const [editPlan, setEditPlan] = useState("");
  const [editPeriod, setEditPeriod] = useState("");
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const { data: rows = [], error, isLoading, refetch } = useGetAdminSubscriptionsQuery();
  const [updateSub, { isLoading: updating }] = useUpdateAdminSubscriptionMutation();

  const filtered = search
    ? rows.filter(
        (r) =>
          (r.user_id || "").toLowerCase().includes(search.toLowerCase()) ||
          (r.lemon_subscription_id || "").toLowerCase().includes(search.toLowerCase())
      )
    : rows;

  function selectSub(row: any) {
    setSelectedId(row.id);
    setEditStatus(row.status || "active");
    setEditPlan(row.plan || "pro");
    setEditPeriod(row.current_period_end || "");
    setActionMsg(null);
  }

  async function saveSub() {
    if (!selectedId) return;
    setActionMsg(null);
    try {
      await updateSub({
        subscriptionId: selectedId,
        updateSubscriptionRequest: {
          status: editStatus,
          plan: editPlan,
          current_period_end: editPeriod || null,
        },
      }).unwrap();
      setActionMsg("Subscription updated.");
      void refetch();
    } catch (e: any) {
      setActionMsg("Update failed: " + (e?.data?.detail || "error"));
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted p-4">
        <Spinner /> Loading subscriptions…
      </div>
    );
  }

  if (error) {
    return <ErrorAlert onRetry={() => void refetch()}>Failed to load subscriptions.</ErrorAlert>;
  }

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-border bg-bg-elevated px-4 py-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search user or lemon id…"
            className="w-64 rounded border border-border bg-bg px-3 py-1.5 text-sm placeholder:text-text-subtle focus:outline-none"
          />
          <span className="text-xs text-text-subtle">{filtered.length} shown</span>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-border bg-bg-elevated text-text-subtle">
              <tr>
                <th className="px-4 py-3 font-medium">User ID</th>
                <th className="px-4 py-3 font-medium">Plan</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Lemon sub</th>
                <th className="px-4 py-3 font-medium">Period end</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => selectSub(row)}
                  className={`border-b border-border/70 cursor-pointer hover:bg-bg-elevated/50 ${selectedId === row.id ? "bg-accent/10" : ""}`}
                >
                  <td className="px-4 py-3 font-mono text-xs">{row.user_id.slice(0, 8)}…</td>
                  <td className="px-4 py-3 capitalize">{row.plan}</td>
                  <td className="px-4 py-3 capitalize">{row.status}</td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {row.lemon_subscription_id?.slice(0, 14) ?? "—"}…
                  </td>
                  <td className="px-4 py-3 text-text-muted">
                    {row.current_period_end ? new Date(row.current_period_end).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <button className="text-xs border px-2 py-0.5 rounded" onClick={(e) => { e.stopPropagation(); selectSub(row); }}>Edit</button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-text-muted">No matching subscriptions.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {selectedId && (
        <Card>
          <h3 className="font-semibold mb-3">Edit Subscription {selectedId}</h3>
          <div className="grid md:grid-cols-3 gap-3 mb-4 text-sm">
            <div>
              <label className="block text-xs text-text-subtle">Status</label>
              <input value={editStatus} onChange={e => setEditStatus(e.target.value)} className="w-full border rounded bg-bg px-3 py-1.5" />
            </div>
            <div>
              <label className="block text-xs text-text-subtle">Plan</label>
              <input value={editPlan} onChange={e => setEditPlan(e.target.value)} className="w-full border rounded bg-bg px-3 py-1.5" />
            </div>
            <div>
              <label className="block text-xs text-text-subtle">Current Period End (ISO)</label>
              <input value={editPeriod} onChange={e => setEditPeriod(e.target.value)} className="w-full border rounded bg-bg px-3 py-1.5" placeholder="2026-12-31T00:00:00Z" />
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={saveSub} disabled={updating} className="bg-accent text-white px-4 py-1.5 rounded-full text-sm font-medium disabled:opacity-60">
              {updating ? "Saving…" : "Save Subscription"}
            </button>
            <button onClick={() => setSelectedId(null)} className="text-sm">Close</button>
          </div>
          {actionMsg && <p className="mt-3 text-sm text-success">{actionMsg}</p>}
        </Card>
      )}
    </div>
  );
}
