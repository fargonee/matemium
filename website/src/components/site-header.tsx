import { useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useSelector } from "react-redux";

import type { RootState } from "@/store";

const NAV_ITEMS = [
  ["/showcase", "Showcase"],
  ["/roadmap", "Roadmap"],
  ["/source", "Source"],
  ["/support", "Support"],
];

export function SiteHeader() {
  const user = useSelector((state: RootState) => state.auth.user);
  const [open, setOpen] = useState(false);
  const location = useLocation();

  const close = () => setOpen(false);

  return (
    <header className="site-header">
      <nav className="mx-auto flex h-[72px] w-full max-w-7xl items-center justify-between gap-4 px-5">
        <Link to="/" onClick={close} className="brand-link">
          <img src="/assets/matemium-logo-180.png" alt="" width={34} height={34} />
          <span>Matemium</span>
          <small>Studio</small>
        </Link>

        <div className="hidden items-center gap-7 lg:flex">
          {NAV_ITEMS.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              {label}
            </NavLink>
          ))}
        </div>

        <div className="hidden items-center gap-3 lg:flex">
          {user ? (
            <Link to="/dashboard" className="button-secondary !px-4 !py-2">Dashboard</Link>
          ) : (
            <Link to="/login" className="nav-link">Sign in</Link>
          )}
          <Link to="/download" className="button-primary !px-4 !py-2">
            Get Matemium <span aria-hidden>→</span>
          </Link>
        </div>

        <button
          type="button"
          className="menu-button lg:hidden"
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          <span className={open ? "rotate-45 translate-y-[5px]" : ""} />
          <span className={open ? "opacity-0" : ""} />
          <span className={open ? "-rotate-45 -translate-y-[5px]" : ""} />
        </button>
      </nav>
      {open ? (
        <div className="mobile-menu lg:hidden">
          {NAV_ITEMS.map(([to, label]) => (
            <NavLink key={to} to={to} onClick={close} className={location.pathname === to ? "active" : ""}>
              {label}
            </NavLink>
          ))}
          <Link to={user ? "/dashboard" : "/login"} onClick={close}>{user ? "Dashboard" : "Sign in"}</Link>
          <Link to="/download" onClick={close} className="button-primary mt-3">Get Matemium <span>→</span></Link>
        </div>
      ) : null}
    </header>
  );
}
