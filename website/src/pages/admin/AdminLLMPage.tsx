import { useGetAdminLLMQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/error-alert";
import { Spinner } from "@/components/ui/spinner";

export function AdminLLMPage() {
  const { data, error, isLoading, refetch } = useGetAdminLLMQuery();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted p-4">
        <Spinner /> Loading LLM integration status…
      </div>
    );
  }

  if (error) {
    return <ErrorAlert onRetry={() => void refetch()}>Failed to load LLM status.</ErrorAlert>;
  }

  return (
    <div className="grid gap-5 md:grid-cols-2">
      <Card>
        <h2 className="text-lg font-semibold mb-3">LLM Provider</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-text-subtle">Model</dt>
            <dd className="font-mono">{data?.model}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-subtle">API Base</dt>
            <dd className="font-mono text-xs break-all">{data?.api_base}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-subtle">Stub Mode</dt>
            <dd className={data?.stub ? "text-warning font-medium" : "text-success"}>
              {data?.stub ? "ENABLED (dev only)" : "DISABLED (production)"}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-subtle">System Prompt</dt>
            <dd>{data?.prompt_loaded ? "Loaded" : "Fallback"}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h2 className="text-lg font-semibold mb-3">Usage Metrics</h2>
        <div>
          <p className="text-sm text-text-subtle">Total AI calls (all users)</p>
          <p className="mt-1 text-4xl font-bold tabular-nums">{data?.total_ai_calls ?? 0}</p>
        </div>
        <p className="mt-4 text-xs text-text-subtle">
          Aggregate count from profile counters. Individual user usage available in Users view.
        </p>
      </Card>

      <Card className="md:col-span-2">
        <h3 className="font-semibold">Production Notes</h3>
        <ul className="mt-3 list-disc pl-5 text-sm text-text-muted space-y-1">
          <li>Rate limits are enforced server-side per plan (see rate_limit.py).</li>
          <li>Stub mode must be disabled in production via MATEMIUM_LLM_STUB=false + valid key.</li>
          <li>Manual overrides for individual user AI call counts are available in the Users panel.</li>
        </ul>
      </Card>
    </div>
  );
}
