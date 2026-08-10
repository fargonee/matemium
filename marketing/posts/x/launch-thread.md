# X launch thread

## Thread

### 1/9

Matemium is live: a free, source-available desktop studio and layout-to-animation compiler for structured visual explanations. It uses Manim, renders locally, and is ready for honest early feedback.

[WEBSITE_URL]/articles/introducing-matemium

### 2/9

Technical animation code can become a list of positions, camera moves, waits, and object mutations. The explanation gets buried under stage directions. I wanted the code to describe the reasoning more directly.

### 3/9

Matemium’s core model is an infinite reasoning tape. Content flows vertically; the camera moves through it; revealed equations, diagrams, and plots keep stable identities so later steps can revisit or change them.

### 4/9

The tape is not the whole scene. Matemium also has a free 3D world for persistent spatial objects. Camera-facing tapes are isolated analytical contexts, so readable reasoning and 3D inspection do not compete in the same frame.

### 5/9

Projects remain visible Python: `scenes.py`, `CanvasBuilder`, and `CanvasScene`. AI can help edit the same project artifacts a person edits. The more ambitious verification-gated autonomous workflow is still active work.

### 6/9

Rendering stays on your machine through a Tauri desktop shell and Python sidecar running Matemium + Manim. No cloud render farm. External AI uses your provider access; Matemium does not sell pooled model credits.

### 7/9

Matemium is source-available, not open-source. The license supports inspection, specified uses, permitted private changes, and contributions to the official project, while restricting redistribution and competing builds.

### 8/9

It is early. FFmpeg and LaTeX are still host prerequisites, signing needs work on some builds, examples are at different review stages, and parts of the spatial and agent workflows need more evidence.

### 9/9

I could keep tuning Matemium against my own examples, or let real use expose the weak assumptions. I chose the second. Try it, break it, question the architecture, and tell me what should improve first.

[WEBSITE_URL]/articles/introducing-matemium

## Standalone ultra-short post

Matemium is live: an early, local-first, source-available compiler for animated visual explanations. Built on Manim, shaped in public from here.

[WEBSITE_URL]/articles/introducing-matemium
