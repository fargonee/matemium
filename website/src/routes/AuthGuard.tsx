import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSelector } from "react-redux";

import type { RootState } from "@/store";

export function AuthGuard() {
  const location = useLocation();
  const { user, initialized } = useSelector((state: RootState) => state.auth);

  if (!initialized) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-text-muted">
        Loading…
      </div>
    );
  }

  if (!user) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <Outlet />;
}