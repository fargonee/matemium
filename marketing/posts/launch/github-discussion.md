# Matemium is public — what should we improve first?

I’m releasing Matemium early enough that real users and contributors can still change its direction.

Matemium is a free, source-available desktop application and layout-to-animation compiler for structured visual explanations. The compiler and desktop foundation work, but this is not a “feedback welcome” message attached to a product I consider finished. I am actively looking for evidence about what breaks outside the projects and machines used to build it.

If you try Matemium, please share any of the following:

- **Installation problems:** operating system, package type, prerequisite setup, warning/error text, and whether the sidecar starts.
- **Rendering bugs:** the smallest project that reproduces the issue, selected scene and quality, logs, and—when safe—a screenshot or output excerpt.
- **API friction:** builder methods or concepts that feel difficult, inconsistent, over-specialized, or under-specified.
- **Confusing UX:** places where the project structure, tape/world model, preview, render state, or AI workflow does not explain itself.
- **Missing visual primitives:** especially needs that recur across unrelated subjects and cannot be handled cleanly with paths, plots, diagrams, state transitions, morphs, or project helpers.
- **Architecture criticism:** TypeScript/Rust/Python boundaries, source model, validation strategy, tape/world separation, agent design, or anything else that deserves challenge.
- **Documentation gaps:** setup assumptions, misleading examples, missing reference details, or explanations that only make sense if you already know the engine.
- **Contribution proposals:** a bug fix, test, guide, platform improvement, example repair, generic abstraction, or scoped design discussion you would like to take on.

Please distinguish compile success from visual or domain correctness. A minimal repro and actual render evidence are especially useful.

Start here: [WEBSITE_URL]/articles/introducing-matemium

Downloads: [DOWNLOAD_URL]

Contribution guide: [GITHUB_URL]/blob/main/CONTRIBUTING.md
