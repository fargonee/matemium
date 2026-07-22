import { PricingCards } from "@/components/pricing-cards";

export function PricingPage() {
  return (
    <section className="px-4 py-16">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 max-w-2xl">
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-accent">
            Free
          </p>
          <h1 className="text-3xl font-bold tracking-tight">Matemium is free to use</h1>
          <p className="mt-3 text-text-muted">
            There are no Matemium subscriptions, paid tiers, or in-app AI credits.
            External AI uses your own provider account; OpenRouter is the default.
          </p>
        </div>
        <PricingCards />
      </div>
    </section>
  );
}
