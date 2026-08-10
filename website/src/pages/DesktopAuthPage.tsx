import { useMemo, useState } from "react";
import { useSelector } from "react-redux";

import { GoogleSignInButton } from "@/components/google-sign-in-button";
import { Card } from "@/components/ui/card";
import type { RootState } from "@/store";

export function DesktopAuthPage() {
  const { user, accessToken, initialized } = useSelector((state: RootState) => state.auth);
  const [returning, setReturning] = useState(false);
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const port = params.get("port") ?? "";
  const state = params.get("state") ?? "";
  const validRequest = /^\d{2,5}$/.test(port) && /^[a-f0-9-]{32,40}$/i.test(state);
  const returnPath = `/desktop-auth?port=${encodeURIComponent(port)}&state=${encodeURIComponent(state)}`;

  if (!validRequest) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center px-4 py-16">
        <Card className="w-full max-w-md text-center">
          <h1 className="text-2xl font-bold">Invalid desktop sign-in request</h1>
          <p className="mt-3 text-sm text-text-muted">
            Return to Matemium and start sign-in again.
          </p>
        </Card>
      </section>
    );
  }

  if (!initialized) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center text-text-muted">
        Preparing secure sign-in…
      </section>
    );
  }

  if (!user || !accessToken) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center px-4 py-16">
        <Card className="w-full max-w-md">
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-accent">
            Matemium Desktop
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Sign in to continue</h1>
          <p className="mt-2 text-sm leading-6 text-text-muted">
            Use your Matemium account to unlock the studio on this computer.
          </p>
          <div className="mt-8">
            <GoogleSignInButton nextPath={returnPath} />
          </div>
        </Card>
      </section>
    );
  }

  return (
    <section className="flex min-h-[70vh] items-center justify-center px-4 py-16">
      <Card className="w-full max-w-md text-center">
        <p className="text-sm font-semibold uppercase tracking-wider text-success">
          Signed in to Matemium
        </p>
        <h1 className="mt-2 text-2xl font-bold">
          {returning ? "Confirming with the desktop…" : "Confirm desktop sign-in"}
        </h1>
        <p className="mt-3 text-sm text-text-muted">
          Signed in as <strong className="text-text">{user.email ?? "your Matemium account"}</strong>.
          Confirm that you want to use this account in the Matemium desktop app.
        </p>
        <form
          method="post"
          action={`http://127.0.0.1:${port}/matemium/auth/callback`}
          className="mt-7"
          onSubmit={() => setReturning(true)}
        >
          <input type="hidden" name="state" value={state} />
          <input type="hidden" name="access_token" value={accessToken} />
          <button type="submit" className="button-primary" disabled={returning}>
            {returning ? "Verifying desktop…" : "Confirm desktop sign-in"}
          </button>
        </form>
        <p className="mt-4 text-xs leading-5 text-text-muted">
          After confirmation, the next page will report whether the desktop accepted your account.
        </p>
      </Card>
    </section>
  );
}
