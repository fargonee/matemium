# Authoring feedback — Supply Shock

## Current evidence

- `DataPlot` renders arbitrary demand/supply curves, equilibrium markers, and
  aligned scenario paths from transparent sampled data.
- `ElementMorph` changes the baseline market plot into the shocked state.
- Semantic `StateTransition` targets the shifted supply series and equilibrium
  marker.
- `Diagram` discloses both the causal sequence and the model boundary.
- `check_project` passes with 33 authored timeline items and no diagnostics.

## Engine changes required

None. The current general plotting, diagrams, semantic addressing, morphs,
state transitions, math, layout, root-tape travel, and focus methods cover the
project without economics-specific engine behavior.

## Authoring and visual findings

- Directed edges with large arrowheads can obscure short horizontal causal
  nodes. An ordered semantic node row plus a separate text arrow chain is more
  robust at preview resolution.
- A long Math expression containing both transformation and equilibrium result
  collided. Two independently laid-out elements solved it.
- Diagram geometry must be reviewed in rendered screen coordinates; a
  structurally valid topology can still exceed the visual safe area.
- Rich-run arrow chains were less stable than one plain, wrapped synthesis
  sentence.

## Honest remaining limitations

- Equilibrium markers are supplied from the same transparent model, but the
  engine does not solve curve intersections automatically.
- Curves, paths, and views are staged rather than bound to a continuous shared
  market-state clock.
- Scenario paths are illustrative and the model omits substantial economic
  mechanisms.
- Preview acceptance does not replace a final 1920×1080 render or independent
  economics review.

## Generalizable maturity conclusion

The engine can author a disciplined causal-model explanation with arbitrary
plots, semantic emphasis, transforms, scenario comparison, and explicit
assumptions. General computed bindings and shared-clock state remain useful
future capabilities, but should be designed across several domains rather than
as supply-and-demand special cases.
