# Video projects

Each subfolder here is **one visual explanation** (or series). The engine code
lives in `canvas/`; project authoring and subject logic stay here.

## Quick commands

```bash
./matemium demo              # built-in test → outputs/demo/
./matemium demo landscape
./matemium new my_topic      # create projects/my_topic/
./matemium render my_topic   # render → outputs/my_topic/
./matemium list
```

## Layout

```
projects/
  demo/           # built-in test scenes (don't delete)
  my_topic/
    scenes.py     # your CanvasScene classes
    helpers.py    # optional reusable topic helpers
outputs/
  demo/media/     # demo renders (gitignored)
  my_topic/media/ # your renders (gitignored)
```

Desktop workspaces use the same `scenes.py` entrypoint and optional `helpers.py`, plus a first-class project brief:

```
project/
  project.json
  scenes.py
  helpers.py
  brief/
    passport.json
    description.md
    tape.md
    roadmap.json
    narration.md
  assets/
    images/
    video/
    audio/
```

`brief/` is project memory for the UI and AI agent: creative direction, tape plan, roadmap, and narration. It is not engine IR; `scenes.py` still compiles through `CanvasBuilder` into `SheetDSL`.

`CanvasBuilder` creates the root tape automatically. Author ordinary projects
directly with `builder.add_*`; reserve `add_tape()` for an additional spatial
context that will be preview-tested.

## New project

1. `matemium new my_explanation`
2. Edit `projects/my_explanation/scenes.py` and optional `helpers.py`
3. `matemium render my_explanation`

Use one `scenes.py` entrypoint with one or more `CanvasScene` classes and build
content with `CanvasBuilder`. See [`../AUTHORING_API.md`](../AUTHORING_API.md)
and [`../canvas/USAGE.md`](../canvas/USAGE.md).

## Current flagship library

The source-bundled library spans mathematics, physics, chemistry, computer
science, engineering, economics, biology, history, philosophy, language
learning, and general education. Each project includes:

- `brief/description.md` with its intended outcome and acceptance criteria;
- deterministic `helpers.py` subject data/calculations;
- a source-visible `scenes.py`;
- `AUTHORING_FEEDBACK.md` recording the strongest current evidence.

These sources are engine evidence and reauthoring inputs. SN2 Reaction,
Feedback Control, and DNA to Protein now have visually inspected world-first
cinematic previews; final masters and independent domain sign-off remain
separate gates. See [`flagship_library.md`](flagship_library.md).

Orbit, Feedback Control, SN2 Reaction, and DNA to Protein also expose repeated
manual 3D positioning and movement work. They are evidence for an open
cross-subject spatial-authoring discussion, not templates for subject-specific
engine APIs. No proposed relative-movement, surface, or geodesic API has been
accepted or rejected. See
[`../SPATIAL_AUTHORING_OPEN_QUESTIONS.md`](../SPATIAL_AUTHORING_OPEN_QUESTIONS.md).

## Generic cross-subject authoring

Use:

- `add_data_path()` for sampled trajectories, routes, contours, and vectors;
- `add_data_plot()` for named series and markers;
- `add_diagram()` for named nodes and edges;
- `add_state_transition()` for synchronized changes to whole visuals or
  semantic parts;
- `add_element_morph()` when content or geometry is recompiled.

Keep simulations, source data, domain rules, and specialized layout algorithms
in `helpers.py`.

## Tape and world authoring

```python
tape = builder.add_tape(
    "notes",
    frame_width=6.4,
    frame_height=4.8,
)
tape.add_heading("Supporting notes")
tape.add_body("This content has its own local tape layout.")
builder.scroll_tape(tape_id="notes", local_y=0.0)

cube_id = builder.add_object(
    "Solid3D",
    content={"shape": "cube"},
    position=(4, 1, 2),
)
builder.observe_object(cube_id)
```

The root tape exists automatically. Additional tapes are separate local 2D
layout contexts presented face-on, one at a time. A selected tape hides the
free world and every other tape; observing a free object opens it.
`scroll_tape()` is an explicit serialized selector. The orbital flagship is a
complete multi-tape curtain runtime proof; new spatial productions still
require an economical preview.
