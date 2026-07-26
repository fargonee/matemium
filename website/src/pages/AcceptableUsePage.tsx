import { Link } from "react-router-dom";

export function AcceptableUsePage() {
  const lastUpdated = "July 26, 2026";

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-sm leading-relaxed text-text-muted">
      <div className="mb-10">
        <Link to="/" className="text-accent hover:underline">← Back to Matemium</Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-text">Acceptable Use Policy</h1>
        <p className="mt-1 text-text-subtle">Last updated: {lastUpdated}</p>
      </div>

      <div className="prose prose-invert max-w-none text-text-muted">
        <p>
          This Acceptable Use Policy ("AUP") sets forth rules for the use of the Matemium Service, including the desktop application, website, cloud API, and AI features. It is incorporated into and forms part of our Terms of Service.
        </p>

        <h2>1. General Rules</h2>
        <p>You must use the Service only for lawful purposes and in accordance with these rules. You agree not to use the Service:</p>
        <ul>
          <li>In any way that violates any applicable federal, state, local, or international law or regulation.</li>
          <li>To exploit, harm, or attempt to exploit or harm minors in any way.</li>
          <li>To send, knowingly receive, upload, download, use, or re-use any material that is defamatory, obscene, indecent, abusive, harassing, threatening, or otherwise objectionable.</li>
          <li>To impersonate or attempt to impersonate Matemium, a Matemium employee, another user, or any other person or entity.</li>
          <li>To engage in any other conduct that restricts or inhibits anyone's use or enjoyment of the Service.</li>
        </ul>

        <h2>2. AI and Chat Features — Specific Prohibitions</h2>
        <p>The AI features (chat and agent) are powerful assistive tools for creating educational and explanatory visual content. You may not use them to:</p>
        <ul>
          <li>Generate or assist in the creation of content intended to deceive, defraud, or cause harm (including deepfakes, misinformation campaigns, or misleading educational material presented as authoritative without disclosure).</li>
          <li>Produce material that promotes violence, discrimination, illegal activities, or child sexual exploitation.</li>
          <li>Attempt to jailbreak, extract training data, reverse engineer the underlying models, or otherwise abuse connected LLM providers.</li>
          <li>Generate large volumes of low-quality or spam content at scale in a manner that imposes unreasonable load on our systems or the LLM providers.</li>
          <li>Create automated bots that interact with the AI without meaningful human oversight, except as expressly authorized.</li>
        </ul>
        <p>
          You remain fully responsible for all content you create, publish, or distribute using AI assistance.
        </p>

        <h2>3. Abuse of the Service</h2>
        <p>You may not:</p>
        <ul>
          <li>Access or attempt to access any part of the Service through automated means (scraping, bots, etc.) except through officially supported APIs with proper authentication.</li>
          <li>Interfere with or disrupt the integrity or performance of the Service or the data contained therein.</li>
          <li>Attempt to gain unauthorized access to any portion of the Service, other accounts, or computer systems.</li>
          <li>Use the Service in a manner that could damage, disable, overburden, or impair the Service or interfere with any other party's use.</li>
          <li>Share credentials or use another person&apos;s connected provider account without authorization.</li>
        </ul>

        <h2>4. User Content Responsibilities</h2>
        <p>
          You are solely responsible for any content, code, lessons, videos, or other materials you create or upload in connection with the Service. This includes ensuring that your content does not infringe the intellectual property or other rights of third parties.
        </p>

        <h2>5. Enforcement and Consequences</h2>
        <p>
          We reserve the right to investigate violations of this AUP and to take appropriate action, including but not limited to:
        </p>
        <ul>
          <li>Removing or disabling access to content that violates this policy.</li>
          <li>Suspending or terminating your account access.</li>
          <li>Reporting illegal activity to law enforcement authorities.</li>
          <li>Cooperating with any investigation by LLM providers or infrastructure providers.</li>
        </ul>
        <p>
          We may also implement technical measures (such as rate limiting) to prevent abuse.
        </p>

        <h2>6. Reporting Violations</h2>
        <p>
          If you become aware of any violation of this Acceptable Use Policy, please report it to <a href="mailto:contact@matemium.fargonee.space" className="text-accent">contact@matemium.fargonee.space</a>.
        </p>

        <h2>7. Changes</h2>
        <p>
          We may update this Acceptable Use Policy from time to time. Continued use of the Service constitutes acceptance of the current version.
        </p>

        <p className="mt-10 text-xs text-text-subtle">
          This policy helps us maintain a safe, high-quality experience for all users and protects the long-term viability of the AI features.
        </p>
      </div>
    </div>
  );
}
