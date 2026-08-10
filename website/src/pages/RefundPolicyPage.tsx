import { Link } from "react-router-dom";

export function RefundPolicyPage() {
  const lastUpdated = "July 26, 2026";

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-sm leading-relaxed text-text-muted">
      <div className="mb-10">
        <Link to="/" className="text-accent hover:underline">← Back to Matemium</Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-text">Refund Policy</h1>
        <p className="mt-1 text-text-subtle">Last updated: {lastUpdated}</p>
      </div>

      <div className="prose prose-invert max-w-none text-text-muted">
        <p>
          Matemium is free to use. We do not sell subscriptions, paid plans,
          Matemium AI credits, or model API access. Visitors may voluntarily
          contribute to support development.
        </p>

        <h2>1. Voluntary Contributions</h2>
        <p>
          Contributions do not purchase software access, a paid tier, model
          usage, or a guaranteed feature. If you contributed by mistake, were
          charged more than once, or believe a payment was unauthorized,
          contact us promptly. Requests are reviewed case by case in accordance
          with applicable law and the payment processor&apos;s terms.
        </p>

        <h2>2. No Subscription to Cancel</h2>
        <p>
          Matemium has no recurring product subscription or Matemium-owned AI
          plan to cancel. Any recurring option explicitly offered by the
          contribution processor must be managed through that processor.
        </p>

        <h2>3. External Provider Costs</h2>
        <p>
          If you connect OpenRouter or another AI provider, any model usage is
          billed directly by that provider under its own terms. Matemium cannot
          refund charges from external providers.
        </p>

        <h2>4. Contact</h2>
        <p>
          For account or access questions, email{" "}
          <a href="mailto:matemiumm@gmail.com" className="text-accent">
            matemiumm@gmail.com
          </a>.
        </p>
      </div>
    </div>
  );
}
