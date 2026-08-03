# Authoring feedback — SN2 Reaction flagship reauthoring

## Outcome

The project is no longer a sequence of explanatory slides around a molecule. It
is one continuous, project-local 3D reaction world observed in several ways,
with one short tape reserved for the final synthesis.

- Conventional, persistent atom identities are introduced in the world: C*, O,
  H, and Br.
- A locked side view establishes the C—Br axis, backside and leaving-group
  sides, the attack arrow, and the approximately 180° approach before reaction
  progress begins.
- Dashed, labelled C—O and C—Br partial bonds change together through a frozen
  transition-state beat.
- A fixed reference plane and persistent substituent labels separate Walden
  inversion from camera rotation; reactant and product are then compared side
  by side under the same camera.
- The energy curve and molecule are generated from the same `progress` value.
  Its marker reaches the labelled maximum with the transition-state geometry.
- Mobile copy is limited to short, high-contrast labels and one concise final
  statement.

## Engine boundary

No engine behavior changed. `SN2ReactionWorld` remains an experimental,
project-local registered object composed from existing Manim and Matemium
primitives. It demonstrates a serious authoring technique, not a generic
molecular-dynamics or reaction-clock feature.

## Evidence

- Strict DSL validation: 23 timeline items, one root world, one closing tape.
- Focused flagship tests, Python compilation, and Ruff checks pass.
- Production master:
  `outputs/sn2_reaction/media/videos/1920p30/SN2ReactionFlagship1080p30.mp4`.
- Master format: 1080×1920 portrait, 30 fps, H.264, approximately 29.4 seconds,
  mute by design.
- Full-resolution frames were inspected for atom identification, alignment,
  transition-state bonds, energy synchronization, inversion comparison, and
  final copy. A clipped edge label found during inspection was shortened to
  `LG SIDE` and the master was regenerated.

## Honest limitations

- Geometry and energy are a deterministic authored teaching model, not a
  quantum-chemical calculation or molecular-dynamics simulation.
- The energy curve is qualitative and illustrative, not a universal energy
  profile for all SN2 reactions.
- Independent organic-chemistry sign-off is still pending.

## Readiness

Production master rendered and visually inspected; suitable as a Matemium
flagship candidate. It is not labelled independently domain-approved.
