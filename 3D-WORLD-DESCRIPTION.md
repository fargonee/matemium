# Free 3D World and Tape Presentation Model

**Current contract: 2026-07-30**

Matemium uses two cooperating presentation contexts. They share a timeline and
object registry, but they are intentionally not composited at the same time.

## 1. Free 3D world

The free world is a persistent three-dimensional scene:

- registered objects have stable IDs and `WorldTransform`s;
- project-local object kinds can build reusable compound geometry;
- camera inspection can orbit, dolly, change angle, and follow authored paths;
- state transitions address an object or one of its semantic parts;
- `ElementMorph` can replace a world object while preserving its stable ID.

The world may continue to evolve while hidden behind a tape. When the tape
opens, the current world state is shown.

## 2. Tape presentation

A `TapeObject` is an isolated, camera-facing 2D reasoning canvas. It owns:

- local XY layout and vertical flow;
- CSS-like width, margin, wrapping, and alignment;
- flex rows and columns;
- lazy reveal and local scrolling;
- text, math, plots, diagrams, and small embedded solids;
- a per-tape static document export.

A tape is not a plane positioned or rotated in the 3D world. `add_tape()` does
not accept `position`, `rotation`, or `scale`.

## 3. Curtain transitions

Only one presentation context is visible:

```text
free 3D world ── close tape ──> selected camera-facing tape
selected tape ── replace ─────> another camera-facing tape
selected tape ── open tape ───> free 3D world
```

The selected tape behaves like a curtain placed directly in front of the
camera. Closing it hides all free-world objects and every other tape. Switching
tapes replaces the foreground canvas. Opening it removes all tape content and
restores only free-world objects.

This isolation is a correctness rule, not merely an artistic default. It keeps
text face-on and readable, prevents mirrored/clipped overlays, and prevents
previous tapes from accumulating over a 3D shot.

## 4. Authoring transitions

Tape context can be selected in two ways:

- revealing an element owned by a different tape switches automatically;
- `scroll_tape(tape_id=..., local_y=...)` selects it explicitly.

World context is selected by a world camera action, including
`observe_object()`, `add_camera_keyframe()` with a world target, or
`add_camera_inspect()`.

Example:

```python
b = CanvasBuilder(canvas_settings=CanvasSettings.for_youtube())

analysis = b.add_tape("analysis", frame_width=6.4, frame_height=4.8)
results = b.add_tape("results", frame_width=6.4, frame_height=4.8)

world_id = b.add_object(
    "OrbitalWorld",
    id="orbital_world",
    content=initial_state,
)
b.add_camera_inspect(world_id, path=opening_path, return_to_sheet=False)

analysis.add_heading("Gravity is still strong")
# world -> analysis happens on reveal

b.add_element_morph(world_id, changed_world)
b.add_camera_inspect(world_id, path=close_path, return_to_sheet=False)
# analysis -> world; the hidden morph is now visible

results.add_heading("Only launch speed changed")
# world -> results
```

## 5. Engine invariants

1. Every tape element belongs to exactly one tape.
2. Tape-owned elements are excluded when restoring the free world.
3. Switching tapes hides the prior tape before revealing the next.
4. World objects have stable registry IDs across hidden morphs.
5. Tapes remain local 2D layouts; world transforms apply only to free objects.
6. Topic-specific simulations and geometry stay in project helpers or
   registered object kinds, not in engine-core branches.

## 6. Static export and preview

Static export renders one tape as an isolated document in its natural local
coordinates. It does not reuse the live 3D camera.

Desktop preview and final Manim output should replay the same context sequence:
world, selected tape, selected tape, or world. Simultaneously showing a tape
over undimmed/unhidden world geometry is a preview or runtime defect.

## 7. Deliberate non-goals

The current contract does not include:

- physically posed tapes floating in world space;
- cinematic fly-arounds of tape planes;
- multiple tapes visible simultaneously;
- attaching tapes as faces or panels of 3D assemblies.

Those are different interaction models. They must not be inferred from the
existence of `WorldTransform` or implemented as project-specific exceptions.

## 8. Open spatial-authoring discussion

The current contract does not yet define persistent parent-relative movement,
generic object traversal, surface-relative placement, or geodesic movement.
The flagship Orbit, Feedback Control, SN2 Reaction, and DNA to Protein projects
are being used as evidence for evaluating possible cross-subject abstractions;
the engine is not being adapted to their subject matter.

No candidate design has been accepted or rejected. See
[`SPATIAL_AUTHORING_OPEN_QUESTIONS.md`](SPATIAL_AUTHORING_OPEN_QUESTIONS.md) for
the open question, alternatives, evaluation criteria, and public-launch
communication boundary.
