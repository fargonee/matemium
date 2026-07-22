import { useSelector } from "react-redux";

import { useGetMeQuery } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/error-alert";
import { Spinner } from "@/components/ui/spinner";
import { SignOutButton } from "@/components/sign-out-button";
import type { RootState } from "@/store";

export function DashboardAccountPage() {
  const user = useSelector((state: RootState) => state.auth.user);
  const { data: account, isLoading, error, refetch } = useGetMeQuery(undefined, { skip: !user });

  const profile = account?.profile;
  const email = user?.email ?? profile?.email ?? "";

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted">
        <Spinner /> Loading account…
      </div>
    );
  }

  if (error) {
    return <ErrorAlert onRetry={() => void refetch()}>Could not load account details.</ErrorAlert>;
  }

  return (
    <div className="max-w-2xl space-y-6">
      <Card>
        <h2 className="text-lg font-semibold">Profile</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-text-subtle">Email</dt>
            <dd className="font-medium">{email}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-subtle">Access</dt>
            <dd className="capitalize">Free</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h2 className="text-lg font-semibold">AI Provider Keys</h2>
        <p className="text-sm text-text-muted mt-1">
          API keys are stored only on your computer in the Matemium desktop app.
          Matemium Cloud does not store, proxy, or resell model provider keys.
        </p>

        <div className="mt-4 rounded border border-border bg-bg-soft p-4 text-sm text-text-muted">
          Open the desktop app, go to Settings → AI &amp; LLM, and choose
          Connect OpenRouter Account. Your device completes the OAuth flow
          directly with OpenRouter and saves the returned key locally.
        </div>
      </Card>

      <div className="flex gap-3">
        <SignOutButton />
      </div>
    </div>
  );
}
