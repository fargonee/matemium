# Orchestration — Orbital Mechanics

## Format and visual system

- Landscape 16:9 master on a dark navy editorial canvas.
- Earth blue is reserved for the body and curvature reference.
- Coral identifies re-entry and inward acceleration.
- Cyan identifies circular orbit.
- Gold identifies tangent velocity and escape.
- The scene uses the automatic root tape; camera travel connects seven
  conceptual stations.

## Beat choreography

### P00 — Hook

Build the apparent contradiction typographically, then reveal three small
concept cards. The hook is deliberately quiet: no decorative star field or
irrelevant spacecraft footage.

### P01 — Gravity

Lead with the 400 km reference altitude and compute both local acceleration and
its fraction of standard surface gravity. Keep numbers subordinate to the
misconception correction.

### P02 — Launch trials

Register one generic data plot under a stable ID and morph its sampled trajectory
through re-entry, circular, and escape trials. Preserve launch point, Earth, axes,
and scale. Pair each state with a short consequence card.

### P03 — Regime comparison

Show all three trajectories together. Use semantic series IDs and state
transitions to isolate one result at a time without rebuilding the coordinate
system.

### P04 — Local vectors

Switch from global paths to a semantic diagram. Emphasize the tangent velocity
edge, then the inward acceleration edge. Text appears after each visual focus.
This is a freeze-frame explanation; it does not claim unsupported reactive
binding to a continuously moving satellite.

### P05 — Equation

Introduce force balance only after the inward direction and curved motion have
visual referents. Isolate the circular-speed law, then provide the computed
400 km value.

### P06 — Finale

Resolve the opening puzzle with `FALLING + MISSING`, followed by three compact
cards that preserve the established visual identities.

## Motion and implementation notes

- Trajectories come from a deterministic normalized RK4 two-body integration.
- Staged generic-element morphs preserve visual identity across trials.
- Semantic state transitions provide series- and edge-level emphasis.
- The normalized plot exaggerates low-orbit altitude so different paths remain
  readable at website scale; this is disclosed on screen.
- The engine currently has no general reactive vector/path clock, so the scene
  honestly uses an inspectable freeze frame rather than faking continuous
  synchronization.
