import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSelector } from "react-redux";

import { useCreateCheckoutMutation } from "@/api/matemiumApi";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CREDIT_PACKS, PLANS } from "@/lib/plans";
import type { RootState } from "@/store";

export function PricingCards() {
  const navigate = useNavigate();
  const signedIn = Boolean(useSelector((state: RootState) => state.auth.user));
  const [createCheckout] = useCreateCheckoutMutation();
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function startCheckout(planId: string) {
    if (!signedIn) {
      navigate(`/login?next=${encodeURIComponent("/pricing")}`);
      return;
    }

    setLoadingPlan(planId);
    setError(null);

    try {
      const result = await createCheckout({ checkoutRequest: { plan_id: planId } }).unwrap();
      if (result.url) {
        window.location.href = result.url;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
      setLoadingPlan(null);
    }
  }

  return (
    <div className="space-y-8">
      {/* Subscription Plans */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Subscriptions</h2>
        <div className="grid gap-5 md:grid-cols-3">
          {PLANS.map((plan) => (
            <Card key={plan.id} highlighted={plan.highlighted} className="flex flex-col">
              {plan.highlighted ? (
                <span className="mb-3 inline-flex w-fit rounded-full bg-accent/15 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-accent">
                  Popular
                </span>
              ) : null}
              <h3 className="text-lg font-semibold">{plan.name}</h3>
              <p className="mt-1 text-2xl font-bold tracking-tight">{plan.priceLabel}</p>
              <p className="mt-2 text-sm text-text-muted">{plan.description}</p>
              <ul className="my-5 flex-1 space-y-2 text-sm text-text-muted">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-2">
                    <span className="text-success">✓</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              {plan.contactSales ? (
                <a href="mailto:contact@matemium.fargonee.space?subject=Matemium%20Teams">
                  <Button variant="secondary" fullWidth>
                    Contact sales
                  </Button>
                </a>
              ) : plan.id === "free" ? (
                signedIn ? (
                  <Link to="/dashboard">
                    <Button variant="secondary" fullWidth>
                      Current plan
                    </Button>
                  </Link>
                ) : (
                  <Link to="/login">
                    <Button variant="secondary" fullWidth>
                      Get started
                    </Button>
                  </Link>
                )
              ) : (
                <Button
                  fullWidth
                  onClick={() => startCheckout(plan.id)}
                  disabled={loadingPlan === plan.id}
                >
                  {loadingPlan === plan.id ? "Redirecting…" : "Upgrade to Pro"}
                </Button>
              )}
            </Card>
          ))}
        </div>
      </div>

      {/* Credit / Token Packs for LLM usage */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Platform LLM Credits (one-time)</h2>
        <p className="text-sm text-text-muted mb-4">
          Buy credits to use our hosted models (code generation + audio). Credits are priced automatically using our real provider costs + your chosen margin.
        </p>
        <div className="grid gap-5 md:grid-cols-2">
          {CREDIT_PACKS.map((pack) => (
            <Card key={pack.id} highlighted={pack.highlighted} className="flex flex-col">
              <h3 className="text-lg font-semibold">{pack.name}</h3>
              <p className="mt-1 text-2xl font-bold tracking-tight">{pack.priceLabel}</p>
              <p className="mt-2 text-sm text-text-muted">{pack.description}</p>
              <ul className="my-5 flex-1 space-y-2 text-sm text-text-muted">
                {pack.features.map((feature) => (
                  <li key={feature} className="flex gap-2">
                    <span className="text-success">✓</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <Button
                fullWidth
                onClick={() => startCheckout(pack.id)}
                disabled={loadingPlan === pack.id}
              >
                {loadingPlan === pack.id ? "Redirecting…" : "Buy Credits"}
              </Button>
            </Card>
          ))}
        </div>
      </div>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}
    </div>
  );
}