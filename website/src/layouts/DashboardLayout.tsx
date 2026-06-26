import { Link, Outlet } from "react-router-dom";
import { useSelector } from "react-redux";

import { useGetMeQuery } from "@/api/matemiumApi";
import { DashboardNav } from "@/components/dashboard-nav";
import { displayName, isAdmin } from "@/lib/auth";
import type { RootState } from "@/store";

export function DashboardLayout() {
  const user = useSelector((state: RootState) => state.auth.user);
  const { data: account } = useGetMeQuery(undefined, { skip: !user });

  const profile = account?.profile
    ? {
        id: account.profile.id,
        email: account.profile.email,
        full_name: account.profile.full_name ?? null,
        role: account.profile.role as "user" | "admin",
        plan: account.profile.plan,
      }
    : null;

  const name = user ? displayName(user, profile) : "User";
  // Show immediately for client-listed admins; also show once server confirms via profile.role
  const showAdmin = isAdmin(user, profile) || isAdmin(user, null);

  return (
    <section className="px-4 py-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-text-subtle">Signed in as</p>
            <h1 className="text-2xl font-bold tracking-tight">{name}</h1>
          </div>
          {showAdmin ? (
            <Link
              to="/admin"
              className="rounded-full border border-border-strong px-4 py-2 text-sm font-medium text-text hover:border-accent"
            >
              Admin panel
            </Link>
          ) : null}
        </div>
        <DashboardNav />
        <div className="mt-8">
          <Outlet />
        </div>
      </div>
    </section>
  );
}