import { Link } from "react-router-dom";

export function RefundPolicyPage() {
  const lastUpdated = "July 21, 2026";

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
          Matemium AI credits, or model API access.
        </p>

        <h2>1. Matemium Charges</h2>
        <p>
          Because Matemium does not currently charge users, there are no
          Matemium subscription fees to cancel and no Matemium payments to
          refund.
        </p>

        <h2>2. External Provider Costs</h2>
        <p>
          If you connect OpenRouter or another AI provider, any model usage is
          billed directly by that provider under its own terms. Matemium cannot
          refund charges from external providers.
        </p>

        <h2>3. Contact</h2>
        <p>
          For account or access questions, email{" "}
          <a href="mailto:contact@matemium.fargonee.space" className="text-accent">
            contact@matemium.fargonee.space
          </a>.
        </p>
      </div>
    </div>
  );
}
