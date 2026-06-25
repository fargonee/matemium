import { Link, useSearchParams } from "react-router-dom";

import { GoogleSignInButton } from "@/components/google-sign-in-button";
import { Card } from "@/components/ui/card";

export function LoginPage() {
  const [params] = useSearchParams();
  const nextPath = params.get("next") ?? "/dashboard";

  return (
    <section className="flex min-h-[70vh] items-center justify-center px-4 py-16">
      <Card className="w-full max-w-md">
        <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-accent">
          Account
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Sign in to Matemium</h1>
        <p className="mt-2 text-sm text-text-muted">
          Use your Google account to access your dashboard, subscription, and licensed
          desktop downloads.
        </p>

        <div className="mt-8">
          <GoogleSignInButton nextPath={nextPath} />
        </div>

        <p className="mt-6 text-center text-xs text-text-subtle">
          By signing in you agree to our terms and privacy policy.{" "}
          <Link to="/pricing" className="text-accent">
            View plans
          </Link>
        </p>
      </Card>
    </section>
  );
}