import { useState } from "react";

import { Button } from "@/components/ui/button";
import { env } from "@/lib/env";
import { supabase } from "@/supabase/client";

interface GoogleSignInButtonProps {
  nextPath?: string;
}

export function GoogleSignInButton({ nextPath = "/dashboard" }: GoogleSignInButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSignIn() {
    setLoading(true);
    setError(null);

    const siteUrl = env.siteUrl || window.location.origin;
    const { error: signInError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${siteUrl}/auth/callback?next=${encodeURIComponent(nextPath)}`,
      },
    });

    if (signInError) {
      setError(signInError.message);
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <Button
        type="button"
        variant="secondary"
        size="lg"
        fullWidth
        onClick={handleSignIn}
        disabled={loading}
      >
        {loading ? "Redirecting…" : "Continue with Google"}
      </Button>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
    </div>
  );
}