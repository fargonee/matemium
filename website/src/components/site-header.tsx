import { Link } from "react-router-dom";
import { useSelector } from "react-redux";

import { SignOutButton } from "@/components/sign-out-button";
import type { RootState } from "@/store";

export function SiteHeader() {
  const user = useSelector((state: RootState) => state.auth.user);

  return (
    <header className="sticky top-0 z-50 border-b border-transparent bg-bg/85 backdrop-blur-md supports-[backdrop-filter]:bg-bg/70">
      <nav className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4">
        <Link to="/" className="inline-flex items-center gap-2.5 font-semibold text-text">
          <img src="/assets/matemium-logo-180.png" alt="Matemium" width={32} height={32} />
          <span>Matemium</span>
        </Link>

        <div className="hidden items-center gap-6 md:flex">
          <Link to="/#features" className="text-sm font-medium text-text-muted hover:text-text">
            Features
          </Link>
          <Link to="/pricing" className="text-sm font-medium text-text-muted hover:text-text">
            Pricing
          </Link>
          {user ? (
            <>
              <Link to="/dashboard" className="text-sm font-medium text-text-muted hover:text-text">
                Dashboard
              </Link>
              <SignOutButton />
            </>
          ) : (
            <Link
              to="/login"
              className="rounded-full border border-border-strong px-4 py-2 text-sm font-medium text-text hover:border-accent hover:bg-accent/10"
            >
              Sign in
            </Link>
          )}
        </div>

        <div className="md:hidden">
          {user ? (
            <Link to="/dashboard" className="text-sm font-medium text-text">
              Dashboard
            </Link>
          ) : (
            <Link to="/login" className="text-sm font-medium text-text">
              Sign in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}