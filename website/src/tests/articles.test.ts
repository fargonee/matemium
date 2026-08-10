import { describe, expect, it } from "vitest";

import { ARTICLES, articleBySlug } from "@/content/articles";

describe("article content collection", () => {
  it("keeps draft templates out of the published collection", () => {
    expect(articleBySlug("article-slug")).toBeUndefined();
  });

  it("contains unique, sorted, valid published entries", () => {
    expect(new Set(ARTICLES.map((article) => article.slug)).size).toBe(ARTICLES.length);
    expect(ARTICLES.every((article) => articleBySlug(article.slug) === article)).toBe(true);
    expect(ARTICLES.every((article) => article.readingMinutes >= 1)).toBe(true);
    expect(ARTICLES.map((article) => article.published)).toEqual(
      [...ARTICLES].sort((left, right) => right.published.localeCompare(left.published)).map((article) => article.published),
    );
  });
});
