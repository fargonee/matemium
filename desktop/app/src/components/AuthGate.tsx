import { useRef, useState } from "react";

import * as api from "../api/tauri";
import { formatError } from "../utils/errors";

interface AuthGateProps {
  checking?: boolean;
  onAuthenticated?: (profile: Record<string, unknown>) => void;
}

export function AuthGate({ checking = false, onAuthenticated }: AuthGateProps) {
  const [busy, setBusy] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const attemptRef = useRef(0);

  const signIn = async () => {
    const attempt = ++attemptRef.current;
    setBusy(true);
    setError(null);
    try {
      const profile = await api.authBrowserLogin();
      if (attempt === attemptRef.current) {
        onAuthenticated?.(profile);
      }
    } catch (signInError) {
      if (attempt === attemptRef.current) {
        setError(formatError(signInError));
      }
    } finally {
      if (attempt === attemptRef.current) {
        setBusy(false);
        setCancelling(false);
      }
    }
  };

  const cancelSignIn = async () => {
    attemptRef.current += 1;
    setCancelling(true);
    setError(null);
    try {
      await api.authBrowserLoginCancel();
    } catch (cancelError) {
      setError(formatError(cancelError));
    } finally {
      setBusy(false);
      setCancelling(false);
    }
  };

  return (
    <main className="auth-gate-modern">
      <div className="auth-gate-glow-modern" aria-hidden />
      <section className="auth-gate-card-modern" aria-labelledby="auth-gate-title">
        <div className="auth-gate-brand-modern">
          <span className="auth-gate-mark-modern" aria-hidden>∑</span>
          <span>Matemium</span>
        </div>

        <div className="auth-gate-emblem-modern" aria-hidden>
          <span>✦</span>
        </div>
        <p className="auth-gate-kicker-modern">Your visual reasoning studio</p>
        <h1 id="auth-gate-title">
          {checking ? "Checking your session" : "Sign in to continue"}
        </h1>
        <p className="auth-gate-copy-modern">
          {checking
            ? "Securely reconnecting this computer to your Matemium account."
            : "One account keeps Matemium available to you across releases while your projects and renders remain on this computer."}
        </p>

        {checking ? (
          <div className="auth-gate-checking-modern" role="status">
            <span className="auth-gate-spinner-modern" /> Verifying account…
          </div>
        ) : (
          <>
            <button
              type="button"
              className="auth-gate-button-modern"
              disabled={busy}
              onClick={() => void signIn()}
            >
              <span className="auth-google-mark-modern" aria-hidden>G</span>
              {busy ? "Waiting for your browser…" : "Continue with Google"}
              {!busy && <span aria-hidden>→</span>}
            </button>
            {busy ? (
              <div className="auth-gate-waiting-modern" role="status">
                <span>Finish Google sign-in in the browser window. This screen will unlock only after your Matemium account is verified.</span>
                <button
                  type="button"
                  className="auth-gate-cancel-modern"
                  disabled={cancelling}
                  onClick={() => void cancelSignIn()}
                >
                  {cancelling ? "Cancelling…" : "Cancel sign-in"}
                </button>
              </div>
            ) : (
              <p className="auth-gate-browser-note-modern">
                Matemium opens a secure browser window and returns here automatically.
              </p>
            )}
          </>
        )}

        {error && (
          <div className="auth-gate-error-modern" role="alert">
            <strong>Sign-in wasn’t completed.</strong>
            <span>{error}</span>
          </div>
        )}

        <div className="auth-gate-trust-modern">
          <span><i aria-hidden>✓</i> Local project files</span>
          <span><i aria-hidden>✓</i> Local rendering</span>
          <span><i aria-hidden>✓</i> Creator-owned output</span>
        </div>
      </section>
    </main>
  );
}
