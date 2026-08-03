# 3D World and Tape Contexts

**Implementation audit: 2026-07-30**

This document maps the presentation model in
[`../3D-WORLD-DESCRIPTION.md`](../3D-WORLD-DESCRIPTION.md) to the current
engine.

## Runtime model

```text
SheetDSL timeline
├── free-world objects
│   ├── WorldObject / CanvasElement
│   ├── WorldTransform
│   └── cinematic camera + semantic actions
└── tapes
    ├── root TapeObject
    ├── additional TapeObjects
    ├── per-tape local LayoutEngine
    └── one camera-facing foreground context
```

Tapes and free-world objects share timeline ordering and stable IDs. They do
not share physical coordinates or remain visible together.

## Source mapping

| Module | Responsibility |
| --- | --- |
| `dsl.py` | `WorldObject`, `WorldTransform`, `TapeObject`, `TapeScroll`, camera and action records |
| `builder.py` | World-object placement; tape creation and local authoring scopes |
| `layout.py` / `measure.py` | Tape-local measurement and layout |
| `scene.py` | Registry construction, timeline execution, curtain context switches |
| `camera.py` | Free-world observation and local tape scrolling |
| `registry.py` | Stable ID to live mobject mapping |
| `tape_export.py` | Isolated static export of one tape |

## Tape ownership

`CanvasScene` records every element ID from the root tape and additional tapes
in `_tape_content_ids`, with `_element_tape_map` storing its owner. This
classification drives all context changes:

- `_get_context_switch_animations(tape)` keeps only that tape;
- `_get_world_context_animations()` hides every tape-owned mobject and restores
  non-tape/free-world mobjects;
- `_enter_world_context()` performs the tape-to-world transition and resets
  observation state.

The distinction must be based on ownership, not on current visibility. A
previous implementation restored a generic “dimmed objects” set and therefore
reintroduced every old tape into later world shots.

## Transition triggers

| Timeline event | Resulting context |
| --- | --- |
| First reveal from tape A | tape A |
| Reveal from tape B while A is active | tape B |
| `TapeScroll(tape_id="B")` | tape B at requested local Y |
| `CameraInspect` on world object | free world |
| world `CameraKeyframe` / `observe_object` | free world |
| hidden world `ElementMorph` | state changes without leaking through active tape |

## World-object lifecycle

Free-world objects are built before the timeline so camera inspection and
semantic actions may target them immediately. `add_object(..., id=...)`
preserves author-selected IDs. `ElementMorph` replaces the registry and
`_world_objects` entries so later actions target the newest compiled geometry.

If a world object is morphed while a tape is active, the target is compiled and
registered without being added to the visible scene. Opening the curtain
reveals the updated world state.

## Tape lifecycle

Tape content remains lazy. On first reveal the engine:

1. selects the owning tape;
2. hides the world and other tape content;
3. resets to an orthographic face-on camera;
4. builds and reveals the element at its local position;
5. scrolls locally for later elements when required.

`TapeObject.get_surface_info()` reports `presentation_mode="camera_facing"`.
`CanvasBuilder.add_tape()` rejects physical pose arguments.

## Compatibility

- The root tape is created automatically.
- `CameraMove` remains root-tape scrolling compatibility sugar.
- `TapeScroll` is a real serialized DSL target.
- `dim_others` and `dim_opacity` remain accepted in `scroll_tape()` for older
  project data, but curtain isolation is mandatory.
- Tape static export remains independent of the live world camera.

## Current limits

- no physical tape transforms or simultaneous visible tapes;
- low-level world keyframes and relative placement still need project preview
  evidence;
- generic sampled paths do not yet have shared simulation clocks;
- preview must still be checked against final rendering for camera timing and
  complex volumetric geometry.

These limits are architectural boundaries. New projects should expose missing
general capabilities through reusable object/action contracts rather than
adding lesson-specific conditionals to `scene.py`.
