# Video projects

Each subfolder here is **one video** (or series). The engine code lives in `canvas/` — you only edit files here.

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

## New project

1. `matemium new quadratic_factoring`
2. Edit `projects/quadratic_factoring/scenes.py`
3. `matemium render quadratic_factoring`

One file, one scene class extending `CanvasScene`, build content with `CanvasBuilder`. See `canvas/USAGE.md`.

## 3D World + Tape Features (newest authoring)

```python
tape1 = b.add_tape('notes')
