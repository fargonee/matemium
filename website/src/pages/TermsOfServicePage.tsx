import { Link } from "react-router-dom";

export function TermsOfServicePage() {
  const lastUpdated = "June 26, 2026";

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-sm leading-relaxed text-text-muted">
      <div className="mb-10">
        <Link to="/" className="text-accent hover:underline">← Back to Matemium</Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-text">Terms of Service</h1>
        <p className="mt-1 text-text-subtle">Last updated: {lastUpdated}</p>
      </div>

      <div className="prose prose-invert max-w-none text-text-muted">
        <p>
          These Terms of Service ("Terms") govern your access to and use of the Matemium desktop application, website, cloud services, and any related software or content (collectively, the "Service") provided by Matemium ("we", "us", or "our").
        </p>
        <p>
          By accessing or using the Service, you agree to be bound by these Terms. If you do not agree, do not use the Service.
        </p>

        <h2>1. Description of the Service</h2>
        <p>
          Matemium is a proprietary layout-to-animation compiler and desktop application for creating animated math education content. The desktop application runs locally on your computer and performs all video rendering, compilation, and export on your device.
        </p>
        <p>
          Cloud components provide authentication, subscription management (via Lemon Squeezy), and AI-powered assistance for editing project code. We do not perform cloud-based video rendering or store your rendered media.
        </p>

        <h2>2. Accounts and Eligibility</h2>
        <ul>
          <li>You must be at least the age of majority in your jurisdiction to create an account.</li>
          <li>You are responsible for maintaining the confidentiality of your account and for all activity under it.</li>
          <li>We may suspend or terminate accounts that violate these Terms.</li>
        </ul>

        <h2>3. Software License and Plans</h2>
        <p>
          The Matemium desktop application is licensed, not sold. Your right to use the desktop software depends on your subscription plan:
        </p>
        <ul>
          <li><strong>Free plan</strong>: Limited to preview-quality renders, single workspace, and basic AI assistance.</li>
          <li><strong>Pro plan</strong>: Unlocks high-quality and final renders, reel cutting, full static exports (PNG/PDF), priority AI usage, and multiple workspaces.</li>
          <li><strong>Teams plan</strong>: Additional volume licensing and administrative features (contact sales).</li>
        </ul>
        <p>
          Your license is non-exclusive, non-transferable, and revocable. You may not rent, lease, sell, sublicense, reverse engineer, decompile, or create derivative works of the desktop application except as expressly permitted by law or these Terms.
        </p>

        <h2>4. Subscriptions and Billing (Lemon Squeezy)</h2>
        <p>
          Paid plans are billed through Lemon Squeezy, our Merchant of Record. Subscriptions automatically renew unless canceled before the end of the current billing period.
        </p>
        <ul>
          <li>You can manage or cancel your subscription at any time through the Lemon Squeezy customer portal (accessible from your Matemium dashboard).</li>
          <li>Upon cancellation, you retain access to paid features until the end of the paid billing period.</li>
          <li>See our separate <Link to="/refund" className="text-accent hover:underline">Refund and Cancellation Policy</Link> for details.</li>
        </ul>

        <h2>5. User Content and License Grant</h2>
        <p>
          You retain ownership of the projects, scenes, and content you create using Matemium ("Your Content").
        </p>
        <p>
          By using the AI features, you grant us a limited, non-exclusive license to process excerpts of Your Content solely to provide the AI assistance service and improve the Service (including training or fine-tuning where permitted by the LLM provider's terms and applicable law). We do not claim ownership of Your Content.
        </p>
        <p>
          You are solely responsible for the legality, accuracy, and appropriateness of Your Content, including any math lessons or videos you produce and distribute.
        </p>

        <h2>6. AI Features and Disclaimers</h2>
        <p>
          The AI chat and agent features are assistive tools only. They generate suggestions and code edits based on large language models. Outputs may be inaccurate, incomplete, or inappropriate.
        </p>
        <ul>
          <li>You are responsible for reviewing, testing, and verifying all AI-suggested code and animations before use.</li>
          <li>We make no warranty that AI outputs will be correct, suitable for any particular educational purpose, or free of errors.</li>
          <li>Do not rely on AI-generated content for high-stakes educational, medical, or legal purposes without independent verification.</li>
        </ul>

        <h2>7. Acceptable Use</h2>
        <p>You agree not to:</p>
        <ul>
          <li>Use the Service for any illegal purpose or in violation of any law.</li>
          <li>Abuse the AI features (e.g., automated scraping, generating harmful or misleading content at scale, attempting to extract model weights).</li>
          <li>Reverse engineer, decompile, or attempt to extract the source code of the desktop application or sidecar (except to the limited extent permitted by applicable law).</li>
          <li>Interfere with or disrupt the Service or servers.</li>
          <li>Impersonate others or misrepresent your affiliation.</li>
          <li>Share your Pro/Teams license with unauthorized users.</li>
        </ul>
        <p>See our <Link to="/acceptable-use" className="text-accent hover:underline">Acceptable Use Policy</Link> for more details.</p>

        <h2>8. Intellectual Property</h2>
        <p>
          All rights, title, and interest in and to the Matemium software, engine, website, and Service (excluding Your Content and open-source components such as Manim Community Edition) are owned by us or our licensors. Manim Community Edition is licensed under its own MIT license.
        </p>
        <p>
          You may not use our trademarks, logos, or trade names without prior written permission.
        </p>

        <h2>9. Disclaimers and Limitation of Liability</h2>
        <p>
          THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
        </p>
        <p>
          TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS, DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES, WHETHER BASED IN CONTRACT, TORT (INCLUDING NEGLIGENCE), STATUTE, OR OTHERWISE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
        </p>
        <p>
          Our total liability to you for any claims arising out of or relating to the Service shall not exceed the amount you paid us (if any) in the twelve (12) months preceding the claim.
        </p>
        <p>
          Some jurisdictions do not allow the exclusion of certain warranties or limitation of liability, so some of the above may not apply to you.
        </p>

        <h2>10. Indemnification</h2>
        <p>
          You agree to indemnify, defend, and hold harmless Matemium and its affiliates, officers, employees, and agents from and against any claims, liabilities, damages, losses, and expenses (including reasonable attorneys' fees) arising out of or in any way connected with your use of the Service, Your Content, or violation of these Terms.
        </p>

        <h2>11. Termination</h2>
        <p>
          We may suspend or terminate your access to the Service at any time, with or without notice, if you breach these Terms or for any other reason. Upon termination, your license to use the desktop software will end, and you must cease all use.
        </p>

        <h2>12. Governing Law and Dispute Resolution</h2>
        <p>
          These Terms are governed by the laws of [Your Jurisdiction — e.g., the State of Delaware, United States], without regard to its conflict of laws principles. Any disputes shall be resolved exclusively in the state or federal courts located in [appropriate venue].
        </p>
        <p className="text-xs italic">(Update jurisdiction and venue to match your entity formation before publishing.)</p>

        <h2>13. Changes to These Terms</h2>
        <p>
          We may modify these Terms at any time. Continued use of the Service after changes constitutes acceptance of the updated Terms. Material changes will be communicated via the website or email where possible.
        </p>

        <h2>14. Contact</h2>
        <p>
          Questions about these Terms? Contact us at <a href="mailto:contact@matemium.fargonee.space" className="text-accent">contact@matemium.fargonee.space</a>.
        </p>

        <p className="mt-10 text-xs text-text-subtle">
          Matemium is licensed software. All rights reserved.
        </p>
      </div>
    </div>
  );
}
