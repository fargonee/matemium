# Orchestration — Dijkstra Execution

## Format and visual system

- Landscape 16:9 execution dashboard.
- Fixed node positions keep graph-reading effort low.
- Blue means tentative/frontier, gold means current, mint means settled, green
  means recovered path, and red marks a rejected relaxation or invalid edge.
- Every graph node includes its current tentative distance.
- The right panel shows distance, predecessor, logical frontier, and active
  pseudocode line; the bottom action card explains the current event.

## Beat choreography

### C00 — Initialize

Create the full registered board from the first generated trace event.

### C01 — Complete relaxation cycle

Morph the same board through settle and relax snapshots. Pause on explicit
green UPDATE and red KEEP verdicts.

### C02 — Accelerated frontier

Use selected event snapshots to preserve causal legibility while advancing the
remaining settled order.

### C03 — Route recovery

Morph the final board to a path-colored target, then emphasize each semantic
path edge in order. Follow with the route/cost equation.

### C04 — Counterexample

Use a separate directed diagram for the negative-edge boundary so the failure
claim is supported by visible arithmetic.

### C05 — Invariant

Reduce the dashboard to one verbal rule and one isolated mathematical
statement.

## Implementation notes

- All execution content derives from `dijkstra_trace()`.
- The displayed frontier excludes stale heap entries and represents the
  logical current best entry for each unsettled node.
- The board is a general semantic `Diagram`; no algorithm-specific engine
  primitive is used.
