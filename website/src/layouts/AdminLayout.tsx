import { Outlet } from "react-router-dom";

import { AdminNav } from "@/components/admin-nav";

export function AdminLayout() {
  return (
    <section className="px-4 py-10">
      <div className="mx-auto max-w-6xl">
        <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-accent">
          Admin
        </p>
        <h1 className="text-2xl font-bold tracking-tight">Matemium control panel</h1>
        <div className="mt-6">
          <AdminNav />
        </div>
        <div className="mt-8">
          <Outlet />
        </div>
      </div>
    </section>
  );
}