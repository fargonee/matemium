# Free-World and Tape-Curtain Implementation Plan

**Reconciled with the current engine: 2026-07-30**

The earlier plan treated tapes as transformed planes inside the 3D world. That
model is superseded. The supported design has a persistent free 3D world and
isolated camera-facing tapes.

## Implemented foundation

- [x] `WorldTransform`, `WorldObject`, stable IDs, and registered object kinds
- [x] persistent free-world construction before timeline execution
- [x] cinematic inspection paths
- [x] semantic-part state transitions
- [x] stable-ID `ElementMorph`
- [x] root and additional `TapeObject` local layouts
- [x] automatic world → tape and tape → tape switching
- [x] tape → world restoration that excludes all tape-owned content
- [x] serialized `TapeScroll` and `scroll_tape()` authoring sugar
- [x] isolated per-tape static export
- [x] orbital flagship runtime proof

## Architecture boundary

```text
Free world                    Selected tape
-----------                   -------------
3D transforms                 local 2D layout
perspective camera            orthographic face-on camera
registered objects            text/math/flex/embedded solids
semantic actions              lazy reveal/local scroll

          one visible context at a time
```

Physical tape poses, tape fly-arounds, and simultaneous visible tapes are not
part of the current contract.

## Near-term work

### 1. Runtime visibility

- [ ] Centralize visible-context state rather than inferring it from membership
  in `scene.mobjects`.
- [ ] Ensure every action type can update a hidden world object without adding
  it to an active tape shot.
- [ ] Add a minimal world → tape A → tape B → world render fixture.

### 2. Preview parity

- [ ] Emit active presentation context and tape ownership in preview data.
- [ ] Make the desktop preview hide the same ID sets as `CanvasScene`.
- [ ] Compare representative transition frames, not every frame.

### 3. Transition styling

- [ ] Add reusable fade/curtain timing parameters.
- [ ] Preserve hard isolation regardless of visual transition style.
- [ ] Keep camera reset and content transition in one deterministic action.

### 4. World authoring

- [ ] Evaluate how relative placement and named anchors should mature for free
  objects.
- [ ] Evaluate reusable traversal actions for sampled paths and poses.
- [ ] Validate low-level world/tape target IDs before runtime.

The first two items are open design questions, not an accepted implementation
plan. Real projects are evidence and test cases; they must not produce
subject-specific engine contracts. Candidate directions, alternatives, and
decision criteria are recorded in
[`SPATIAL_AUTHORING_OPEN_QUESTIONS.md`](SPATIAL_AUTHORING_OPEN_QUESTIONS.md).

### 5. Packaging

- [ ] Exercise registered project-local kinds in frozen sidecars.
- [ ] Verify fonts, LaTeX, FFmpeg, and renderer behavior on each desktop target.
- [ ] Keep bundled projects source-only; do not ship rendered videos.

## Verification policy

For every general engine repair:

1. prove the defect with a focused test or reproducible project action;
2. implement the smallest reusable contract;
3. run structural checks and relevant unit tests;
4. execute the complete project timeline at economical settings;
5. inspect only representative frames/transitions needed for visual evidence;
6. keep domain-specific calculations in project helpers.

## Acceptance

The implementation is mature when:

- tape content is always upright and readable;
- the world never leaks behind a tape;
- prior tapes never return during a world shot;
- tape-to-tape switching never stacks content;
- hidden world state changes appear on reopening;
- desktop preview and final render agree on the active context;
- additional flagship projects use the same contracts without engine branches
  keyed to their topics.
