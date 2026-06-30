# Matemium — Engine

Layout-to-animation compiler for infinite scrollable math sheets on Manim.

**Note (Phase 10 complete):** Canonical model is the unified infinite 3D space (XZ/Y up) with `TapeObject` as the special 2D sheet carrier. Full compat for legacy sheet authoring. See:

- `3D-model.md` (audit + terminology + diagrams)
- `../architecture.md` (updated paradigm section)
- The implementation plan in the sibling `math-preview/` worktree

| Doc | Contents |
|-----|----------|
| [`USAGE.md`](USAGE.md) | Authoring guide — `CanvasBuilder` API; desktop AI chat reference |
| [`../desktop-architecture.md`](../desktop-architecture.md) | Desktop product — editor, AI chat, section fences |
| [`../README.md`](../README.md) | Project overview, quick start, built videos |
| [`../architecture.md`](../architecture.md) | Design spec and abstraction rules |
| [`../project-spec.md`](../project-spec.md) | Feature status and abstraction audit |
| [`3D-model.md`](3D-model.md) | Emerging 3D world model, current sheet assumptions audit |

Render: `../matemium.sh demo` from the repo root.