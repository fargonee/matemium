# Authoring feedback — SN2 Reaction

## Current evidence

- `Diagram` expresses reactants, a transition state, products, and the steric
  comparison through stable semantic node and edge identities.
- `ElementMorph` preserves registered molecular and plot objects while their
  states change.
- `StateTransition` addresses the nucleophile, leaving bond, energy profile,
  and progress marker without reaching into renderer internals.
- `DataPlot` presents a deterministic one-barrier qualitative energy profile.
- Automatic root-tape camera travel carries the portrait narrative, and
  `CameraFocus(mode="isolate")` closes on the transition-state signature.
- `check_project` passes with 33 authored timeline items and no diagnostics.

## Engine changes required

None. The project uses general diagrams, sampled plots, semantic addressing,
state transitions, element morphs, rich text, math, and camera focus. No
chemistry-specific behavior was added to the engine.

## Authoring and visual findings

- A rich-text newline did not create two independently laid-out title lines.
  Two normal headings were the robust authoring method.
- Overlay focus was inappropriate for the dense molecular panel because it
  visibly duplicated the diagram over nearby copy. Removing that project-level
  treatment produced a clearer result; this was not evidence for a core patch.
- The portable MathTex rate law works without `mhchem`. It is explicitly
  labeled as the standard elementary case because SN2 classification alone
  does not guarantee observed second-order kinetics in every system.

## Honest remaining limitations

- Molecular and energy states are coordinated in three stages, not bound to a
  continuous shared progress clock.
- The molecular view is a stable 2D teaching projection, not a 3D optimized
  structure, orbital calculation, or molecular-dynamics simulation.
- A general target-bound curved-arrow abstraction would be valuable across
  chemistry, algorithms, circuits, and causal diagrams, but this project did
  not justify a chemistry-only implementation.
- Preview acceptance does not replace a final 1080×1920 render or independent
  chemistry sign-off.

## Generalizable maturity conclusion

The current engine can produce a strong microscopic mechanism explanation from
semantic graphs, registered morph targets, and deterministic sampled data.
Future shared-clock and bound-annotation work should be introduced only through
general contracts exercised by several projects.
