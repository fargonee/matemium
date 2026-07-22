import { useGetAdminLLMSpendQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/error-alert";
import { Spinner } from "@/components/ui/spinner";

export function AdminLLMPage() {
  const { data: spend, error, isLoading, refetch } = useGetAdminLLMSpendQuery();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-4 text-sm text-text-muted">
        <Spinner /> Loading provider telemetry…
      </div>
    );
  }

  if (error) {
    return <ErrorAlert onRetry={() => void refetch()}>Failed to load provider telemetry.</ErrorAlert>;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-text-subtle">Provider mode</p>
          <p className="mt-1 text-3xl font-bold">BYO</p>
        </Card>
        <Card>
          <p className="text-sm text-text-subtle">Recorded calls</p>
          <p className="mt-1 text-3xl font-bold tabular-nums">{spend?.call_count ?? 0}</p>
        </Card>
        <Card>
          <p className="text-sm text-text-subtle">Estimated provider cost</p>
          <p className="mt-1 text-3xl font-bold tabular-nums">
            ${spend?.total_cost_usd?.toFixed?.(2) ?? "0.00"}
          </p>
        </Card>
      </div>

      <Card>
        <h2 className="text-lg font-semibold">AI Access Policy</h2>
        <p className="mt-2 text-sm text-text-muted">
          Matemium does not maintain shared model pools, set resale margins,
          or deduct in-app AI credits. External AI uses user-owned
          provider keys, with OpenRouter as the default provider.
        </p>
      </Card>
    </div>
  );
}
