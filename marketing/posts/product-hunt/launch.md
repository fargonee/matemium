# Product Hunt launch kit

## Product name

Matemium

## Tagline

Turn structured ideas into locally rendered visual explanations

## Short description

Matemium is a free, source-available desktop studio and layout-to-animation compiler built on Manim. Author inspectable Python projects—with AI assistance—and render vertical or landscape explanations on your own machine.

## First comment / maker comment

Hi Product Hunt — I’m the builder behind Matemium.

I started this project because writing a substantial technical animation often meant spending more time coordinating positions, camera moves, object lifetimes, and transitions than thinking about the explanation itself.

Matemium treats that as a compiler problem. A project describes structured content through Python `scenes.py` using `CanvasBuilder` and `CanvasScene`. The engine handles layout, persistent visual identities, validated actions, and compilation to Manim. Its main canvas is an infinite vertical reasoning tape, but projects can also move into a free 3D world and return to isolated camera-facing tapes for equations, plots, or diagrams.

Everything renders locally. The desktop app uses a TypeScript interface, a Tauri/Rust shell, and a Python sidecar that runs Matemium and Manim on the user’s computer. AI can help work on the same inspectable project files, using the user’s own provider access; Matemium does not sell AI credits or send rendering to a cloud farm.

I’m launching before the product has reached imaginary “perfect” status. That is intentional. Installation still needs more clean-machine testing, FFmpeg and LaTeX remain host prerequisites, some builds may show signing or notarization warnings, and the most ambitious autonomous production workflow still needs harder verification and evaluation. The example library also contains projects at different review stages rather than a wall of finished showcase pieces.

The foundation is working, and keeping it private would now hide more problems than it solves. I want early users to try subjects and workflows I did not anticipate, tell me where the API is awkward, share failed renders, and question the product architecture. Those reports can shape Matemium while its abstractions are still changeable.

Matemium is free and source-available—not open-source. You can inspect the code, use it for the purposes described in the license, make permitted private modifications, and contribute improvements to the official project. Please read the license for the exact boundaries.

If you make visual explanations, teach, work with Manim, or build local creative tools, I would be grateful for a candid first run. What should become simpler first?

## Five feature bullets

- Infinite reasoning tape with persistent, revisitable visual elements
- Separate free 3D world and isolated camera-facing analytical tapes
- Python `scenes.py` authoring with `CanvasBuilder` and AI assistance
- Generic paths, plots, diagrams, semantic transitions, and morphs
- Local 9:16 and 16:9 rendering through Matemium + Manim

## Suggested gallery screenshot captions

1. **One project, visible artifacts** — Edit `scenes.py`, inspect the project brief, and keep source, assets, and renders together.
2. **Reasoning that stays spatially coherent** — Build a vertical tape where equations, explanations, plots, and diagrams remain available to revisit.
3. **From analytical tape to 3D world** — Move between readable camera-facing reasoning and persistent spatial objects.
4. **AI assistance with inspectable output** — Review project-aware edits instead of receiving an opaque generated animation.
5. **Render on your machine** — Produce portrait or landscape video locally through the bundled Matemium sidecar and host rendering tools.

## Links

- Suggested primary link: [WEBSITE_URL]/articles/introducing-matemium
- Suggested secondary link: [DOWNLOAD_URL]
- Suggested secondary link: [GITHUB_URL]
- Suggested secondary link: [DEMO_URL]
