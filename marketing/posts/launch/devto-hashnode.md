---
title: "Why I Built Matemium: A Layout-to-Animation Compiler for Visual Explanations"
published: false
description: "A technical look at Matemium's compiler model, Python authoring API, tape/world composition, local desktop architecture, and early-launch tradeoffs."
tags:
  - python
  - devtools
  - animation
  - ai
---

> This is a developer-focused adaptation. The canonical launch article lives at [WEBSITE_URL]/articles/introducing-matemium.

I have spent enough time writing technical animations to recognize a recurring failure mode: the code starts with an idea and ends as choreography.

Move this object. Wait. Shift the camera. Fade that group. Recreate an earlier equation because the original was removed. Adjust six coordinates because one label wrapped. Add another conditional to preserve state across a transition.

None of those operations is inherently wrong. Manim Community Edition is powerful precisely because it gives Python authors detailed control. But when an explanation behaves like a structured document, raw imperative orchestration makes the author manage a large amount of accidental complexity.

Matemium is my attempt to put a compiler layer between the explanation and that orchestration.

It is a free, source-available desktop application built on Manim. Authors write visible Python project files through `CanvasBuilder` and `CanvasScene`. The engine measures content, lays it out, validates identities and actions, compiles a timeline, and produces a Manim scene for local rendering.

This article explains the technical model, what is implemented, and which parts I am deliberately not claiming are finished.

## From scene choreography to a compiler input

The main authoring artifact in Matemium is `scenes.py`. A minimal project looks like normal Python:

```python
from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder


# ---DIV: Explanation---
def part_explanation(builder: CanvasBuilder) -> None:
    builder.add_heading("A structured explanation")
    builder.add_body("State the idea before animating its consequences.")
    builder.add_math(r"a^2 + b^2 = c^2")


# ---DIV: Main scene---
class Explanation(CanvasScene):
    def __init__(self, **kwargs):
        builder = CanvasBuilder(
            title="Explanation",
            canvas_settings=CanvasSettings.for_reels(title="Explanation"),
        )
        part_explanation(builder)
        super().__init__(dsl=builder.build(), **kwargs)
```

`builder.build()` produces a serializable internal representation called `SheetDSL`. That representation is useful to the compiler and tests, but it is not the user-facing language and it is not what an AI is expected to invent over the network. Human and AI edits meet in the same reviewable Python source.

This boundary matters for maintainability. Topic-specific work—simulations, source data, graph layout, chemistry coordinates, or numerical calculations—belongs in project code, usually `helpers.py`. The engine is reserved for abstractions that can survive use across unrelated subjects.

## The infinite tape

The root composition model is an infinite vertical reasoning tape. Ordinary `builder.add_*` calls flow onto it automatically.

Content is placed on an XY plane. The Y axis becomes a document-like scroll direction. As the camera reaches new content, elements are revealed and stored in a registry. They do not need to be recreated simply because the explanation later returns to them.

This makes several common structures easier to express:

- a derivation where earlier equations remain available;
- a definition followed by examples below it;
- a plot that is revisited after a symbolic explanation;
- a long-form sheet exported as PNG or PDF;
- a portrait explanation divided into short segments.

The engine still produces a timeline, not a static webpage screenshot. It compiles lazy reveals, camera movement, focus, transformations, and state changes into a `Manim` scene. The tape is a layout and persistence model for animation.

Portrait is the default production orientation: `CanvasSettings.for_reels()` uses 1080×1920. `CanvasSettings.for_youtube()` targets 1920×1080. A resolution change does not re-author a composition automatically, so both orientations require their own preview and visual review.

## A free 3D world, not a stack of floating pages

A flat tape is useful for reasoning, but some explanations depend on genuine spatial relationships. Matemium therefore has a free 3D world for registered objects, equation-backed surfaces, built-in solids, transforms, lifts, rotations, and camera inspection paths.

It also supports additional tapes. The key design decision is that a tape remains a camera-facing presentation context rather than becoming a physical world object.

When Matemium selects a tape, that tape hides the world and every other tape. Switching tapes replaces the active context. Inspecting a world object opens the world again. The engine uses an opacity curtain around a camera cut rather than visibly interpolating between unrelated camera poses.

Why impose that restriction?

Because analytical content becomes unreadable quickly when several planes, equations, diagrams, and 3D objects share one perspective. The world is good at showing spatial relationships. A tape is good at stopping the action and explaining those relationships clearly. Treating them as separate modes creates a usable grammar for moving between intuition and analysis.

The root tape and the production tape/world path are implemented and exercised. Lower-level world keyframes and relative placement are more experimental; they need preview evidence and are not general layout promises.

## Generic visuals instead of subject APIs

It is tempting to add one compiler primitive per lesson: a quadratic graph helper, then an orbital helper, then a reaction helper. That path does not scale.

Matemium's current general-purpose visual layer centers on three sampled structures:

- `DataPath`: sampled 2D or 3D points for trajectories, routes, contours, and vectors;
- `DataPlot`: named sampled series, axes, and markers;
- `Diagram`: explicit nodes, edges, directions, and labels.

For example:

