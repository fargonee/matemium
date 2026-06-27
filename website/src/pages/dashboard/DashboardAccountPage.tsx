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
    <div className="max-w-xl space-y-5">
      <Card>
        <h2 className="text-lg font-semibold">Profile</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-text-subtle">Email</dt>
            <dd className="font-medium">{email}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-subtle">Full name</dt>
            <dd className="font-medium">{profile?.full_name ?? "—"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-subtle">Role</dt>
            <dd className="capitalize">{profile?.role ?? "user"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-subtle">Plan</dt>
            <dd className="capitalize">{profile?.plan ?? "free"}</dd>
          </div>
        </dl>
        <p className="mt-4 text-xs text-text-subtle">
          Profile details are managed via your Google account and our system. Contact support to update email.
        </p>
      </Card>

      <div>
        <SignOutButton />
      </div>
    </div>
  );
}
