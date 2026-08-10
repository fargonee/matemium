# I built a source-available desktop compiler for structured visual explanations

I’m the creator of Matemium. It is a free desktop application and layout-to-animation compiler built on Manim Community Edition.

The problem I wanted to solve was not “how do I draw an equation?” Manim already gives Python authors powerful primitives. The problem was keeping a long explanation coherent when layout, camera position, reveal timing, and object state are all managed imperatively.

In Matemium, a project has a visible Python `scenes.py` entrypoint. Authors use `CanvasBuilder` and `CanvasScene`; the engine compiles that into an internal timeline and Manim scene. Content can live on an infinite vertical reasoning tape, while persistent spatial objects live in a separate 3D world. Additional tapes are isolated camera-facing contexts, not arbitrary planes composited into the world.

The architecture has deliberately hard boundaries:

- TypeScript desktop UI
- Tauri/Rust for filesystem and process orchestration
- a platform-specific Python sidecar for checking and rendering
- Manim, FFmpeg, and LaTeX on the local machine

There is no cloud render service. Optional cloud functionality is limited to things such as auth and user-directed requests to the user’s own AI provider. AI-assisted edits and manual edits go through the same project and render pipeline.

The generic authoring API currently includes sampled paths and plots, semantic node-edge diagrams, state transitions, morphs, persistent IDs, focus/camera actions, 3D surfaces and solids, static sheet export, and portrait/landscape profiles. I am trying to keep subject-specific logic in project helpers instead of growing the compiler around one lesson.

This is source-available, not open-source. The license permits inspection, personal/educational/research/internal use, private modifications, contribution forks, and contributions to the official project. It restricts redistribution, derivative public builds, hosted versions, and competing forks without permission.

The launch is early. Host FFmpeg/LaTeX setup still creates friction, signing is incomplete on some builds, parts of the spatial authoring API are younger than the root-tape path, and the autonomous-agent architecture is not fully realized. I’m releasing now because outside usage will expose more than polishing my own examples can.

I would genuinely like feedback on the compiler boundaries, API shape, packaging, and contribution model—even if your conclusion is that one of them is wrong.

Main link: [GITHUB_URL]
