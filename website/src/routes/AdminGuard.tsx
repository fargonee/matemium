import { Navigate, Outlet } from "react-router-dom";
import { useSelector } from "react-redux";

import { useGetMeQuery } from "@/api/matemiumApi";
import { isAdmin } from "@/lib/auth";
import type { RootState } from "@/store";

export function AdminGuard() {
  const user = useSelector((state: RootState) => state.auth.user);
  const { data: account, isLoading } = useGetMeQuery(undefined, { skip: !user });

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-text-muted">
        Loading…
      </div>
    );
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

  if (!isAdmin(user, profile)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}