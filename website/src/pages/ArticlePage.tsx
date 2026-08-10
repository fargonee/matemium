import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import { Link, Navigate, useParams } from "react-router-dom";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import { articleBySlug, formatArticleDate } from "@/content/articles";

type MarkdownLinkProps = ComponentPropsWithoutRef<"a"> & { node?: unknown };

function MarkdownLink({ href = "", children, node, ...props }: MarkdownLinkProps) {
  void node;
  if (href.startsWith("/")) {
    return <Link to={href}>{children}</Link>;
  }
  return <a href={href} {...props}>{children}</a>;
}

export function ArticlePage() {
  const { slug = "" } = useParams();
  const article = articleBySlug(slug);

  if (!article) return <Navigate to="/articles" replace />;

  return (
    <article className="article-page">
      <header className="article-header">
        <Link to="/articles" className="text-link">← Back to Articles</Link>
        <div className="article-header-meta">
          {article.category ? <span>{article.category}</span> : null}
          <time dateTime={article.published}>{formatArticleDate(article.published)}</time>
          <span>{article.readingMinutes} min read</span>
        </div>
        <h1>{article.title}</h1>
        <p className="article-description">{article.description}</p>
        <div className="article-byline">
          <span>By {article.author}</span>
          {article.updated ? (
            <span>Updated <time dateTime={article.updated}>{formatArticleDate(article.updated)}</time></span>
          ) : null}
        </div>
        {article.tags.length > 0 ? (
          <div className="article-tags" aria-label="Article tags">
            {article.tags.map((tag) => <span key={tag}>{tag}</span>)}
          </div>
        ) : null}
      </header>

      {article.heroImage ? (
        <figure className="article-hero-image">
          <img src={article.heroImage} alt="" />
        </figure>
      ) : null}

      <div className="article-prose">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
          components={{
            a: MarkdownLink,
            img: ({ alt = "", node, ...props }) => {
              void node;
              return <img alt={alt} loading="lazy" {...props} />;
            },
            table: ({ children, node, ...props }) => {
              void node;
              return (
                <div className="article-table-wrap">
                  <table {...props}>{children}</table>
                </div>
              );
            },
          }}
        >
          {article.body}
        </ReactMarkdown>
      </div>

      <footer className="article-end">
        <Link to="/articles" className="text-link">← More Matemium articles</Link>
      </footer>
    </article>
  );
}
