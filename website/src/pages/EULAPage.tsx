import { Link } from "react-router-dom";

export function EULAPage() {
  const lastUpdated = "July 21, 2026";

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-sm leading-relaxed text-text-muted">
      <div className="mb-10">
        <Link to="/" className="text-accent hover:underline">← Back to Matemium</Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-text">Software License</h1>
        <p className="mt-1 text-text-subtle">Last updated: {lastUpdated}</p>
      </div>

      <div className="prose prose-invert max-w-none text-text-muted">
        <p>
          Matemium is free to use and source-available. This license summary
          applies to the desktop application, bundled sidecar, website, and
          related Matemium software, except for third-party components that
          retain their own licenses.
        </p>

        <h2>1. Permitted Uses</h2>
        <ul>
          <li>Inspect the source code.</li>
          <li>Use Matemium for personal, educational, and internal projects.</li>
          <li>Contribute changes to the official Matemium project.</li>
          <li>Make private modifications for your own use.</li>
        </ul>

        <h2>2. Permission Required</h2>
        <p>
          Redistribution, publication of derivative builds, commercial use, and
          operation of competing forks require written permission from Matemium.
        </p>

        <h2>3. Third-Party Components</h2>
        <p>
          Matemium includes third-party software and libraries, including Manim
          Community Edition, Tauri components, Python runtime elements, and
          TinyTeX. Those components are governed by their own license terms.
        </p>

        <h2>4. Disclaimer</h2>
        <p>
          The software is provided &quot;as is&quot; without warranties of any kind.
          You are responsible for verifying educational and mathematical content
          produced with Matemium.
        </p>
      </div>
    </div>
  );
}
