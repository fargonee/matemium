import { useState } from "react";
import { useGetAdminLLMAutonomousQuery, useGetAdminLLMProvidersQuery, useGetAdminLLMSpendQuery, useUpdateAdminLLMMarginMutation } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/error-alert";
import { Spinner } from "@/components/ui/spinner";

export function AdminLLMPage() {
  const { data: providers = [], error: pErr, isLoading: pLoading, refetch: refetchP } = useGetAdminLLMProvidersQuery();
  const { data: spend, error: sErr, isLoading: sLoading, refetch: refetchS } = useGetAdminLLMSpendQuery();
  const { data: auto, error: aErr, isLoading: aLoading, refetch: refetchA } = useGetAdminLLMAutonomousQuery();

  const [marginInput, setMarginInput] = useState((auto?.margin ?? 0.4) * 100);
  const [updateMargin, { isLoading: updatingMargin }] = useUpdateAdminLLMMarginMutation();

  const loading = pLoading || sLoading || aLoading;
  const error = pErr || sErr || aErr;

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted p-4">
        <Spinner /> Loading LLM management…
      </div>
    );
  }

  if (error) {
    return <ErrorAlert onRetry={() => { refetchP(); refetchS(); refetchA(); }}>Failed to load LLM management data.</ErrorAlert>;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-text-subtle">Our Active Providers</p>
          <p className="mt-1 text-3xl font-bold">{providers.length}</p>
        </Card>
        <Card>
          <p className="text-sm text-text-subtle">Total Platform Spend</p>
          <p className="mt-1 text-3xl font-bold tabular-nums">${spend?.total_cost_usd?.toFixed?.(2) ?? "0.00"}</p>
        </Card>
        <Card>
          <p className="text-sm text-text-subtle">Current Margin</p>
          <p className="mt-1 text-3xl font-bold">{((auto?.margin ?? 0.4) * 100).toFixed(0)}%</p>
          <p className="text-xs text-text-muted">Auto-applied to all platform usage</p>
        </Card>
      </div>

      <Card>
        <h2 className="text-lg font-semibold mb-3">Our Platform LLM Providers</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-text-subtle border-b">
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Base</th>
                <th className="py-2 pr-4">Budget (USD)</th>
                <th className="py-2 pr-4">Auto-replenish</th>
                <th className="py-2">Key</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p: any) => (
                <tr key={p.id} className="border-b border-border/60">
                  <td className="py-2 pr-4 font-medium">{p.name}</td>
                  <td className="py-2 pr-4 font-mono text-xs">{p.api_base}</td>
                  <td className="py-2 pr-4">{p.monthly_budget_usd ?? "—"}</td>
                  <td className="py-2 pr-4">{p.auto_replenish ? "Yes" : "No"}</td>
                  <td className="py-2">{p.has_key ? "Configured" : "Missing"}</td>
                </tr>
              ))}
              {providers.length === 0 && (
                <tr><td colSpan={5} className="py-6 text-center text-text-muted">No platform providers configured yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-text-subtle mt-2">Add providers via API or future admin form. Keys are stored server-side only.</p>
      </Card>

      <Card>
        <h2 className="text-lg font-semibold mb-3">Autonomous Status &amp; Recommendations</h2>
        <pre className="bg-bg-elevated p-4 rounded text-xs overflow-auto">{JSON.stringify(auto, null, 2)}</pre>
        <p className="mt-2 text-xs text-text-muted">
          The system monitors spend vs budgets and can suggest or (in future) trigger replenishment of tokens from providers.
        </p>
      </Card>

      <Card>
        <h2 className="text-lg font-semibold">Pricing Autonomy</h2>
        <div className="flex items-end gap-3 mt-3">
          <div>
            <label className="text-xs text-text-subtle block mb-1">Profit Margin %</label>
            <input
              type="number"
              step="0.1"
              value={marginInput}
              onChange={(e) => setMarginInput(parseFloat(e.target.value))}
              className="border rounded px-3 py-1.5 w-24 text-sm bg-bg"
            />
          </div>
          <button
            onClick={async () => {
              await updateMargin({ marginUpdate: { margin: marginInput / 100 } }).unwrap();
              await refetchA();
            }}
            disabled={updatingMargin}
            className="px-4 py-1.5 rounded bg-accent text-white text-sm disabled:opacity-60"
          >
            {updatingMargin ? "Saving..." : "Save Margin"}
          </button>
        </div>
        <ul className="mt-3 text-sm space-y-1 text-text-muted">
          <li>• Per-model costs in llm_model_pricing table.</li>
          <li>• Platform calls auto calculate cost × (1+margin) for user credit deduction.</li>
          <li>• Set margin once — pricing is fully autonomous after.</li>
        </ul>
      </Card>
    </div>
  );
}
