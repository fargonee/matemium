# Matemium — Engine

Layout-to-animation compiler for structured visual explanations on Manim.

**Current contract (2026-07-27):** the automatic root tape provides the mature
2D layout, scroll, lazy-reveal, and focus path. Additional tapes and free 3D
objects exist but remain experimental. `scroll_tape()` is not usable because
the current DSL has no `TapeScroll` target. Arbitrary physical tape transforms
remain an unfinished architecture seam; `add_tape()` rejects position,
rotation, and scale. See the following as design records:

- `3D-model.md` (audit + terminology + diagrams)
- `../architecture.md` (updated paradigm section)
- The implementation plan in the sibling `math-preview/` worktree

| Doc | Contents |
|-----|----------|
| [`USAGE.md`](USAGE.md) | Authoring guide — `CanvasBuilder` API; desktop AI chat reference |
| [`../AUTHORING_API.md`](../AUTHORING_API.md) | Current source-aligned public API and data schemas |
| [`../desktop-architecture.md`](../desktop-architecture.md) | Desktop product — editor, AI chat, section fences |
| [`../README.md`](../README.md) | Project overview, quick start, built videos |
| [`../architecture.md`](../architecture.md) | Design spec and abstraction rules |
| [`../project-spec.md`](../project-spec.md) | Feature status and abstraction audit |
| [`3D-model.md`](3D-model.md) | Emerging 3D world model, current sheet assumptions audit |

### Quick Root-Tape Example

```python
from canvas.builder import CanvasBuilder

b = CanvasBuilder(title="Factor and Check")
b.add_heading("Method")
b.add_body("Factor the expression first.")
b.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")
b.add_heading("Check")
b.add_body("Verify each root in the original equation.")
b.add_math(r"x=2:\;4-10+6=0")
```

The root tape exists automatically and is the recommended authoring path.

### Quick 3D Object Example

```python
from canvas.builder import CanvasBuilder

b = CanvasBuilder(title="3D Object")

b.add_heading("A cube above the reasoning tape")
cube = b.add_object("Solid3D", position=(4, 1, 2), content={"shape": "cube"})
b.observe_object(cube)
```

Free-world objects and their camera observation are experimental. Prefer
`add_solid(id=...)` plus `add_camera_inspect(id, ...)` for production scenes.

Render: `../matemium.sh demo` from the repo root.

### Quick Generic Visual Example

```python
from canvas import CanvasElement
from canvas.builder import CanvasBuilder

b = CanvasBuilder(title="A Stateful Process")
graph = b.add_diagram(
    nodes=[
        {"id": "input", "label": "Input", "position": [-2, 0]},
        {"id": "output", "label": "Output", "position": [2, 0]},
    ],
    edges=[{"id": "flow", "from": "input", "to": "output"}],
    id="process",
)
b.add_state_transition([
    {"target_id": f"{graph}::edge:flow", "changes": {"stroke_width": 7}},
])
```

`DataPath`, `DataPlot`, and `Diagram` use validated sampled data and expose
stable semantic parts. `StateTransition` changes allowlisted properties;
`ElementMorph` recompiles replacement content through the same object registry.
