import { Link } from "react-router-dom";
import { useSelector } from "react-redux";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PLANS } from "@/lib/plans";
import type { RootState } from "@/store";

export function PricingCards() {
  const signedIn = Boolean(useSelector((state: RootState) => state.auth.user));

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold mb-4">Free Access</h2>
        <div className="grid gap-5 md:grid-cols-2">
          {PLANS.map((plan) => (
            <Card key={plan.id} highlighted={plan.highlighted} className="flex flex-col">
              {plan.highlighted ? (
                <span className="mb-3 inline-flex w-fit rounded-full bg-accent/15 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-accent">
                  Free
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

              {signedIn ? (
                <Link to="/dashboard">
                  <Button variant="secondary" fullWidth>
                    Open dashboard
                  </Button>
                </Link>
              ) : (
                <Link to="/login">
                  <Button variant="secondary" fullWidth>
                    Get started
                  </Button>
                </Link>
              )}
            </Card>
          ))}
          <Card className="flex flex-col">
            <h3 className="text-lg font-semibold">AI Providers</h3>
            <p className="mt-1 text-2xl font-bold tracking-tight">BYO</p>
            <p className="mt-2 text-sm text-text-muted">
              Connect OpenRouter or another supported provider. Matemium does not sell model credits or shared keys.
            </p>
            <ul className="my-5 flex-1 space-y-2 text-sm text-text-muted">
              <li className="flex gap-2"><span className="text-success">✓</span><span>OpenRouter-first setup</span></li>
              <li className="flex gap-2"><span className="text-success">✓</span><span>Multiple user-owned keys</span></li>
              <li className="flex gap-2"><span className="text-success">✓</span><span>Optional local models</span></li>
            </ul>
            <Link to={signedIn ? "/dashboard/account" : "/login"}>
              <Button fullWidth>
                Manage keys
              </Button>
            </Link>
          </Card>
        </div>
      </div>
    </div>
  );
}
