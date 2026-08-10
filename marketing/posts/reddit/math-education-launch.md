# I made a tool for visual explanations where earlier reasoning stays on the page

I’m the creator of Matemium, and I’m releasing its first public version.

The idea came from a frustration with mathematical animation: a good explanation often needs to behave less like a slideshow and more like a continuous piece of reasoning. You introduce a definition, derive something below it, compare a graph with the equation, and later return to an earlier step. When each shot is manually staged, preserving that structure takes a lot of animation code.

Matemium uses an “infinite reasoning tape.” Text, equations, diagrams, and plots are laid out on a vertical surface. The camera moves through the tape, while revealed elements keep stable identities and can be focused, emphasized, transformed, or revisited later. The same project can target a vertical 9:16 explanation or a 16:9 video, although each orientation still needs human inspection.

For moments that need real space, Matemium also has a free 3D world. A project can inspect a persistent object or surface, then switch to a separate camera-facing tape to explain what the viewer just saw. The contexts are isolated on purpose so equations do not become unreadable decorations floating in a 3D scene.

Authors can work in Python through `scenes.py`, `CanvasBuilder`, and `CanvasScene`. The engine currently supports mathematical text, layout and flex composition, sampled paths and plots, node-edge diagrams, semantic state changes, morphs, camera focus, equation-backed surfaces, solids, and local rendering through Manim. AI assistance can help edit the project, but I do not want to pretend that visual or mathematical review can be automated away.

The example library reaches beyond mathematics into physics, chemistry, algorithms, engineering, biology, history, and other subjects. Those examples are at different review stages; they are evidence for the engine, not a claim that every lesson is publication-ready.

The application is free and source-available, not open-source. Rendering stays on the user’s computer and currently requires FFmpeg and LaTeX. This is an early launch because I want educators and visual explainers to reveal where the model is confusing, limiting, or simply wrong.

If you teach, make educational videos, or have fought with visualizing a proof or derivation, I would value feedback on what this approach still fails to express. I’m the creator, and criticism is the point of releasing it now.

Full explanation: [WEBSITE_URL]/articles/introducing-matemium