```python
trajectory_id = builder.add_data_path(
    [[0, 0], [1, 1.4], [2.2, 0.6], [3, 1.8]],
    id="trajectory",
    smooth=True,
    arrow=True,
    color="#5eb3ff",
    stroke_width=5,
)

builder.add_state_transition(
    [
        {
            "target_id": f"{trajectory_id}::path",
            "changes": {
                "stroke_color": "#ffdd66",
                "stroke_width": 7,
            },
        }
    ],
    run_time=0.8,
)
```

The `::path` suffix is a semantic part. Plots expose parts such as `axes`, `series:<id>`, and `marker:<id>`. Diagrams expose `node:<id>`, `edge:<id>`, and edge labels. Actions can address these stable meanings instead of depending on renderer-specific object positions.

`StateTransition` applies synchronized, allowlisted visual property changes. `ElementMorph` sends replacement content or geometry back through the registered build pipeline. Structural validation catches unknown targets, duplicate IDs, malformed data, invalid diagram endpoints, and unsupported transition properties before a full render.

These visuals are currently sampled and staged. Matemium does not yet provide generic timed traversal along any path, a reactive simulation clock, arbitrary surface-relative positioning, or automatic subject-specific layouts.

## The desktop boundary

The local application is intentionally split across three languages:

```text
TypeScript/WebView
       ↓ Tauri invoke and events
Rust shell
       ↓ NDJSON over stdin/stdout
Python sidecar
       ↓
Matemium + Manim render
```

The TypeScript layer owns the project interface, code editor, AI interaction, preview, and render history. Rust owns application filesystem access, workspace management, process lifecycle, and the boundary to native capabilities. The platform-specific Python sidecar imports `scenes.py`, runs project checks, and performs the local render.

TypeScript never imports Python, and Rust does not embed the Manim engine. Each operating system receives a native sidecar built on that platform. The repository has build workflows for Linux, Windows, Apple Silicon macOS, and Intel macOS.

The installers bundle the application and sidecar. They do not bundle FFmpeg, a full LaTeX distribution, local language models, or provider keys. Those rendering prerequisites are an important current setup cost, not a footnote to hide.

## Where AI fits

Matemium is designed so AI can help with real project artifacts: the description, creative passport, tape content, orchestration, `scenes.py`, helpers, diagnostics, and render evidence.

The existing desktop has project-aware chat and agent paths. Proposed code still enters the local project and goes through the same checks and rendering path as a manual edit. External AI access is user-owned; Matemium does not resell tokens or maintain a pooled model quota. Optional cloud services do not run Manim or store a cloud render farm.

The target autonomous runtime is more ambitious than the current guarantee. Its specification calls for persistent run state, bounded tools, typed errors, budgets, recovery, resumability, visual evidence, and verifier-controlled completion. The production lifecycle also separates project description, creative decisions, tape content, orchestration, code, render repair, and optional audio paths into durable gates.

That complete standard remains active work. A successful compile does not prove that an equation is correct, a camera move is readable, or a visual explanation communicates what the user intended. Users should review source and actual output.

## Source-available is a deliberate term

Matemium is not open-source. It uses the Matemium Source-Available License.

The license permits specified personal, educational, research, nonprofit, and internal organizational use; inspection and study; private modifications; contribution forks; and contributions to the official project. It restricts redistribution, public derivative builds, commercial exploitation of the software, hosted Matemium services, and competing products without written permission.

User-created lessons, videos, images, scripts, and educational material remain the creator's and may be used commercially. Read the license itself before relying on a specific permission.

## What is implemented—and what needs help

The current codebase includes root-tape authoring, layout, rich text, flex groups, paths, plots, diagrams, semantic state transitions, morphs, focus modes, local checks, full-sheet export, reel cutting, surfaces, solids, registered world objects, camera inspection, additional tapes, explicit tape scrolling, and isolated world/tape switching.

The desktop includes project workspaces, editing, preview/render paths, AI assistance, archive import/export, and native release pipelines. The cross-subject example library is useful engine evidence, but its projects are at different review and final-master stages.

Areas where contribution and outside use can help immediately include:

- clean-machine installation and packaging reports;
- Windows signing and macOS signing/notarization hardening;
- rendering and camera bugs exposed by unfamiliar projects;
- better world-authoring ergonomics and generic visual primitives;
- accessibility, domain review, and final-quality example review;
- agent recovery, visual verification, and evaluation;
- documentation gaps and confusing API names.

## Getting started

1. Read the launch article and current documentation: [WEBSITE_URL]/articles/introducing-matemium and [DOCS_URL].
2. Download the installer for your platform from [DOWNLOAD_URL].
3. Install the platform's FFmpeg and LaTeX prerequisites described in the release notes.
4. Open an example or create a project, run a preview-quality render, and inspect the output.
5. Report installation failures, visual defects, or API friction at [GITHUB_URL].

For engine development from source:

```bash
git clone [GITHUB_URL]
cd matemium
uv sync --python 3.12 --extra dev --frozen
pytest
```

You can see current visual evidence at [DEMO_URL].

I am releasing Matemium now because private polishing has reached diminishing returns. The next useful evidence will come from machines, subjects, and contributors I do not control. If the compiler model interests you, I would rather hear a precise objection or receive a reproducible failure than collect another vague launch compliment.

Canonical article: [WEBSITE_URL]/articles/introducing-matemium
