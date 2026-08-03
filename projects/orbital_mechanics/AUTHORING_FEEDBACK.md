# Authoring feedback — Orbital Mechanics

## Current evidence

- `OrbitalWorld` is a project-local registered kind: orbital physics and visual
  composition stay outside `canvas/`, while the engine supplies reusable
  building, semantic-part, morph, and observation contracts.
- One persistent volumetric Earth/world survives the complete explanation.
- The circular state carries a continuously orbiting satellite assembly whose
  tangent-velocity and inward-gravity arrows rotate with the body.
- Re-entry, circular, and positive-energy escape use the same deterministic
  RK4 model, launch point, scale, and registered object ID.
- Three analytical tapes act as isolated camera-facing curtains. The world is
  hidden while a tape is read, and the latest world state returns when it opens.
- A small volumetric Earth is genuinely embedded on the principle tape.
- Cinematic camera paths, semantic vector emphasis, and registered-object
  morphs all execute through general engine actions.
- `check_project` passes with 28 timeline items and no errors or warnings.
- A complete 640×360, 4 fps, non-video curtain runtime finished successfully.

## General engine work discovered and completed

The first attempt exposed real cross-project defects rather than missing
orbital special cases:

1. free world objects discarded explicit IDs and never reached placement
   bookkeeping;
2. root world objects were not built before timeline actions targeted them;
3. the generic restore path reintroduced every previously revealed tape into
   later 3D shots;
4. root-tape ownership was not indexed with secondary-tape ownership;
5. hidden world morphs could leak their replacement geometry through a tape;
6. `TapeScroll` was referenced by authoring sugar but absent from the DSL;
7. world-object rotations and scale were not applied at runtime.

These were repaired as general world/tape/camera behaviors and covered by
regression tests. No orbital regime or formula was added to engine core.

## Honest remaining limitations

- Raw DSL deserialization of arbitrary registered world-object payloads remains
  narrower than source-based project execution. Bundled projects execute the
  visible Python source, which is the supported product path.
- The new cinematic production has passed compilation and a complete
  low-resolution runtime smoke, but it has not yet received an accepted visual
  preview or final 1920×1080 render.
- Independent physics sign-off remains a publication gate.

## Maturity conclusion

This project now demonstrates the intended Matemium grammar: a persistent world
is the explanation, while compact tapes temporarily close over the camera to
deliver readable analysis. Further orbital polish belongs in the project-local
registered kind; further engine work must remain reusable beyond this project.
