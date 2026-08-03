# Orchestration — Orbital Mechanics

## Format and visual system

- Landscape 16:9 master in one continuous spatial world.
- A volumetric Earth and procedural trajectory are the persistent center.
- Four compact camera-facing tapes act as principle, telemetry, experiment,
  and synthesis instruments. Each temporarily hides the world like a curtain.
- Earth blue identifies the body, coral identifies re-entry/inward
  acceleration, cyan identifies circular orbit, and gold identifies tangent
  velocity/escape.

## Camera-led beat choreography

### W00 — Establish the world

Hold a high side view long enough to establish Earth, orbital plane, and
satellite silhouette. Make one measured move to a near-pole view so the orbit
reads as a circle rather than a foreshortened ring.

### T01 — State the puzzle

Close the principle tape over the world. Reveal the title, one-sentence
premise, and a small embedded 3D Earth.

### W02 — Observe the mechanism

Return to the pole-locked central model. Release the satellite first with no
tangential speed, then replay from the same point with progressively more
sideways speed. The attached tangent and inward vectors, impact arcs, and final
closed path make continuous free fall visible without camera movement.

### T03 — Read telemetry

Close the telemetry tape. Quantify gravity at 400 km and introduce circular
speed only after the physical directions have visual referents.

### W04/T04 — Run the controlled experiment

Continue from circular speed to a wider bound ellipse, then exceed escape
speed to open the path. Keep the pole axis fixed and zoom out only as needed to
contain each trajectory. Follow with one compact regime recap tape.

### W05 — Resolve

Return to circular orbit for one final stable pole observation. Finish by
closing the synthesis tape over the world.

## Implementation boundary

- The two-body model and `OrbitalWorld` builder remain project-local.
- World construction, tape curtain switching, camera paths, semantic state
  changes, and object morphing use general engine contracts.
- No downloaded textures, footage, or network resources are required.
