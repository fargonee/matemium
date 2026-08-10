# Show HN: Matemium – a local layout-to-animation compiler built on Manim

I built Matemium because I kept running into the same problem when authoring technical animations: the explanation was structured like a document, but the code was structured like a long sequence of stage directions.

Matemium is a free, source-available desktop application and compiler for visual explanations. Authors write Python `scenes.py` files with a higher-level `CanvasBuilder` / `CanvasScene` API. The compiler handles layout, persistent object identity, camera movement, staged reveals, validated transitions, and compilation to Manim. Rendering happens locally.

The central abstraction is an infinite reasoning tape. Content is laid out on a vertical plane; the camera scrolls through it, and revealed elements remain registered so later steps can revisit or transform them. It works well for arguments where earlier equations, definitions, or diagrams should remain spatially meaningful instead of being recreated slide by slide.

There is also a separate free 3D world. Camera-facing tapes are intentionally not modeled as arbitrary pieces of 3D geometry: selecting one hides the world and other tapes, giving the explanation a clean analytical surface. Inspecting a world object opens the spatial context again. That “curtain” boundary is one of the architectural decisions I would especially like people to challenge.

The current generic visual layer includes sampled `DataPath`, `DataPlot`, and node-edge `Diagram` elements. Their parts have stable semantic IDs, so a timeline action can say, for example, “emphasize this node and edge while dimming that series.” `StateTransition` handles synchronized property changes; `ElementMorph` replaces compiled content or geometry. The data stays finite and serializable so it can be checked before render.

The desktop boundary is TypeScript UI → Tauri/Rust → a platform-specific Python sidecar → Manim. The cloud is optional and thin: authentication and user-directed BYO model requests, not rendering. Matemium does not sell AI credits. AI can assist with the same project artifacts a human edits, while the more ambitious persistent, verification-gated autonomous runtime remains ongoing work rather than something I want to oversell.

It currently supports local 9:16 and 16:9 renders, tape/world composition, generic visuals, project checks, full-sheet export, and desktop project workspaces. The source library contains examples across several subjects, but they are at different review stages and are not all final showcase pieces.

The rough parts are real: FFmpeg and LaTeX remain host prerequisites, signing/notarization is incomplete where credentials are unavailable, some world/camera and timed-media seams need work, and installation needs more clean-machine evidence. The project is source-available rather than open-source; the license permits inspection, specified use, private modification, contribution forks, and contributions to the official project, but restricts redistribution and competing builds.

I could keep testing only the paths I already understand, but that is a poor way to discover whether the abstraction holds up. I would value code review, architectural criticism, installation reports, strange use cases, and ugly render bugs.

Canonical explanation and links: [WEBSITE_URL]/articles/introducing-matemium
