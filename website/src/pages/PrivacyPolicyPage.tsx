import { Link } from "react-router-dom";

export function PrivacyPolicyPage() {
  const lastUpdated = "July 21, 2026";

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-sm leading-relaxed text-text-muted">
      <div className="mb-10">
        <Link to="/" className="text-accent hover:underline">← Back to Matemium</Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-text">Privacy Policy</h1>
        <p className="mt-1 text-text-subtle">Last updated: {lastUpdated}</p>
      </div>

      <div className="prose prose-invert max-w-none text-text-muted">
        <p>
          This Privacy Policy explains how Matemium handles information when you
          use the desktop application, website, and cloud services.
        </p>

        <h2>1. Information We Collect</h2>
        <ul>
          <li>Email address and basic profile information when you sign in with Google via Supabase Authentication.</li>
          <li>Provider settings such as selected AI provider, selected model, and whether a key has been configured.</li>
          <li>AI interaction context, including prompts and project excerpts, when you explicitly use AI chat or agent features.</li>
          <li>Basic technical data required for security, abuse prevention, and compatibility.</li>
        </ul>

        <h2>2. What Stays Local</h2>
        <p>
          Rendering, Manim compilation, LaTeX processing, and media export run
          locally on your device. Matemium does not upload rendered videos or
          full project directories for cloud rendering.
        </p>

        <h2>3. AI Providers</h2>
        <p>
          External AI uses your connected provider account. OpenRouter is the
          default provider. Provider prompts and usage are subject to the
          provider&apos;s own privacy policy and terms.
        </p>
        <p>
          Provider API keys are treated as secrets. They are never returned to
          the client after saving and must be redacted from logs and telemetry.
        </p>

        <h2>4. Third-Party Services</h2>
        <ul>
          <li><strong>Supabase</strong> — authentication and profile storage.</li>
          <li><strong>OpenRouter or user-selected LLM providers</strong> — AI prompt processing when you use AI features.</li>
          <li>Infrastructure providers used to host the website and optional cloud API.</li>
        </ul>
        <p>We do not sell your personal information.</p>

        <h2>5. Data Retention</h2>
        <ul>
          <li>Account data is retained while your account is active or as needed for legal and security obligations.</li>
          <li>AI context is processed for the requested interaction and should not be stored long-term unless needed for debugging or abuse prevention.</li>
          <li>You may request deletion of your account and associated data by contacting us.</li>
        </ul>

        <h2>6. Contact</h2>
        <p>
          To ask privacy questions or request account deletion, email{" "}
          <a href="mailto:contact@matemium.fargonee.space" className="text-accent">
            contact@matemium.fargonee.space
          </a>.
        </p>
      </div>
    </div>
  );
}
