# Matemium documentation

The source for [docs.matemium.fargonee.space](https://docs.matemium.fargonee.space).
It is an Astro site built with Starlight and lives beside the engine, desktop app,
example projects, and public website so the documentation can stay aligned with the
software.

## Work locally

From this directory:

```bash
pnpm install
pnpm dev
```

Before publishing:

```bash
pnpm build
```

The generated site is written to `dist/`. Search, the sitemap, internal routes, and
optimized assets are produced as part of the build.

## Write documentation

Documentation pages live in `src/content/docs/`. Navigation is deliberately curated
in `astro.config.mjs`; when adding a page, place it in the right section there as well.

Keep examples tied to real APIs and real projects in this repository. If behavior
changes, update the relevant guide, reference page, and recipe in the same change.

## Publishing

This project is already connected to the documentation deployment. Pushing the
intended changes publishes them at the domain above.
