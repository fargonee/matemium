import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export function RootLayout() {
  const { pathname } = useLocation();

  useEffect(() => {
    const titles: Record<string, string> = {
      "/": "Matemium — Give mathematical ideas motion",
      "/showcase": "Showcase — Matemium",
      "/download": "Download — Matemium",
      "/support": "Support Matemium",
      "/roadmap": "Roadmap — Matemium",
      "/source": "Source & license — Matemium",
      "/login": "Sign in — Matemium",
    };
    document.title = titles[pathname] ?? "Matemium";
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main>
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  );
}
