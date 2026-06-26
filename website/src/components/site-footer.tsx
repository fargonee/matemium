import { Link } from "react-router-dom";

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-bg py-12">
      <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 md:grid-cols-4">
        <div className="md:col-span-1">
          <div className="mb-3 inline-flex items-center gap-2 font-semibold">
            <img src="/assets/matemium-logo-180.png" alt="Matemium" width={28} height={28} />
            <span>Matemium</span>
          </div>
          <p className="max-w-xs text-sm text-text-subtle">
            A document compiler for animated math — proprietary desktop software for
            educators and creators.
          </p>
        </div>

        <div className="flex flex-col gap-2 text-sm">
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-subtle">
            Product
          </h4>
          <Link to="/#features" className="text-text-muted hover:text-text">
            Features
          </Link>
          <Link to="/pricing" className="text-text-muted hover:text-text">
            Pricing
          </Link>
          <Link to="/dashboard/downloads" className="text-text-muted hover:text-text">
            Downloads
          </Link>
        </div>

        <div className="flex flex-col gap-2 text-sm">
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-subtle">
            Account
          </h4>
          <Link to="/login" className="text-text-muted hover:text-text">
            Sign in
          </Link>
          <Link to="/dashboard" className="text-text-muted hover:text-text">
            Dashboard
          </Link>
          <a href="mailto:contact@matemium.fargonee.space" className="text-text-muted hover:text-text">
            Contact
          </a>
        </div>

        <div className="flex flex-col gap-2 text-sm">
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-subtle">
            Legal
          </h4>
          <Link to="/terms" className="text-text-muted hover:text-text">Terms of Service</Link>
          <Link to="/privacy" className="text-text-muted hover:text-text">Privacy Policy</Link>
          <Link to="/refund" className="text-text-muted hover:text-text">Refund &amp; Cancellation</Link>
          <Link to="/license" className="text-text-muted hover:text-text">Desktop License (EULA)</Link>
          <Link to="/acceptable-use" className="text-text-muted hover:text-text">Acceptable Use</Link>
          <span className="mt-1 text-text-subtle">© 2026 Matemium. All rights reserved.</span>
        </div>
      </div>
    </footer>
  );
}