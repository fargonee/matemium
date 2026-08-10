import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { articleBySlug } from "@/content/articles";
import { projectBySlug } from "@/content/showcase";

const DEFAULT_DESCRIPTION = "Matemium is a free, source-available agentic studio for turning complex ideas into visual stories with local rendering.";
const ARTICLES_DESCRIPTION = "Engineering notes, product stories, tutorials, launch notes, and deeper explanations from the people building Matemium.";

function setMetaTag(selector: string, attribute: "name" | "property", key: string, content?: string) {
  let element = document.head.querySelector<HTMLMetaElement>(selector);
  if (!content) {
    element?.remove();
    return;
  }
  if (!element) {
    element = document.createElement("meta");
    element.setAttribute(attribute, key);
    document.head.append(element);
  }
  element.content = content;
}

export function RootLayout() {
  const { pathname } = useLocation();

  useEffect(() => {
    const titles: Record<string, string> = {
      "/": "Matemium — Give complex ideas motion",
      "/showcase": "Showcase — Matemium",
      "/articles": "Articles — Matemium",
      "/download": "Download — Matemium",
      "/support": "Support Matemium",
      "/connect": "Connect with Matemium",
      "/roadmap": "Roadmap — Matemium",
      "/source": "Source & license — Matemium",
      "/login": "Sign in — Matemium",
    };
    const showcaseProject = pathname.startsWith("/showcase/")
      ? projectBySlug(pathname.slice("/showcase/".length))
      : undefined;
    const article = pathname.startsWith("/articles/")
      ? articleBySlug(pathname.slice("/articles/".length))
      : undefined;
    const title = article
      ? `${article.title} — Matemium`
      : titles[pathname] ?? (showcaseProject ? `${showcaseProject.title} — Matemium` : "Matemium");
    const description = article?.description
      ?? showcaseProject?.description
      ?? (pathname === "/articles" ? ARTICLES_DESCRIPTION : DEFAULT_DESCRIPTION);
    const canonicalUrl = `${window.location.origin}${window.location.pathname}`;

    document.title = title;
    setMetaTag('meta[name="description"]', "name", "description", description);
    setMetaTag('meta[property="og:title"]', "property", "og:title", title);
    setMetaTag('meta[property="og:description"]', "property", "og:description", description);
    setMetaTag('meta[property="og:type"]', "property", "og:type", article ? "article" : "website");
    setMetaTag('meta[property="og:url"]', "property", "og:url", canonicalUrl);
    setMetaTag('meta[property="og:image"]', "property", "og:image", article?.heroImage ? new URL(article.heroImage, window.location.origin).toString() : undefined);
    setMetaTag('meta[property="article:published_time"]', "property", "article:published_time", article?.published);
    setMetaTag('meta[property="article:modified_time"]', "property", "article:modified_time", article?.updated);
    setMetaTag('meta[name="twitter:card"]', "name", "twitter:card", article?.heroImage ? "summary_large_image" : "summary");

    let canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement("link");
      canonical.rel = "canonical";
      document.head.append(canonical);
    }
    canonical.href = canonicalUrl;
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
