# Authoring feedback — Feedback Control

## Current evidence

- `Diagram` expresses the physical disturbance, closed-loop blocks, signal
  directions, and one four-value correction snapshot.
- Semantic edges and `StateTransition` trace measurement, feedback, error,
  command, and actuation through one registered loop.
- `DataPlot` presents deterministic balanced and four-case aligned responses.
- `check_project` passes with 32 authored timeline items and no diagnostics.

## Engine changes required

None. General diagrams, semantic addressing, sampled plots, rich text, math,
root-tape travel, and focus cover the project without control-specific engine
behavior.

## Authoring and visual findings

- Compact node labels work better than placing equations inside block nodes;
  the exact PI equation belongs in a separate Math element.
- Four numeric rich-text cards collided in a flex row at preview resolution.
  A semantic four-node diagram provided reliable fixed widths.
- Plot titles and legends needed explicit clearance from axes. Increasing
  heading and plot margins, while reducing plot footprint, solved the issue.

## Honest remaining limitations

- Physical state, signal values, and plot progress are staged rather than bound
  to one continuous reactive simulation clock.
- The model is a disclosed actuator-lag/longitudinal teaching model, not a
  production automotive controller.
- Preview acceptance does not replace a final 1920×1080 render or independent
  controls-engineering review.

## Generalizable maturity conclusion

The engine can explain causal engineered systems with semantic diagrams,
sampled simulations, and inspectable state emphasis. A shared-clock binding
would be broadly useful, but should be introduced as a general contract across
multiple simulations rather than as cruise-control code.
