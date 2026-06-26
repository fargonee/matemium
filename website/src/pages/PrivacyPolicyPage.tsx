import { Link } from "react-router-dom";

export function PrivacyPolicyPage() {
  const lastUpdated = "June 26, 2026";

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-sm leading-relaxed text-text-muted">
      <div className="mb-10">
        <Link to="/" className="text-accent hover:underline">← Back to Matemium</Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-text">Privacy Policy</h1>
        <p className="mt-1 text-text-subtle">Last updated: {lastUpdated}</p>
      </div>

      <div className="prose prose-invert max-w-none text-text-muted">
        <p>
          Matemium ("we", "us", or "our") operates the Matemium desktop application, website (matemium.app and related subdomains), and associated cloud services (the "Service"). This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use the Service.
        </p>

        <h2>1. Information We Collect</h2>
        <h3>Account and Authentication Information</h3>
        <ul>
          <li>Email address and basic profile information when you sign in with Google via Supabase Authentication.</li>
          <li>Authentication tokens (handled securely via Supabase; we do not store your Google credentials).</li>
        </ul>

        <h3>Subscription and Billing Information</h3>
        <ul>
          <li>Subscription status, plan type (Free, Pro, Teams), and associated Lemon Squeezy customer and subscription identifiers.</li>
          <li>Billing-related events are processed by Lemon Squeezy (our payment processor and Merchant of Record). We receive limited information such as subscription status and customer ID for entitlement enforcement.</li>
          <li>We do not store full credit card details.</li>
        </ul>

        <h3>Usage and AI Interaction Data</h3>
        <ul>
          <li>When you use the built-in AI chat or agent features, excerpts from your project files (primarily <code>scenes.py</code> and optionally <code>assets.py</code>), selection context, and your prompts are sent to our cloud server and then forwarded to third-party large language model (LLM) providers (e.g., OpenAI or compatible services).</li>
          <li>We do not store your full project files on our servers. Only temporary context needed for the current chat session is processed.</li>
          <li>Anonymous usage metrics related to plan entitlements, chat usage (for Pro priority), and feature access.</li>
        </ul>

        <h3>Technical and Device Information</h3>
        <ul>
          <li>Basic technical data required to operate the Service (e.g., IP address for abuse prevention, browser/app version for compatibility).</li>
          <li>The desktop application runs all rendering locally on your device using a bundled Python sidecar (Manim Community Edition + supporting tools). No video or media files are uploaded to our servers.</li>
        </ul>

        <h2>2. How We Use Your Information</h2>
        <ul>
          <li>To provide, maintain, and improve the Service, including authentication, subscription management, and AI assistance.</li>
          <li>To enforce plan limits (e.g., preview vs. high-quality renders, AI priority).</li>
          <li>To communicate with you about your account, billing, important Service updates, and (with consent where required) marketing.</li>
          <li>To detect and prevent fraud, abuse, or unauthorized use of the AI features.</li>
          <li>To comply with legal obligations.</li>
        </ul>

        <h2>3. Third-Party Service Providers</h2>
        <p>We share limited information with trusted service providers:</p>
        <ul>
          <li><strong>Supabase</strong> — Authentication, database for profiles and subscription metadata.</li>
          <li><strong>Lemon Squeezy</strong> — Payment processing, subscription management, and checkout. Lemon Squeezy is the Merchant of Record.</li>
          <li><strong>LLM Providers</strong> (e.g. OpenAI) — Processing of chat prompts and project excerpts for AI-powered code assistance. These providers have their own privacy policies. We send the minimum context necessary.</li>
          <li>Infrastructure providers for hosting the cloud API.</li>
        </ul>
        <p>We do not sell your personal information.</p>

        <h2>4. Local vs. Cloud Processing</h2>
        <p>
          <strong>Important:</strong> All video rendering, animation compilation, LaTeX processing, and media export occurs entirely on your local device inside the Matemium desktop application. We never receive or store your rendered videos, full project directories, or LaTeX assets.
        </p>
        <p>Only the following crosses the network:</p>
        <ul>
          <li>Authentication with Supabase.</li>
          <li>Billing webhooks and entitlement checks.</li>
          <li>AI chat context (project excerpts + your messages) sent to LLM providers via our proxy.</li>
        </ul>

        <h2>5. Data Retention</h2>
        <ul>
          <li>Account and subscription data is retained for as long as your account is active or as needed to provide the Service and comply with legal obligations.</li>
          <li>Chat context is processed transiently and is not stored long-term by Matemium beyond what is necessary for the immediate interaction.</li>
          <li>You may request deletion of your account and associated data by contacting us.</li>
        </ul>

        <h2>6. Your Rights</h2>
        <p>Depending on your location, you may have rights to:</p>
        <ul>
          <li>Access, correct, or delete your personal information.</li>
          <li>Object to or restrict certain processing.</li>
          <li>Data portability.</li>
          <li>Withdraw consent (where processing is based on consent).</li>
        </ul>
        <p>To exercise these rights, email <a href="mailto:hello@matemium.app" className="text-accent">hello@matemium.app</a>.</p>

        <h2>7. Children's Privacy</h2>
        <p>
          The Service is intended for educators, creators, and adults. We do not knowingly collect personal information from children under 13 (or the applicable age in your jurisdiction). If you believe we have collected such information, please contact us so we can delete it.
        </p>

        <h2>8. Security</h2>
        <p>
          We implement reasonable technical and organizational measures to protect your information. However, no method of transmission over the Internet is 100% secure. You are responsible for maintaining the security of your devices and accounts.
        </p>

        <h2>9. International Transfers</h2>
        <p>
          Your information may be processed in countries outside your own (including the United States). By using the Service, you consent to the transfer of information to countries that may have different data protection rules.
        </p>

        <h2>10. Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy from time to time. We will notify you of material changes by posting the new policy on this page and updating the "Last updated" date, or through other reasonable means.
        </p>

        <h2>11. Contact Us</h2>
        <p>
          If you have questions about this Privacy Policy or our data practices, contact us at:
          <br />
          <strong>hello@matemium.app</strong>
        </p>

        <p className="mt-10 text-xs text-text-subtle">
          This policy applies to the Matemium website, desktop application (in connection with cloud features), and related services.
        </p>
      </div>
    </div>
  );
}
