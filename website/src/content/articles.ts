import articleRecords from "virtual:matemium-articles";

export interface Article {
  title: string;
  slug: string;
  description: string;
  published: string;
  updated?: string;
  author: string;
  category?: string;
  tags: string[];
  heroImage?: string;
  body: string;
  readingMinutes: number;
}

export const ARTICLES = articleRecords as Article[];

export function articleBySlug(slug: string): Article | undefined {
  return ARTICLES.find((article) => article.slug === slug);
}

export function formatArticleDate(date: string): string {
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${date}T00:00:00Z`));
}
