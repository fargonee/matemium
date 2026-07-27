# Production report — Orbital Mechanics

## Outcome

- **Project behavior completed:** Seven-beat mute explanation covering gravity
  at low orbit, controlled launch trials, regime comparison, local vectors,
  force balance, circular speed, and synthesis.
- **Engine behavior changed:** None during this flagship reauthoring.
- **Project-local helpers added:** SI constants, normalized RK4 two-body
  integration, sampled trajectories, semantic diagram data, and stable visual
  identities.
- **Authoring check:** `check_project` passed with 45 authored timeline items,
  no errors, and no warnings.
- **Accepted preview:** 960×540, 15 fps, landscape, 54.798047 seconds,
  2,170,972 bytes, and 60 rendered animations.
- **Mute verification:** `ffprobe` reported one H.264 video stream and no audio
  stream.

## Visual repair record

1. The first contact sheet exposed trajectory content beyond the safe frame and
   a vector-text collision.
2. The first repair reduced plot/diagram footprints and separated vector copy.
3. Full-resolution sampling then exposed rich-text boundary collapse, a
   transition-state vector label that exceeded its node, and a force-balance
   formula larger than its declared layout box.
4. The next repair replaced fragile mixed-run cards, simplified the vector node
   label, and matched equation size to layout.
5. The final hold still revealed two touching synthesis cards. They were
   replaced with one centered verbal equation.
6. The accepted contact sheet and representative full-size frames show the
   opening, gravity correction, three launch outcomes, comparison plot, vector
   freeze frame, equations, and closing statement legibly. Camera travel may
   crop previous stations while moving to the next focal item; active content
   resolves fully inside the frame.

## Scientific checks

- Circular speed at 400 km: `7.672598648 km/s`.
- Gravitational acceleration at 400 km: `8.694250483 m/s²`.
- Fraction of standard surface gravity: `0.8865668`.
- Slow trial intersects the normalized Earth.
- Circular trial preserves its radius within integration tolerance.
- Escape trial has positive normalized specific orbital energy.
- Source-and-calculation review is recorded in `brief/domain-review.md`;
  independent expert sign-off remains pending.

## Honest readiness

The authoring-stage preview is accepted and the project is a bundled flagship
candidate. Final public delivery still requires a visually inspected
1920×1080 master and independent physics sign-off. Continuous moving-body,
path-history, and vector synchronization remains a future general engine
capability; this project uses honest staged paths and a freeze-frame diagram.
