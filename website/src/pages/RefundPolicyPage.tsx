import { Link } from "react-router-dom";

export function RefundPolicyPage() {
  const lastUpdated = "June 26, 2026";

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-sm leading-relaxed text-text-muted">
      <div className="mb-10">
        <Link to="/" className="text-accent hover:underline">← Back to Matemium</Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-text">Refund and Cancellation Policy</h1>
        <p className="mt-1 text-text-subtle">Last updated: {lastUpdated}</p>
      </div>

      <div className="prose prose-invert max-w-none text-text-muted">
        <p>
          This Refund and Cancellation Policy applies to all paid subscription plans (Pro and Teams) for the Matemium Service, processed through our Merchant of Record, Lemon Squeezy.
        </p>

        <h2>1. Subscription Model</h2>
        <p>
          Matemium offers subscription-based access to enhanced features of the desktop application and cloud services. Subscriptions are billed on a recurring basis (monthly or as otherwise selected at checkout) and automatically renew at the end of each billing period unless canceled.
        </p>

        <h2>2. Cancellation</h2>
        <ul>
          <li>You may cancel your subscription at any time through the <strong>Manage billing</strong> button in your Matemium dashboard or directly via the Lemon Squeezy customer portal.</li>
          <li>Cancellation takes effect at the end of the current paid billing period. You will continue to have access to paid features (high-quality renders, reel cutting, priority AI, multiple workspaces, etc.) until that date.</li>
          <li>There is no penalty for canceling, and you will not be charged again after cancellation.</li>
          <li>Upon cancellation or expiration, your account reverts to the Free plan limits.</li>
        </ul>

        <h2>3. Refunds</h2>
        <p>
          <strong>General Rule:</strong> Because Matemium is digital software and provides immediate access upon successful payment and account upgrade, we generally do not offer refunds.
        </p>
        <p>
          Refunds are provided only in the following limited circumstances, at our sole discretion:
        </p>
        <ul>
          <li>Technical issues on our side that completely prevent you from using paid features for a significant period after purchase (and we are unable to resolve the issue).</li>
          <li>Duplicate or erroneous charges caused by a system error.</li>
          <li>Other cases required by applicable consumer protection laws in your jurisdiction.</li>
        </ul>

        <p>
          <strong>We do not provide refunds for:</strong>
        </p>
        <ul>
          <li>Change of mind after access has been granted or after you have used Pro features (including high-quality renders, reel cutting, or AI assistance).</li>
          <li>Failure to cancel before the next billing cycle.</li>
          <li>Dissatisfaction with AI-generated suggestions (AI is an assistive tool only).</li>
          <li>Issues arising from your local hardware, operating system, LaTeX installation, or internet connectivity.</li>
        </ul>

        <h2>4. How to Request a Refund</h2>
        <p>
          To request a refund, contact us within 14 days of the charge at <a href="mailto:hello@matemium.app" className="text-accent">hello@matemium.app</a> with your Lemon Squeezy order number and a description of the issue. We will review the request and respond within a reasonable time.
        </p>

        <h2>5. Chargebacks and Disputes</h2>
        <p>
          Initiating a chargeback or dispute with your payment provider for a legitimate charge may result in immediate suspension or termination of your account. We encourage you to contact us first to resolve any billing concerns.
        </p>

        <h2>6. Proration and Plan Changes</h2>
        <p>
          If you upgrade or downgrade your plan, any price difference will be handled according to Lemon Squeezy's policies (typically prorated on the next billing cycle). Contact support for details on specific changes.
        </p>

        <h2>7. Free Plan and Trials</h2>
        <p>
          The Free plan is provided at no cost. Any promotional trials or introductory offers will clearly state their terms at the time of signup. Unused portions of trials generally do not convert to cash refunds.
        </p>

        <h2>8. Contact</h2>
        <p>
          For questions about billing, cancellation, or refunds, email <strong>hello@matemium.app</strong> or use the support channels available in your dashboard.
        </p>

        <p className="mt-8 text-xs text-text-subtle">
          This policy is in addition to Lemon Squeezy's buyer protections and our general Terms of Service.
        </p>
      </div>
    </div>
  );
}
