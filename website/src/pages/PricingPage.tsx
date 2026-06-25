import { PricingCards } from "@/components/pricing-cards";

export function PricingPage() {
  return (
    <section className="px-4 py-16">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 max-w-2xl">
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-accent">
            Pricing
          </p>
          <h1 className="text-3xl font-bold tracking-tight">Start free, upgrade when you need more</h1>
          <p className="mt-3 text-text-muted">
            Matemium is licensed software. Sign in to manage your subscription and download
            installers from your account dashboard.
          </p>
        </div>
        <PricingCards />
      </div>
    </section>
  );
}