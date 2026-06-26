import { Navigate, Outlet } from "react-router-dom";
import { useSelector } from "react-redux";

import { useGetMeQuery } from "@/api/matemiumApi";
import { isAdmin } from "@/lib/auth";
import type { RootState } from "@/store";

export function AdminGuard() {
  const { user, initialized } = useSelector((state: RootState) => state.auth);
  const { data: account, isLoading: meIsLoading } = useGetMeQuery(undefined, {
    skip: !user || !initialized,
  });

  if (!initialized) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-text-muted">
        Loading…
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const profile = account?.profile
    ? {
        id: account.profile.id,
        email: account.profile.email,
        full_name: account.profile.full_name ?? null,
        role: account.profile.role as "user" | "admin",
        plan: account.profile.plan,
      }
    : null;

  const knownAdmin = isAdmin(user, profile);

  // If we don't yet have confirmation from profile and the client email list
  // doesn't match, keep waiting for /me (server may upgrade role via MATEMIUM_ADMIN_EMAILS).
  if (meIsLoading && !knownAdmin) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-text-muted">
        Loading…
      </div>
    );
  }

  if (!knownAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}