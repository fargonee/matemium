# Production report — Orbital Mechanics

## Current outcome

- **Visual narrative upgraded:** one high side establishing shot makes a single
  deliberate move to a pole-locked experiment. Zero-speed drop, three widening
  impact arcs, circular orbit, bound ellipse, and escape replay from one launch
  point with no observational orbiting during the experiment.
- **Project-local visual:** `OrbitalWorld` builds a volumetric Earth, procedural
  paths, enlarged satellite and locator, launch marker, constant inward vector,
  and speed-scaled tangential vector.
- **Authoring check:** strict DSL validation passes with 33 timeline items and no
  errors or warnings.
- **Runtime proof:** a complete 960×540, 15 fps preview render finished at
  63.730 seconds with 65 animations.
- **Visual review:** finished frames at 2, 6, 12, 16, 20, 24, 29, 36, 42, 47,
  53, 55, 57, 59, and 62 seconds were inspected. Satellite silhouette, force
  vectors, impact arcs, circular path, bound ellipse, escape path, recap tape,
  and closing synthesis are visible, framed, and free of overlap or clipping.
- **Publication status:** the engine/project preview gate passes. Independent
  human showcase acceptance and the 1920×1080 website master remain pending.

## General engine repairs

The project exposed and justified reusable repairs to world-object IDs and
bookkeeping, persistent world construction, complete tape ownership,
world/tape opacity-only curtain switching with camera cuts, stale replacement
cleanup, flex-first tape activation, hidden morph behavior, explicit
`TapeScroll`, and world transform application.
Regression coverage is in `tests/test_3d_space.py`.

No orbital rule or project-specific scene branch was added to engine core.

## Scientific checks retained

- Circular speed at 400 km: `7.672598648 km/s`.
- Gravitational acceleration at 400 km: `8.694250483 m/s²`.
- Fraction of standard surface gravity: `0.8865668`.
- Slow trial intersects the normalized Earth.
- Circular trial preserves radius within integration tolerance.
- `1.08×` remains bound and is shown as an ellipse.
- Escape trial has positive normalized specific orbital energy.

See `domain-review.md` for assumptions and sources.

## Invalidated evidence

The former 48.864-second preview predates the speed-ladder narrative. It remains
historical evidence only and must not be cited as acceptance of this version.

## Next publication gate

Obtain independent human composition and physics sign-off, then render the
final 1920×1080 mute master.
