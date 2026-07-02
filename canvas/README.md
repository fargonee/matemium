# Matemium — Engine

Layout-to-animation compiler for infinite scrollable math sheets on Manim.

**Note (Clarified model - 2026-07):** The world is one 3D space. `TapeObject` is one special object. By default it is observed like any 3D object (use `observe_object()` or `ObjectAnchor`). `TapeScroll` / `scroll_tape()` activates its internal classic tape behaviors (local scroll + reveal). Legacy sheet authoring continues to work. See:

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

### Quick 3D + Tape Example

```python
from canvas.builder import CanvasBuilder
from canvas.dsl import ObjectAnchor, TapeScroll

b = CanvasBuilder(title="Mixed 3D + Tape")

# Classic tape content (targets root tape by default)
b.add_heading("A Tape in 3D Space")
b.add_body("This content lives inside the tape's local 2D space.")

# Position/rotate the tape as a 3D object
b.set_tape_pose(rotation=(30, 15, 0))

# Free 3D object
b.add_object("Solid3D", id="cube", position=(4, 1, 2), content={"shape": "cube"})

# Normal 3D observation (tape treated as any 3D plane)
b.observe_object("root_tape")

# Enter tape-scroll-mode (classic internal tape scroll/reveal)
b.scroll_tape(local_y=3.0)

# Or use raw keyframes
# b.add_camera_keyframe(target=ObjectAnchor("cube"))
# b.add_camera_keyframe(target=TapeScroll("root_tape", local_y=3.0))
```

Render: `../matemium.sh demo` from the repo root.