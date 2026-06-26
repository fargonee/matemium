import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { supabase } from "@/supabase/client";

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const handledRef = useRef(false);

  useEffect(() => {
    if (handledRef.current) return;
    handledRef.current = true;

    const code = params.get("code");
    const errorParam = params.get("error");
    const errorDescription =
      params.get("error_description") || params.get("error_code");
    const next = params.get("next") ?? "/dashboard";

    async function exchange() {
      if (errorParam) {
        setError(errorDescription || errorParam);
        return;
      }
      if (!code) {
        setError("Missing auth code");
        return;
      }

      const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
      if (exchangeError) {
        setError(exchangeError.message);
        return;
      }

      navigate(next, { replace: true });
    }

    void exchange();
  }, [navigate, params]);

  if (error) {
    return (
      <section className="flex min-h-[50vh] items-center justify-center px-4">
        <p className="text-red-300">Sign-in failed: {error}</p>
      </section>
    );
  }

  return (
    <section className="flex min-h-[50vh] items-center justify-center px-4 text-text-muted">
      Completing sign-in…
    </section>
  );
}