# Open discussion: native spatial authoring

**Status:** Open — no proposal in this document is accepted or rejected  
**Recorded:** 2026-08-03  
**Scope:** Free-world 3D authoring and engine abstractions  
**Evidence projects:** Orbital Mechanics, Feedback Control, SN2 Reaction, and
DNA to Protein

## Why this is being recorded

The current flagship projects are real production tests of Matemium. They are
not templates that the engine must imitate, and they do not by themselves
justify subject-specific engine APIs. Their role is to expose repeated
authoring work and help determine whether a smaller cross-subject abstraction
belongs in Matemium.

The four projects currently perform substantial spatial work inside
project-local registered object builders:

- Orbital Mechanics samples a physical trajectory and uses a Manim updater to
  interpolate position and recompute tangent and inward vectors.
- Feedback Control computes road height and slope, car pose, and the absolute
  positions of car-attached arrows, sensors, and labels.
- SN2 Reaction computes atom and bond endpoints from reaction progress and
  recompiles the compound world at selected states.
- DNA to Protein constructs stages using explicit curves, shifts, sampled
  positions, and whole-world morphs.

Some of this is correctly project-owned domain logic. The open question is
which repeated spatial mechanics, if any, should become neutral Matemium
authoring and engine capabilities.

## Current boundary

Today Matemium supports top-level `WorldTransform`s, registered object kinds,
stable IDs, semantic parts, absolute position/shift state patches, camera
inspection, and stable-ID `ElementMorph`.

Current relative placement is primarily an authoring-time calculation. It
does not yet establish a durable runtime relationship in which a child follows
a moving or rotating parent. General object traversal also has no shared DSL
action; projects either morph compiled states or implement motion inside their
Manim builders.

This description is an audit of the current implementation, not a decision
that every relationship must become persistent or reactive.

## The open question

How can Matemium make relative placement, relative movement, and movement on
curves or surfaces feel native while keeping the engine small,
renderer-independent, deterministic, and useful across subjects?

The desired outcome is lower authoring complexity. The design must not turn
the engine into a collection of APIs adapted to these four projects.

## Candidate directions under discussion

These directions are alternatives or composable pieces. Listing them does not
select them.

### A. Retained spatial relationships

Objects could retain parent/local-transform and named-anchor references in the
DSL. The runtime would derive world poses through a scene graph. This could
make attachments follow parent motion naturally, but introduces lifecycle,
reparenting, cycle detection, interpolation, and renderer-parity obligations.

### B. Compiled pose paths

Project helpers or reusable geometry libraries could compile domain intent
into sampled, serializable poses containing position and orientation. A
generic traversal action would interpolate those poses. This keeps orbital,
road, reaction, and geodesic calculations outside the renderer, but may be
less expressive for relationships that must remain live during several
independent motions.

### C. Narrow runtime bindings

Lines, arrows, labels, or other dependents could reference object anchors and
resolve their endpoints as targets move. This could remove repeated connector
calculations without introducing a general constraint solver. The correct
scope and serialization model remain undecided.

### D. Surface-aware authoring utilities

Parametric surfaces, height fields, and meshes could expose reusable sampling
utilities for points, tangent frames, normals, and possibly geodesics. These
utilities might live in the engine, in an official authoring library, or in
registered extensions that compile to a smaller engine representation.

"Movement on any surface" is a design goal to investigate, not a current
capability or a promise of exact geodesics for arbitrary geometry.

### E. Incremental improvement of existing primitives

Matemium could first mature current relative placement and add sampled path
traversal without adopting a retained graph or surface system. This has a
smaller implementation cost but may leave authors responsible for orientation,
attachments, and dependent geometry.

## Possible neutral intermediate representation

One candidate—not an accepted design—is a small spatial representation made
of:

- local or world poses;
- optional parent and named-anchor references;
- sampled pose paths;
- a generic path-traversal timeline action;
- narrowly defined anchor-to-anchor bindings.

Domain helpers would continue to calculate physical trajectories, reaction
progress, biological states, and specialized geometry. Surface or geodesic
utilities could compile to sampled poses rather than adding solver logic to
the render timeline.

This candidate must be compared with simpler alternatives before adoption.

## Reliability and maintainability criteria

Any proposal should be evaluated against all of the following:

1. **Cross-project evidence:** the same contract works unchanged in several
   structurally different projects.
2. **No subject branches:** engine behavior does not inspect names such as
   orbit, road, molecule, DNA, car, or reaction.
3. **Serializable and inspectable:** authored motion and relationships survive
   DSL round trips and can be validated before rendering.
4. **Deterministic timing:** playback does not depend on hidden mutable Python
   closures or renderer-specific updater state.
5. **Renderer independence:** a future renderer can interpret the same spatial
   representation.
6. **Stable identity:** semantic targets remain addressable across movement
   and genuine topology changes.
7. **Clear ownership:** domain facts and simulations remain in project helpers
   or extensions; reusable spatial mechanics are candidates for shared code.
8. **Composability:** camera actions, tape/world context switching, hidden
   world updates, and spatial movement interact predictably.
9. **Bounded complexity:** the engine does not become a general physics,
   geometry, or constraint-solving system without demonstrated need.
10. **Migration value:** reauthoring a real project materially reduces manual
    positioning and movement code rather than merely renaming it.

## Evidence and experiments needed before a decision

- Inventory repeated spatial operations in the four evidence projects and at
  least one unrelated 3D fixture.
- Prototype the smallest credible sampled traversal action.
- Compare a compiled-pose approach with a retained parent/local-transform
  approach on Orbit and Feedback Control.
- Test synchronized moving endpoints using SN2 Reaction without adding a
  chemistry-specific engine type.
- Test hierarchy and repeated curve-relative placement using DNA to Protein.
- Add synthetic cases for rotated/scaled parents, nested attachments, moving
  connectors, path orientation, DSL round trips, and hidden-world playback.
- Measure authoring-code reduction, validation quality, preview/final parity,
  and implementation complexity.
- Record rejected alternatives and the evidence for any accepted contract in
  an architecture decision record.

## Explicitly not decided

No decision has been made to add:

- a retained scene graph;
- a `PosePath` or similarly named public type;
- a general constraint solver;
- a built-in molecule, orbit, road, vehicle, or DNA API;
- exact geodesic solvers for arbitrary surfaces;
- reactive runtime evaluation for every object relationship;
- any of the illustrative method names discussed above.

Likewise, none of these possibilities has been rejected. Implementation should
not begin merely because an option appears in this document.

## Public-launch communication boundary

For the current Matemium introduction, describe only implemented behavior as a
product capability. The four flagship projects may be described as production
evidence and as inputs to continuing engine design. Native relative movement,
surface traversal, and arbitrary-surface geodesics should be described only as
open research/design questions unless and until a tested contract is accepted
and implemented.

