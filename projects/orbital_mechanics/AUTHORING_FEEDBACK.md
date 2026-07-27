# Authoring feedback — Orbital Mechanics

## Current evidence

- `DataPlot` accepts deterministic sampled paths and markers, so the three
  trajectory regimes are now expressed through the supported high-level DSL.
- `ElementMorph` preserves the registered experiment plot while its trajectory
  changes between trials.
- Semantic series parts and `StateTransition` support reliable path-by-path
  emphasis in the comparison view.
- `Diagram` semantic edges support the local velocity/acceleration freeze frame.
- Automatic root-tape camera travel carries the complete seven-beat sequence.
- The scene validates with 45 authored timeline items and no diagnostics.

## Engine changes required

None. The project used general engine capabilities rather than adding
orbital-mechanics-specific behavior.

## Honest remaining limitations

- There is no general reactive shared-clock abstraction that binds a moving
  body, its sampled path history, and derived vectors continuously.
- The scene therefore uses staged trajectory morphs and an explicitly local
  freeze-frame vector diagram. It does not advertise continuous binding that
  the engine does not provide.
- `DataPlot` includes Cartesian axes by design. A future general-purpose
  world-space sampled-path primitive could offer an axis-free scientific view,
  but it is not required for the current explanation.
- Preview acceptance does not replace a final 1920×1080 render or independent
  domain sign-off.

## Generalizable maturity conclusion

The current engine can produce a strong deterministic physics explanation when
the concept is represented as sampled paths, semantic state changes, and
inspectable diagrams. A future reactive clock/path system should be justified
by several projects—not patched into the engine solely for orbit animation.
