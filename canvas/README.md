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

### Quick Multi-Tape Example

```python
from canvas.builder import CanvasBuilder

b = CanvasBuilder(title="Compare Two Ideas")

method = b.add_tape("method")
method.add_heading("Method")
method.add_body("Factor the expression first.")
method.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")

check = b.add_tape("check")
check.add_heading("Check")
check.add_body("Verify each root in the original equation.")
check.add_math(r"x=2:\;4-10+6=0")

# Returning to method content automatically switches the visible tape context.
method.add_observation("Both roots check out, so the factorization is complete.")
```

No manual drag/drop, stacking, lift, or tape switch animation is needed. When the timeline reveals content from a different tape, `CanvasScene` automatically focuses that tape and hides/dims inactive tape content.

### Quick 3D Object Example

```python
from canvas.builder import CanvasBuilder

b = CanvasBuilder(title="3D Object")

b.add_heading("A cube above the reasoning tape")
b.add_object("Solid3D", id="cube", position=(4, 1, 2), content={"shape": "cube"})
b.observe_object("cube")
b.scroll_tape(local_y=3.0)
```

Render: `../matemium.sh demo` from the repo root.
