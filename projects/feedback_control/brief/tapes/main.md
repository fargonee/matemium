# Visible content — Feedback Control

## C00 — Disturbance

- Target remains 25 m/s while an uphill load changes.
- A fixed command cannot react in open loop.

## C01 — Close the loop

- Target → compare → PI control → actuator → car → sensor → feedback.
- Trace one signal cycle and define `e(t)=r(t)−y(t)`.

## C02 — One correction

- Show target, measured speed, error, and controller command at 4.5 s.
- Clarify that feedback changes input rather than removing the disturbance.

## C03 — Recovery

- Show target, hill start, and balanced response on one time axis.

## C04 — Tuning

- Compare slow, balanced, aggressive, and open-loop responses on identical axes.
- State the PI control law.

## C05 — Synthesis

- Measure → compare → correct → repeat.
