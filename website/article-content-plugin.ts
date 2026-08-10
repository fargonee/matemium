import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import matter from "gray-matter";
import type { Plugin } from "vite";

const VIRTUAL_MODULE_ID = "virtual:matemium-articles";
const RESOLVED_VIRTUAL_MODULE_ID = `\0${VIRTUAL_MODULE_ID}`;
const ARTICLE_FILE_PATTERN = /\.md$/i;
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

type ArticleStatus = "draft" | "published";

interface ArticleSource {
  title: string;
  slug: string;
  description: string;
  published: string;
  updated?: string;
  author: string;
  category?: string;
  tags: string[];
  heroImage?: string;
  status: ArticleStatus;
  body: string;
  readingMinutes: number;
}

type PublishedArticleSource = Omit<ArticleSource, "status">;

function requireString(value: unknown, field: string, fileName: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${fileName}: frontmatter field \"${field}\" must be a non-empty string.`);
  }
  return value.trim();
}

function optionalString(value: unknown, field: string, fileName: string): string | undefined {
  if (value === undefined || value === null || value === "") return undefined;
  return requireString(value, field, fileName);
}

function normalizeDate(value: unknown, field: string, fileName: string): string {
  const normalized = value instanceof Date
    ? value.toISOString().slice(0, 10)
    : requireString(value, field, fileName);

  const parsedDate = new Date(`${normalized}T00:00:00Z`);
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(normalized)
    || Number.isNaN(parsedDate.valueOf())
    || parsedDate.toISOString().slice(0, 10) !== normalized
  ) {
    throw new Error(`${fileName}: frontmatter field \"${field}\" must use YYYY-MM-DD.`);
  }
  return normalized;
}

function normalizeTags(value: unknown, fileName: string): string[] {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value) || value.some((tag) => typeof tag !== "string" || tag.trim() === "")) {
    throw new Error(`${fileName}: frontmatter field \"tags\" must be a list of non-empty strings.`);
  }
  return value.map((tag) => tag.trim());
}

function calculateReadingMinutes(markdown: string): number {
  const readableText = markdown
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/~~~[\s\S]*?~~~/g, " ")
    .replace(/`[^`]*`/g, " ")
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/<[^>]+>/g, " ")
    .replace(/[#>*_|~-]/g, " ");
  const words = readableText.match(/[\p{L}\p{N}]+(?:['’][\p{L}\p{N}]+)?/gu)?.length ?? 0;
  return Math.max(1, Math.ceil(words / 220));
}

function parseArticle(filePath: string): ArticleSource {
  const fileName = path.basename(filePath);
  const { data, content } = matter(readFileSync(filePath, "utf8"));
  const status = requireString(data.status, "status", fileName);
  if (status !== "draft" && status !== "published") {
    throw new Error(`${fileName}: frontmatter field \"status\" must be \"draft\" or \"published\".`);
  }

  const slug = requireString(data.slug, "slug", fileName);
  if (!SLUG_PATTERN.test(slug)) {
    throw new Error(`${fileName}: slug must contain lowercase letters, numbers, and single hyphens only.`);
  }

  const published = normalizeDate(data.published, "published", fileName);
  const updated = data.updated === undefined
    ? undefined
    : normalizeDate(data.updated, "updated", fileName);
  if (updated && updated < published) {
    throw new Error(`${fileName}: \"updated\" cannot be earlier than \"published\".`);
  }

  return {
    title: requireString(data.title, "title", fileName),
    slug,
    description: requireString(data.description, "description", fileName),
    published,
    updated,
    author: requireString(data.author, "author", fileName),
    category: optionalString(data.category, "category", fileName),
    tags: normalizeTags(data.tags, fileName),
    heroImage: optionalString(data.heroImage, "heroImage", fileName),
    status,
    body: content.trim(),
    readingMinutes: calculateReadingMinutes(content),
  };
}

function loadPublishedArticles(contentDirectory: string): PublishedArticleSource[] {
  const sourceFiles = readdirSync(contentDirectory)
    .filter((fileName) => ARTICLE_FILE_PATTERN.test(fileName))
    .sort();
  const articles = sourceFiles.map((fileName) => ({
    fileName,
    article: parseArticle(path.join(contentDirectory, fileName)),
  }));
  const seenSlugs = new Map<string, string>();

  for (const { fileName, article } of articles) {
    const previousFile = seenSlugs.get(article.slug);
    if (previousFile) {
      throw new Error(`${fileName}: duplicate article slug \"${article.slug}\" (also used by ${previousFile}).`);
    }
    seenSlugs.set(article.slug, fileName);
  }

  return articles
    .flatMap(({ fileName, article }) => {
      const { status, ...publishedArticle } = article;
      return !fileName.startsWith("_") && status === "published" ? [publishedArticle] : [];
    })
    .sort((left, right) => right.published.localeCompare(left.published));
}

export function articleContentPlugin(contentDirectory: string): Plugin {
  return {
    name: "matemium-article-content",
    resolveId(id) {
      return id === VIRTUAL_MODULE_ID ? RESOLVED_VIRTUAL_MODULE_ID : undefined;
    },
    load(id) {
      if (id !== RESOLVED_VIRTUAL_MODULE_ID) return undefined;

      const articleFiles = readdirSync(contentDirectory)
        .filter((fileName) => ARTICLE_FILE_PATTERN.test(fileName));
      for (const fileName of articleFiles) {
        this.addWatchFile(path.join(contentDirectory, fileName));
      }

      try {
        return `export default ${JSON.stringify(loadPublishedArticles(contentDirectory))};`;
      } catch (error) {
        this.error(error instanceof Error ? error.message : String(error));
      }
    },
    configureServer(server) {
      server.watcher.add(contentDirectory);
      server.watcher.on("all", (_event, changedPath) => {
        if (path.dirname(changedPath) !== contentDirectory || !ARTICLE_FILE_PATTERN.test(changedPath)) return;
        const module = server.moduleGraph.getModuleById(RESOLVED_VIRTUAL_MODULE_ID);
        if (module) server.moduleGraph.invalidateModule(module);
        server.ws.send({ type: "full-reload" });
      });
    },
  };
}
