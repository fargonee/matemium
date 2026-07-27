# Why an Orbit Is a Continuous Fall

## Project identity

- **Subject:** Physics
- **Project slug:** `orbital_mechanics`
- **Status:** Flagship reauthoring complete; preview visually accepted; final-quality website master pending
- **Central question:** Why does a satellite keep falling toward Earth without hitting it?
- **Primary audience:** General science learners with an intuitive understanding of velocity and gravity
- **Target format:** 16:9 flagship master, approximately 50–70 seconds; a longer narrated adaptation may follow

## Purpose

This project should replace the common misconception that an orbit is a place where gravity disappears. It must show an orbit as the continuous interaction between inward gravitational acceleration and sideways velocity.

The explanation should progress from an ordinary falling object to a curved trajectory around Earth. Mathematics must sharpen the intuition without displacing it.

## Learning outcomes

The viewer should understand:

- gravity remains substantial in low orbit;
- velocity is tangent to the path while acceleration points inward;
- a projectile travels farther around Earth as horizontal speed increases;
- circular orbit occurs at a specific relationship between radius and speed;
- too little, sufficient, and excessive speed produce qualitatively different trajectories.

## Narrative arc

1. **The misconception:** Place an astronaut and satellite above Earth and ask whether gravity has vanished.
2. **Ordinary fall:** Drop an object vertically and show its velocity growing downward.
3. **Sideways launch:** Give the object horizontal velocity and draw the curved path.
4. **Newton’s mountain:** Increase launch speed through several controlled trials as Earth curves away beneath the object.
5. **Force and velocity:** Freeze a point on the successful orbit and display tangent velocity and inward acceleration vectors.
6. **The governing relationship:** Connect `GMm/r² = mv²/r` to the already understood geometry.
7. **Three outcomes:** Compare re-entry, circular orbit, and escape-like trajectory with the same initial position.
8. **Synthesis:** Return to the opening satellite and state that orbit is falling while continually missing the ground.

## Visual and motion direction

- Use a restrained, physically legible space scene rather than a cinematic star field.
- Keep trajectory, velocity, and acceleration colors consistent.
- Exaggerate Earth curvature only when explicitly identified as a teaching view.
- Display trials from the same launch point so speed is the meaningful changing variable.
- Transition between global orbit view and local vector view without losing spatial orientation.
- Numerical values should be plausible, labeled, and secondary to the conceptual story.

## Matemium capabilities this project must demonstrate

- world-space geometry and curved trajectories;
- vector animation tied to a moving body;
- parameter sweeps and comparable scenarios;
- camera movement across large spatial scales;
- equations connected to physical objects;
- traces, annotations, and freeze-frame inspection;
- optional 3D perspective used only where it improves orbital understanding.

## Required source and assets

- Generate Earth, satellite, vectors, and trajectories procedurally.
- Use a documented simplified two-body model or precomputed deterministic samples.
- Keep physical constants and initial conditions in a clear configuration block.
- No downloaded textures, footage, or network resources may be required.

## Scope boundaries

- Do not attempt a complete treatment of elliptical orbits, perturbations, or relativity.
- Do not call a visibly open trajectory “escape” unless its energy and scale support that claim.
- Do not imply that centripetal force is an additional force beyond gravity.
- Avoid unexplained unit changes or physically arbitrary vector directions.

## Acceptance criteria

- The final scene clearly distinguishes velocity from acceleration.
- At least three launch speeds produce visibly and correctly different outcomes.
- The circular-orbit equation appears only after its components have visual referents.
- Physics claims and numerical labels receive an explicit review.
- The scene has no spatial discontinuities during camera transitions.
- It renders from source alone and can be modified by changing a small set of initial conditions.
- The output is suitable as Matemium’s primary physics showcase.
