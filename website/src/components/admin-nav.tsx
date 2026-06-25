import { Link, useLocation } from "react-router-dom";

const links = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/subscriptions", label: "Subscriptions" },
];

export function AdminNav() {
  const { pathname } = useLocation();

  return (
    <nav className="flex flex-wrap gap-2">
      {links.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            to={link.href}
            className={[
              "rounded-full px-4 py-2 text-sm font-medium transition",
              active
                ? "bg-accent/15 text-text"
                : "text-text-muted hover:bg-bg-card hover:text-text",
            ].join(" ")}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}