# I’m building an AI-assisted animation tool where the real artifact stays inspectable

I’m the creator of Matemium, a free, source-available desktop tool for producing structured visual explanations with a local Manim-based compiler.

The AI design starts from a constraint: the model should work on the same durable project artifacts as the user. The primary render entrypoint is a visible Python `scenes.py`, usually backed by `helpers.py`, a project brief, tape-content documents, orchestration notes, and render evidence. AI is not asked to emit an opaque animation JSON payload that only the application understands.

That gives the workflow useful pressure. A proposed change has to survive the same project check and local render path as a manual edit. The desktop can provide project-aware chat and agent workflows, while the local TypeScript → Rust → Python-sidecar boundary remains responsible for files, checks, and rendering. External model access is BYO; Matemium does not provide shared credits or own the user’s provider spend. There is no cloud rendering.

The longer-term agent model is deliberately more demanding than “put a ReAct loop behind a button.” The repository specifies persistent run state, scoped tools, resumable plans, typed errors, budgets, recovery rules, visual verification, and evidence-backed completion. It also defines a production lifecycle that keeps description, creative decisions, tape content, orchestration, code, and render validation as durable phases.

Some of that machinery exists; the complete autonomous runtime does not yet meet every target gate. I am being explicit about that because compiler success is not proof that an animation communicates the right idea. False completion is especially dangerous when the output can be visually polished but mathematically or narratively wrong.

What is usable today is the underlying compiler and desktop project path: infinite reasoning tapes, a separate 3D world, generic paths/plots/diagrams, semantic transitions, morphs, local checks and rendering, and AI assistance around inspectable source. The rough edges include setup prerequisites, spatial-authoring ergonomics, visual evaluation, and agent reliability.

I’m releasing it because building the agent against only my own projects would optimize for a very narrow distribution. I would like feedback from people working on coding agents, local-first tools, structured creative systems, or verification: which boundaries are useful, and which are ceremony without enough payoff?

I’m the creator. Canonical launch article: [WEBSITE_URL]/articles/introducing-matemium
