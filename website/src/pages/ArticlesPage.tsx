import { Link } from "react-router-dom";

import { ARTICLES, formatArticleDate } from "@/content/articles";

export function ArticlesPage() {
  return (
    <>
      <section className="articles-hero">
        <div>
          <p className="section-kicker">Notes from the work</p>
          <h1>Articles</h1>
          <p>
            Engineering notes, product stories, tutorials, launch notes, and deeper
            explanations from the people building Matemium.
          </p>
        </div>
      </section>

      <section className="articles-index" aria-label="Published articles">
        {ARTICLES.length > 0 ? (
          <div className="article-list">
            {ARTICLES.map((article) => (
              <article key={article.slug} className="article-card">
                <div className="article-card-meta">
                  <time dateTime={article.published}>{formatArticleDate(article.published)}</time>
                  {article.category ? <span>{article.category}</span> : null}
                  <span>{article.readingMinutes} min read</span>
                </div>
                <h2>
                  <Link to={`/articles/${article.slug}`}>{article.title}</Link>
                </h2>
                <p>{article.description}</p>
                <Link to={`/articles/${article.slug}`} className="text-link" aria-label={`Read ${article.title}`}>
                  Read article <span aria-hidden>→</span>
                </Link>
              </article>
            ))}
          </div>
        ) : (
          <div className="articles-empty-state">
            <span aria-hidden>✦</span>
            <p className="section-kicker">The first story is in progress</p>
            <h2>Nothing published yet.</h2>
            <p>
              This is where long-form notes from Matemium will live. In the meantime,
              the documentation covers how to install, use, and extend the project.
            </p>
            <a href="https://docs.matemium.fargonee.space" className="button-secondary">
              Read the documentation <span aria-hidden>↗</span>
            </a>
          </div>
        )}
      </section>
    </>
  );
}
