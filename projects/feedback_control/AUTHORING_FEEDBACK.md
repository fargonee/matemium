# Authoring feedback — Feedback Control cinematic reauthoring

## Current evidence

- `FeedbackVehicleWorld` is one persistent project-local 3D road, terrain,
  detailed vehicle, disturbance, speed vector, and control-effort vector.
- The world now follows Manim's native `z`-up convention. The former `y`-up
  rail geometry was the root cause of the below-road and edge-on camera views.
- A surfaced two-lane road, shoulders, lane markings, windows, lights,
  camera-facing wheel sidewalls, rotating wheel detail, and roadside target
  sign establish a readable physical scale.
- Disturbance, speed sensor, measured speed, and throttle command use staged
  attached callouts. At most the labels needed by the current causal beat are
  visible.
- World snapshots are generated from the same deterministic teaching model as
  dashboard values and response plots.
- Open- and closed-loop shots reuse the same hill and physical time before the
  balanced controller advances to recovery.
- Seven isolated tapes inspect the premise, two dashboards, causal loop,
  response trace, tuning comparison, and synthesis.
- All comparison curves use identical axes and disturbance time.
- Strict DSL validation passes with 44 timeline items, seven tapes, and one
  free-world object.

## Engine changes required

None. Physical rendering is project-local; the production uses existing world
morphs, camera inspection, tapes, semantic diagrams, and sampled plots.

## Render and visual evidence

- Full economical preview: `outputs/feedback_control/media/videos/270p10/FeedbackControl.mp4`.
- 480×270 landscape, 10 fps, 57.9 seconds, 86 rendered animations. This proved
  the rebuilt world, staged morphs, cameras, tapes, and curtain transitions
  render as one production.
- Final geometry was then inspected in focused 960×540 still renders for the
  disturbance, measurement, correction, side-profile, and three-quarter shots.
- A dedicated depth-order repair separates ground, far volumetric geometry,
  opaque shell, and roadside detail layers. Window glass and door seams no
  longer share or sit inside shell planes; lamps sit beyond the body end faces;
  a thin roadside body skin prevents Cairo from dropping the lower shell.
- The final camera matrix was inspected at theta `-68°`, `-90°`, and the
  authored `-92°` extreme. The body, cabin, windows, two roadside wheels,
  lights, vectors, and complete callout text remain visible. The body also
  survives an additional `-100°` stress shot outside the authored corridor.
- Final principle, causal-loop, and finale tapes were exported at 540 px and
  visually inspected. Headings have real spacing; diagram panels mask
  connectors; edge labels no longer collide with nodes.
- The final wheel-sidewall and label depth refinements were verified with
  focused stills rather than another full render.

## Honest limitations

- Simulation coordination uses explicit shared timestamps, not a continuously
  reactive engine binding.
- The vehicle is a detailed procedural teaching model, not an automotive CAD
  asset; the longitudinal model is not controller-certification evidence.
- Cairo rendering of the low-poly world remains considerably more expensive
  than tape rendering.
- A new full-sequence preview after the final still-level refinements, the
  1920×1080 master, and independent controls sign-off remain pending.

## Readiness

Repaired cinematic candidate with full intermediate render evidence and final
focused visual evidence. Not yet production-ready or independently
domain-approved.
