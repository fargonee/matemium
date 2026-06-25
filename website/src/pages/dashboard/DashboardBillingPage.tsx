import { Link } from "react-router-dom";
import { useSelector } from "react-redux";

import { useGetMeQuery } from "@/api/matemiumApi";
import { ManageBillingButton } from "@/components/manage-billing-button";
import { Card } from "@/components/ui/card";
import type { RootState } from "@/store";

export function DashboardBillingPage() {
  const user = useSelector((state: RootState) => state.auth.user);
  const { data: account } = useGetMeQuery(undefined, { skip: !user });
  const plan = account?.profile.plan ?? "free";
  const sub = account?.subscription;

  return (
    <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
      <Card>
        <h2 className="text-lg font-semibold">Subscription</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-text-subtle">Plan</dt>
            <dd className="font-medium capitalize">{plan}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-text-subtle">Status</dt>
            <dd className="font-medium capitalize">{sub?.status ?? "active"}</dd>
          </div>
          {sub?.current_period_end ? (
            <div className="flex justify-between gap-4">
              <dt className="text-text-subtle">Renews</dt>
              <dd className="font-medium">
                {new Date(sub.current_period_end).toLocaleDateString()}
              </dd>
            </div>
          ) : null}
        </dl>

        <div className="mt-6 flex flex-wrap gap-3">
          {plan === "free" ? (
            <Link
              to="/pricing"
              className="inline-flex rounded-[10px] bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover"
            >
              Upgrade to Pro
            </Link>
          ) : (
            <ManageBillingButton hasSubscription={account?.profile.plan === "pro"} />
          )}
        </div>
      </Card>

      <Card>
        <h2 className="text-lg font-semibold">What&apos;s included</h2>
        <ul className="mt-4 space-y-2 text-sm text-text-muted">
          {plan === "pro" ? (
            <>
              <li>High & final render quality</li>
              <li>Reel cutting & static export</li>
              <li>Priority AI usage</li>
              <li>Multiple workspaces</li>
            </>
          ) : (
            <>
              <li>Desktop editor & AI chat</li>
              <li>Preview-quality renders</li>
              <li>Single workspace</li>
            </>
          )}
        </ul>
      </Card>
    </div>
  );
}