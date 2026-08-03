# Tape Curtain and Free-World Observation Work

**Reconciled: 2026-07-30**

This file supersedes the earlier physical/posed-tape plan. Tapes are
camera-facing presentation contexts; only free objects live in world space.

## Non-negotiable model

- One persistent free 3D world.
- One visible tape at a time.
- World → tape closes an isolated foreground curtain.
- Tape → tape replaces the curtain.
- Tape → world opens the curtain and restores only free-world objects.
- Tape layout stays local 2D.
- No `position`, `rotation`, or `scale` on `TapeObject`.

## Completed reconciliation

- [x] `add_tape()` rejects physical pose arguments.
- [x] `TapeObject` serialization contains local settings, not world transforms.
- [x] Root and secondary tape element ownership is indexed by `CanvasScene`.
- [x] Tape selection hides world objects and other tape content.
- [x] World restoration excludes every tape-owned mobject.
- [x] `CameraInspect` and world camera keyframes open the curtain.
- [x] Tape-to-tape switching uses the same isolated transition path.
- [x] Hidden world `ElementMorph` updates registry state without leaking into
  the foreground tape.
- [x] World objects are built before timeline camera/actions target them.
- [x] `add_object(..., id=...)` preserves stable IDs.
- [x] `TapeScroll` is an explicit serializable DSL target.
- [x] `scroll_tape()` selects a tape and local Y.
- [x] Validation rejects `TapeScroll` targets with unknown tape IDs.
- [x] Preview data includes every tape and an element-to-tape ownership map.
- [x] Desktop replay hides the world and other tapes when a tape is active.
- [x] Orbital flagship uses world/tape alternation and multiple tape contexts.
- [x] Source validation, focused engine tests, and a complete low-resolution
  timeline execution pass.

## Remaining preview work

- [ ] Render a normal-quality orbital preview and visually inspect the three
  context transitions at representative timestamps.
- [ ] Add a compact transition fixture covering world → A → B → world for
  screenshot regression testing.
- [ ] Confirm tape export selection for root and secondary tapes in the desktop
  UI.

## General engine follow-ups

- [ ] Make visibility-state handling explicit for every action type, not only
  morphs, so hidden world actions never re-add a target unexpectedly.
- [ ] Define a reusable transition-style record (fade, vertical curtain,
  duration) without weakening context isolation.
- [ ] Expose presentation-context state to preview/diagnostic output.
- [ ] Retire stale demos that still call removed physical tape-pose APIs.

## Acceptance criteria

1. Tape text is upright, face-on, and readable.
2. No free-world object remains visible behind a selected tape.
3. No previous tape reappears when the world opens.
4. Switching tapes never stacks their contents.
5. Hidden world mutations appear only after returning to the world.
6. The same rules hold for projects beyond orbital mechanics.
