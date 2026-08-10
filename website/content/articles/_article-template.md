---
title: "Article title"
slug: "article-slug"
description: "A concise summary used on the Articles index and in social metadata."
published: "2026-01-01"
# updated: "2026-01-02"
author: "Matemium contributors"
category: "Engineering"
tags:
  - "Matemium"
  - "Technical notes"
# heroImage: "/media/articles/article-slug/hero.png"
status: "draft"
---

Open with a short paragraph that tells readers what this article will explain and why it matters. The page title and metadata are rendered from frontmatter, so the article body should begin with prose rather than another level-one heading.

## Section heading

Markdown supports paragraphs with [links](https://matemium.fargonee.space), **strong text**, and inline code such as `CanvasBuilder`.

- Use lists when they make a sequence or set easier to scan.
- Keep the narrative readable without relying on visual decoration.

> Blockquotes work well for a principle, conclusion, or short quotation.

### Code example

Fenced code blocks are syntax highlighted when their language is specified.

```python
from canvas.builder import CanvasBuilder

builder = CanvasBuilder(title="A structured visual story")
builder.add_heading("Begin with the idea")
```

### Table example

| Surface | Purpose |
| --- | --- |
| Docs | Product and technical documentation |
| Articles | Public long-form stories and explanations |

Images use normal Markdown syntax and should point to an asset within `website/public/`:

```markdown
![Descriptive alternative text](/media/articles/article-slug/example.png)
```

Before publishing, replace the placeholder metadata, set `status` to `published`, and rename this copied file without the leading underscore.
