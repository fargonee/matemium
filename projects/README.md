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

## 3D World + Tape Features (newest authoring)

```python
b.set_tape_pose(rotation=(25, 10, 0))                    # tilt main tape
tid = b.add_tape("notes", position=(4,1,0), rotation=(5,40,0))
with b.in_object_space(tid):
    b.add_body("side content")

b.add_object("Solid3D", id="cube", position=(2,0,3), ...)

b.observe_object("cube")          # normal 3D view (cinematic)
b.scroll_tape(local_y=4.0)        # tape-scroll mode (classic internal logic)
b.observe_object(tid)             # 3D view of secondary tape
```

Use `observe_object` for normal 3D, `scroll_tape` only when you want internal tape scroll/reveal.

Legacy `add_*` / `CameraMove` on default tape still work 100% unchanged.

See `canvas/USAGE.md` and `canvas/3D-model.md`.