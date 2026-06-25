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
outputs/
  demo/media/     # demo renders (gitignored)
  my_topic/media/ # your renders (gitignored)
```

## New project

1. `matemium new quadratic_factoring`
2. Edit `projects/quadratic_factoring/scenes.py`
3. `matemium render quadratic_factoring`

One file, one scene class extending `CanvasScene`, build content with `CanvasBuilder`. See `canvas/USAGE.md`.