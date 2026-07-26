import { Link } from "react-router-dom";

export function TermsOfServicePage() {
  const lastUpdated = "July 26, 2026";

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-sm leading-relaxed text-text-muted">
      <div className="mb-10">
        <Link to="/" className="text-accent hover:underline">← Back to Matemium</Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-text">Terms of Service</h1>
        <p className="mt-1 text-text-subtle">Last updated: {lastUpdated}</p>
      </div>

      <div className="prose prose-invert max-w-none text-text-muted">
        <p>
          These Terms govern your access to Matemium, including the desktop
          application, website, cloud services, and related software.
        </p>

        <h2>1. Service</h2>
        <p>
          Matemium is a layout-to-animation compiler and desktop application for
          creating animated math education content. Rendering, compilation, and
          export run locally on your device.
        </p>
        <p>
          Cloud components may provide authentication, profile sync, provider-key
          settings, and AI assistance. Matemium does not provide cloud video
          rendering or store rendered media.
        </p>

        <h2>2. Free Use and Source Availability</h2>
        <p>
          Matemium is free to use under the Matemium Source-Available License.
          Its source code is publicly available for inspection, personal use,
          education, internal use, and contribution to the official project.
          Private modifications are permitted.
        </p>
        <p>
          Redistribution, publication of derivative builds, commercial use, and
          operation of competing forks require written permission.
        </p>

        <h2>3. AI Providers</h2>
        <p>
          Matemium does not sell model API access, pooled provider keys, or
          in-app AI credits. External AI features use your connected provider
          account, with OpenRouter as the default provider. Your provider usage
          is governed by that provider&apos;s terms and billing.
        </p>

        <h2>4. User Content</h2>
        <p>
          You retain ownership of projects, scenes, videos, and other content
          you create with Matemium. When you use AI features, excerpts of your
          project may be processed only to provide the requested assistance.
        </p>

        <h2>5. Acceptable Use</h2>
        <p>You agree not to use Matemium to violate law, abuse connected AI providers, disrupt the service, impersonate others, or misrepresent your affiliation with Matemium.</p>
        <p>See the <Link to="/acceptable-use" className="text-accent hover:underline">Acceptable Use Policy</Link> for more details.</p>

        <h2>6. Disclaimers</h2>
        <p>
          AI features are assistive only. You are responsible for reviewing,
          testing, and verifying generated code, animations, and educational
          content before use.
        </p>
        <p>
          The service is provided &quot;as is&quot; without warranties of any kind.
          To the maximum extent permitted by law, Matemium is not liable for
          indirect, incidental, special, consequential, or punitive damages.
        </p>
      </div>
    </div>
  );
}
