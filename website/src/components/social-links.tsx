import type { CSSProperties } from "react";

import { SOCIAL_LINKS } from "@/content/socials";

type SocialLinkGridProps = {
  compact?: boolean;
};

export function SocialLinkGrid({ compact = false }: SocialLinkGridProps) {
  return (
    <div className={`social-link-grid ${compact ? "social-link-grid-compact" : ""}`}>
      {SOCIAL_LINKS.map((item) => (
        <a
          key={item.id}
          href={item.href}
          target={item.email ? undefined : "_blank"}
          rel={item.email ? undefined : "noreferrer"}
          className="social-link-card"
          style={{ "--social-accent": item.accent } as CSSProperties}
        >
          <span className="social-link-card-top">
            <span className="social-link-mark" aria-hidden>{item.mark}</span>
            <span className="social-link-arrow" aria-hidden>↗</span>
          </span>
          <strong>{item.label}</strong>
          <span className="social-link-handle">{item.handle}</span>
          <p>{item.description}</p>
        </a>
      ))}
    </div>
  );
}

export function SocialLinkStrip() {
  return (
    <div className="social-link-strip" aria-label="Matemium social links">
      {SOCIAL_LINKS.map((item) => (
        <a
          key={item.id}
          href={item.href}
          target={item.email ? undefined : "_blank"}
          rel={item.email ? undefined : "noreferrer"}
          aria-label={`${item.label}: ${item.handle}`}
          title={`${item.label} · ${item.handle}`}
          style={{ "--social-accent": item.accent } as CSSProperties}
        >
          <span aria-hidden>{item.mark}</span>
          <strong>{item.label}</strong>
        </a>
      ))}
    </div>
  );
}
