import { Link } from "react-router-dom";

export function EULAPage() {
  const lastUpdated = "June 26, 2026";

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 text-sm leading-relaxed text-text-muted">
      <div className="mb-10">
        <Link to="/" className="text-accent hover:underline">← Back to Matemium</Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-text">End User License Agreement (EULA)</h1>
        <p className="mt-1 text-text-subtle">Last updated: {lastUpdated}</p>
      </div>

      <div className="prose prose-invert max-w-none text-text-muted">
        <p>
          This End User License Agreement ("EULA") is a legal agreement between you and Matemium ("Licensor") for the Matemium desktop application, including all associated software, documentation, updates, and the bundled rendering engine (the "Software").
        </p>
        <p>
          By installing, copying, or otherwise using the Software, you agree to be bound by the terms of this EULA. If you do not agree, do not install or use the Software.
        </p>

        <h2>1. Grant of License</h2>
        <p>
          Subject to your compliance with these Terms and payment of any applicable fees, Licensor grants you a limited, non-exclusive, non-transferable, revocable license to:
        </p>
        <ul>
          <li>Install and use the Software on devices you own or control, solely for your personal or internal business/educational use.</li>
          <li>Use the features of the Software consistent with your active subscription plan (Free, Pro, or Teams) as described in the Terms of Service.</li>
        </ul>
        <p>
          The Software is licensed, not sold. This license does not grant you any rights to the source code.
        </p>

        <h2>2. Restrictions</h2>
        <p>You may not:</p>
        <ul>
          <li>Copy, modify, translate, reverse engineer, decompile, disassemble, or create derivative works based on the Software (except to the limited extent expressly permitted by applicable law).</li>
          <li>Rent, lease, lend, sell, sublicense, distribute, or transfer the Software or your license rights.</li>
          <li>Use the Software for timesharing, service bureau, or any other commercial hosting purpose without express written permission.</li>
          <li>Remove or alter any proprietary notices or labels on the Software.</li>
          <li>Use the Software in any manner that violates applicable law or the rights of others.</li>
          <li>Share a single Pro or Teams license across multiple unauthorized users or organizations.</li>
        </ul>

        <h2>3. Ownership</h2>
        <p>
          The Software and all intellectual property rights therein are owned by Licensor or its licensors. This EULA does not transfer any ownership rights. Manim Community Edition components are subject to their own open source licenses (primarily MIT).
        </p>

        <h2>4. Updates and Maintenance</h2>
        <p>
          Licensor may provide updates, upgrades, or patches. Such updates are subject to this EULA unless accompanied by separate terms. We have no obligation to provide updates or support except as may be required under your subscription plan.
        </p>

        <h2>5. Termination</h2>
        <p>
          This license is effective until terminated. It will terminate automatically if you fail to comply with any term of this EULA or your subscription expires or is canceled. Upon termination, you must destroy all copies of the Software in your possession.
        </p>

        <h2>6. Disclaimer of Warranty</h2>
        <p>
          THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT. LICENSOR DOES NOT WARRANT THAT THE SOFTWARE WILL BE UNINTERRUPTED, ERROR-FREE, OR MEET YOUR REQUIREMENTS.
        </p>
        <p>
          You assume all responsibility for the selection of the Software to achieve your intended results and for the installation, use, and results obtained from the Software. Educational and mathematical content produced with the Software is your sole responsibility to verify for accuracy.
        </p>

        <h2>7. Limitation of Liability</h2>
        <p>
          IN NO EVENT SHALL LICENSOR BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, PUNITIVE, OR EXEMPLARY DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS, DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES, ARISING OUT OF OR RELATED TO THE USE OR INABILITY TO USE THE SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
        </p>
        <p>
          OUR MAXIMUM LIABILITY SHALL NOT EXCEED THE FEES PAID BY YOU FOR THE SOFTWARE (IF ANY) IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM.
        </p>

        <h2>8. Third-Party Components</h2>
        <p>
          The Software includes or is bundled with third-party software and libraries (including Manim Community Edition and its dependencies, Tauri components, Python runtime elements, and TinyTeX). Such components are subject to their own license terms, which are made available with the Software or upon request. Your use of those components is governed by the respective third-party licenses.
        </p>

        <h2>9. Export Compliance</h2>
        <p>
          You may not export or re-export the Software in violation of any applicable export laws or regulations.
        </p>

        <h2>10. Entire Agreement</h2>
        <p>
          This EULA, together with the Terms of Service and any other agreements expressly referenced herein, constitutes the entire agreement between you and Licensor concerning the Software and supersedes all prior agreements.
        </p>

        <h2>11. Contact</h2>
        <p>
          For questions regarding this EULA, contact <a href="mailto:contact@matemium.fargonee.space" className="text-accent">contact@matemium.fargonee.space</a>.
        </p>

        <p className="mt-10 text-xs text-text-subtle">
          This EULA applies specifically to the Matemium desktop application and bundled sidecar. Use of the website and cloud services is also governed by the Terms of Service.
        </p>
      </div>
    </div>
  );
}
