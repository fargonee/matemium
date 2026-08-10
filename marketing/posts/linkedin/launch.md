# I’m releasing Matemium before it feels finished

Today I’m launching Matemium publicly.

It is a free, source-available desktop application and layout-to-animation compiler for structured visual explanations. It began with mathematics, but the underlying system is meant for any subject that benefits from staged reasoning: equations, text, paths, plots, diagrams, persistent objects, a free 3D world, camera-facing reasoning tapes, and a camera that moves with purpose.

The project started from a practical frustration. When I tried to build longer technical animations, the code often became dominated by coordination: where every object should sit, when it should appear, what the camera should frame, what remained alive, and how one state should become the next. The explanation I cared about was still there, but it was surrounded by stage directions.

Matemium became my attempt to treat that as a compiler problem.

Authors work with visible Python projects through `scenes.py`, `CanvasBuilder`, and `CanvasScene`. The engine lays out content on an infinite reasoning tape, gives visual elements persistent identities, validates transitions, and compiles the result to Manim. Projects can move between that analytical tape and a separate 3D world, then render locally in 9:16 or 16:9.

The desktop application wraps the engine with a TypeScript interface, a Tauri/Rust shell, and a Python sidecar. AI can help work on the same project artifacts that a person can inspect and edit. It does not replace the compiler, and rendering does not move to a cloud farm.

I also want to acknowledge how I built it. I used free AI resources heavily and iterated intensely: asking for implementations, inspecting results, finding contradictions, rewriting architecture, running tests, repairing broken builds, and trying again. AI accelerated the amount of ground I could cover as an independent builder. It did not remove the need to decide what the product should be, keep the layers coherent, verify claims against code, or look at actual output.

There is a larger AI production vision in the repository: an agent that can understand a project, maintain durable creative artifacts, make scoped edits, render, inspect evidence, recover from failures, and refuse to call a task complete without verification. Parts of that system exist. The full standard does not yet.

That distinction is one reason I decided to launch now.

There is always another private milestone that can be labeled “before launch.” Cleaner onboarding. More polished examples. Better signing. Stronger visual evaluation. More reliable agent behavior. A longer list can feel responsible while also delaying the only test that matters now: what happens when people who did not build Matemium try to use it?

I could continue optimizing for my own machine and my own mental model. Instead, I want installation failures, confusing UI reports, ugly renders, API criticism, missing primitives, and architectural disagreements while the project is still malleable. This is not an apology for releasing something incomplete. It is a choice to let evidence guide the next version.

Matemium is source-available, not open-source. People can inspect the code, use it under the Matemium license, make permitted private modifications, and contribute to the official project. The license restricts redistribution, derivative public builds, hosted versions, and competing forks without permission. That keeps the official product coherent while making external technical contribution possible.

I hope Matemium reaches educators, Manim authors, Python developers, technical artists, scientists, engineers, and people building local-first or AI-assisted creative tools. You do not need to arrive with praise. A precise report about where it fails is more useful.

The full launch article explains the architecture, what works today, and what remains rough:

[WEBSITE_URL]/articles/introducing-matemium
