# Domain review — Orbital Mechanics

**Review date:** 2026-07-30
**Reviewer:** AI source-and-calculation review; independent physics review still
recommended before public scientific sign-off.

## Claims checked

1. A spacecraft in orbit remains under gravitational acceleration and is in
   continuous free fall.
2. At 400 km altitude, gravitational acceleration is about `8.69 m/s²`, or
   about 89% of standard surface gravity.
3. For an ideal circular orbit, gravity supplies the centripetal acceleration,
   giving `v = √(GM/r)`.
4. The corresponding ideal circular speed at 400 km is about `7.67 km/s`.
5. The scene's escape trial has positive specific orbital energy; the label
   “escape” is therefore physically supported in the simplified model.

## Evidence

- NASA Science, “Chapter 3: Gravity & Mechanics”:
  https://science.nasa.gov/learn/basics-of-space-flight/chapter3-4/
- NASA Glenn Research Center, “Free Falling Objects”:
  https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/free-falling-objects/

## Deterministic checks

- Constants: Earth mean radius `6,371,000 m`; Earth standard gravitational
  parameter `3.986004418×10¹⁴ m³/s²`; standard gravity `9.80665 m/s²`.
- `gravity_at_altitude(400 km)` returns `8.694250483 m/s²`.
- `gravity_fraction(400 km)` returns `0.8865668`.
- `circular_speed(400 km)` returns `7.672598648 km/s`.
- The `0.78×` trial intersects the normalized Earth radius.
- The `1.00×` trial maintains normalized radius `1.52` within integration
  tolerance.
- The `1.08×` teaching trial remains below the local `√2` escape threshold and
  therefore forms a bound ellipse rather than an open path.
- The `1.46×` trial exceeds `√2` times local circular speed and has normalized
  specific orbital energy `+0.04328947`.

## Assumptions and simplifications

- The trajectory model is planar and treats Earth as a stationary spherical
  central body.
- Atmospheric drag, Earth rotation, oblateness, third bodies, and relativity
  are omitted.
- Low-orbit altitude is visually exaggerated to `1.52` Earth radii so the
  falling distance and trajectory curvature remain legible.
- “Circular” describes the ideal initial condition in this two-body model.
- “Centripetal force” names the inward net force requirement; it is not an
  additional force alongside gravity.

## Unresolved review items

- Obtain independent physics review before labeling the final-quality master
  “domain approved.”
- The cinematic reauthoring has a complete low-resolution runtime smoke, not
  an accepted visual preview or final 1080p website master.
