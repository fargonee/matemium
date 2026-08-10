---
title: "Introducing Matemium"
slug: "introducing-matemium"
description: "Why I built a local, source-available layout-to-animation compiler for structured visual explanations—and why I am releasing it before it feels finished."
published: "2026-08-10"
author: "Matemium"
category: "Launch"
tags:
  - "Matemium"
  - "Visual explanations"
  - "Developer tools"
status: "published"
---

Today I am releasing Matemium: a free, source-available desktop application and layout-to-animation compiler for structured visual explanations.

Matemium began with mathematics, but the underlying problem is broader. Many subjects become easier to understand when an explanation can combine text, equations, paths, plots, diagrams, persistent objects, spatial scenes, and a camera that moves through the reasoning deliberately. The difficult part is not always drawing those things. It is coordinating them without turning every project into a pile of fragile animation instructions.

I could keep improving Matemium privately until every workflow looked polished in a controlled demo. That would also keep its most important weaknesses hidden. I would rather put the real system in front of people who will install it differently, explain unfamiliar subjects with it, challenge the API, and notice the assumptions I have stopped seeing.

This is an early public launch, not a declaration that the work is finished.

## The authoring problem

Matemium is built on [Manim Community Edition](https://www.manim.community/), a powerful Python animation engine. Manim makes it possible to construct precise mathematical and technical visuals, but a substantial explanation still asks the author to manage many concerns at once: positions, timing, camera framing, object lifetimes, transitions, and the relationship between one step and the next.

Imperative scene code is useful when every beat is intentionally handcrafted. It becomes harder to maintain when the explanation itself is document-like: introduce an equation, preserve it, add an observation below it, move to a plot, revisit an earlier object, compare two states, then leave the flat reasoning surface for a three-dimensional inspection.

The code can end up describing the mechanics of animation more loudly than the idea being explained.

Matemium approaches that problem as a compiler. An author describes structured content and a timeline through a higher-level Python API. The engine measures and lays out the content, assigns persistent identities, validates references, compiles camera and transition actions, and produces a Manim scene for local rendering.

The goal is not to hide code. It is to make the code speak in the vocabulary of an explanation.

## An infinite reasoning tape

The original Matemium model is an infinite vertical tape. Content lives on a flat XY plane, with Y acting as the scroll direction. The camera moves down the tape as new material is introduced. Elements appear when the viewport reaches them, then remain registered so later actions can revisit or change them.

This creates a different rhythm from a sequence of disconnected slides. Earlier reasoning can remain spatially present. A camera move can return to a definition or equation instead of reconstructing it. A long explanation can also be exported as a static PNG or PDF, or divided into shorter video segments.

Portrait output is a first-class target: `CanvasSettings.for_reels()` produces a 9:16 scene. The same system also supports 16:9 authoring through `CanvasSettings.for_youtube()`. Changing resolution does not magically redesign a composition, so each intended orientation still needs inspection.

The root tape is the production-safe default, but it is not the entire spatial model.

## Camera-facing tapes and the free 3D world

Matemium also has a free three-dimensional world for persistent objects, mathematical surfaces, built-in solids, transforms, and camera inspection paths. Additional tapes can provide separate, camera-facing analytical surfaces within a project.

The distinction matters. A tape is not a physical sheet floating arbitrarily in the world. It is an isolated presentation context: when a tape is selected, it faces the camera and hides the free world and every other tape. Selecting another tape replaces it. Observing a world object opens the world again. The transition is deliberately treated as a controlled curtain and camera cut, not as several unreadable canvases competing in the same frame.

That boundary lets a project move between two useful visual languages. The world can establish space, motion, and physical relationships. A tape can stop the camera and explain something with stable text, equations, plots, or diagrams. Then the project can return to the same registered world objects without pretending the analytical surface is ordinary 3D geometry.

This world-and-tape composition path is implemented and exercised, but its ergonomics are still younger than the root-tape workflow. Low-level world placement and camera keyframes remain specialist tools that need careful preview evidence.

## The project is visible Python

The normal authoring artifact is `scenes.py`. Authors use `CanvasBuilder` to describe content and actions, then pass the compiled internal representation to `CanvasScene`:

```python
from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder


class FallingOrbit(CanvasScene):
    def __init__(self, **kwargs):
        builder = CanvasBuilder(
            title="Why an orbit keeps falling",
            canvas_settings=CanvasSettings.for_reels(title="Orbit"),
        )
        builder.add_heading("An orbit is continuous free fall")
        builder.add_body("Gravity bends the path as the object moves forward.")
        builder.add_math(r"a = \frac{v^2}{r}")
        super().__init__(dsl=builder.build(), **kwargs)
```

`SheetDSL` exists inside the compiler, but it is not the product authoring format. People and AI work on the same reviewable Python project. Subject calculations, simulations, source data, and domain-specific helpers can live in `helpers.py`; the engine is kept for reusable visual, layout, camera, and timeline abstractions.

For larger projects, `# ---DIV: ...---` section fences make a long `scenes.py` navigable in the desktop editor without turning the project into generated fragments. A workspace can also carry a durable brief, tape content, orchestration notes, assets, and render history. Those artifacts preserve intent; `scenes.py` remains the required render entrypoint.

## Generic visuals, stable parts, and change over time

Matemium started with equation and layout primitives, but a cross-subject system needs more than text and formulas. The current production authoring surface includes three generic sampled visual types:

- `DataPath` represents a trajectory, contour, route, vector, or other sampled path.
- `DataPlot` represents one or more sampled series, axes, and named markers.
- `Diagram` represents explicit nodes, directed or undirected edges, and labels.

These structures use finite, JSON-compatible data. They can be validated before a render and computed in project helpers without embedding arbitrary subject logic in the engine.

Their internal parts also have stable semantic names. A plot can expose `axes`, `series:measured`, and `marker:current`; a diagram can expose `node:sensor` or `edge:measurement`. `StateTransition` can then change allowlisted properties on several whole elements or semantic parts in one timeline beat. `ElementMorph` is used when compiled content or geometry must be replaced.

This is important for explanatory animation. “Emphasize the sensor, thicken the measurement edge, and dim the reference series together” is a more useful authoring instruction than a collection of unrelated low-level object mutations.

The generic visuals are currently sampled and staged rather than reactive. Matemium does not yet promise a shared simulation clock, generic timed traversal along every path or plot, or automatic domain-specific layout. Those remain open problems.

## AI assists the project; it is not the render engine

AI is intended to act as a production coworker around real project artifacts. In the current desktop application, people can work with project-aware chat and agent paths while retaining the same inspectable `scenes.py`, helpers, briefs, checks, and local render pipeline used for manual edits.

The architectural direction goes further: a bounded agent should understand the project, make scoped edits, compile, inspect evidence, recover from ordinary failures, and only report completion after verification gates pass. The production lifecycle is designed around persistent decisions and artifacts rather than a one-shot prompt.

That complete autonomous runtime is not something I consider finished. Persistent run state, reliable phase management, visual verification, evaluation, recovery, and false-completion control are active engineering work. Today, AI assistance is useful, but users should review proposed changes and actual renders—especially for mathematical accuracy, pacing, and visual composition.

Matemium does not sell model access or provide pooled AI credits. Users connect their own external provider access, with OpenRouter as the default provider path, or use supported local options. Optional cloud services can help with authentication, profiles, and user-directed model requests. They do not render videos.

## Rendering stays on your machine

The desktop architecture has three clear boundaries:

```text
TypeScript interface → Tauri/Rust shell → Python sidecar → Manim
```

The interface manages the project, editor, AI interaction, preview, and output history. Rust owns filesystem and process orchestration. A platform-specific Python sidecar imports the project, checks it, and runs the Matemium/Manim render locally. Progress and results return through structured IPC.

There is no cloud render farm and no upload of full project directories or rendered media for compute. Local rendering gives the author direct control over source and outputs, but it also means the machine needs the rendering prerequisites. The desktop installers bundle Matemium and its sidecar; FFmpeg and a compatible LaTeX distribution still need to be installed on the host. Windows and macOS builds may also show trust warnings until signing and notarization are fully configured.

## What works today

The repository currently includes:

- root-tape text and mathematics, CSS-like block styling, rich text runs, and flex composition;
- persistent element identities, lazy reveal, camera movement, focus modes, state transitions, and morphs;
- sampled paths and plots plus semantic node-edge diagrams;
- equation-backed 3D surfaces, built-in solids, registered world objects, lift/rotation actions, and camera inspection;
- additional camera-facing tapes with explicit scrolling and isolated world/tape switching;
- strict structural validation and project checks before committing to a full render;
- portrait and landscape profiles, local video rendering, full-sheet PNG/PDF export, and reel-cutting tools;
- a Tauri desktop workspace with code editing, AI assistance, preview/render workflows, project archives, and bundled editable examples;
- native build pipelines for Linux, Windows, Apple Silicon macOS, and Intel macOS.

The example library covers multiple subjects, but it should be read honestly: the projects are authoring proofs and engine evidence at different review stages. They are not all final, independently reviewed showcase masters.

## What is still rough

Installation needs more clean-machine testing. Rendering prerequisites add friction. Signing and notarization are incomplete where credentials are not configured, automatic application updates are not enabled, and initial Linux/Windows packages target x86_64.

Some engine seams still need work: world-camera composition, timed media and audio, reel-cutting polish, generic traversal, and broader visual primitives. More examples need final render review, accessibility work, and independent domain review. Documentation will improve fastest when new users reveal which concepts are obvious only to the person who built them.

The ambitious autonomous production model also needs harder evaluation. A compiler passing does not prove that an explanation is visually clear or factually correct. Matemium needs better visual evidence inspection, recovery behavior, agent accounting, and real-world task benchmarks before that experience deserves strong claims.

## Why release now

Software like this can look complete for a long time when its creator controls every example. A new subject, an unfamiliar machine, or a contributor with a different mental model is more revealing than another month of polishing the same path.

I am launching Matemium because the foundation is real enough to be useful and incomplete enough that outside use can still shape it. I want installation reports, awkward APIs, rendering failures, confusing concepts, missing visual primitives, architectural disagreements, and examples that do not fit the abstractions cleanly.

Matemium is source-available, not open-source. Under the Matemium Source-Available License, people can inspect and study the code, use it for permitted personal, educational, research, nonprofit, and internal purposes, make private modifications, prepare contribution forks, and contribute to the official project. Redistribution, derivative public builds, commercial exploitation of the software, hosted versions, and competing forks require written permission. Content created with Matemium remains the creator's and may be used commercially.

That model is meant to make serious collaboration possible while keeping official distribution coherent. Read the license before relying on a particular use.

If Matemium interests you, try it on something I did not design for. Tell me where the model breaks. Open an issue with an ugly render. Question the tape/world boundary. Improve a validator, a platform build, a guide, or an example. The useful version of this project will be built from evidence, and I do not want all of that evidence to come from me.

- GitHub and issues: [GITHUB_URL]
- Download: [DOWNLOAD_URL]
- Demo: [DEMO_URL]
- Documentation: [DOCS_URL]
