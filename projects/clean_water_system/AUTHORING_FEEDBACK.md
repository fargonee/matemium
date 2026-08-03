# Authoring feedback — Clean-water system

## Current evidence

- Eight structured stages form a conventional source-to-tap teaching model.
- Semantic overview and treatment diagrams preserve system components and stage
  identities.
- Sequential state transitions trace all eight stages and four monitoring
  response states.
- Separate challenge cards distinguish particles, microorganisms, and dissolved
  chemicals.
- `check_project` passes with 55 timeline items and no diagnostics.
- One repaired 2207×7814 full-tape PNG was inspected and accepted.

## Engine changes required

None. Semantic diagrams, addressable state, rich text, flex layout, root-tape
travel, and focus cover the project without water-specific engine behavior.

## Authoring and visual findings

- Compact directed connectors terminated over node labels. Connector-free
  semantic nodes plus an explicit numbered path made flow clearer.
- Stage purpose text remains separate from the overview so diagrams do not
  become unreadable miniature process manuals.
- The monitoring sequence avoids turning one sensor value into an automatic
  chemical command.
- Drinking water and wastewater are shown as separate system boundaries.

## Honest remaining limitations

- The treatment train is one conventional surface-water model; real systems
  vary by source, risk, regulation, and infrastructure.
- No concentration, dose, contact time, pressure target, or operating
  instruction is provided.
- The diagram is not a literal plant design or a certification that any water
  is safe.
- Full-tape acceptance does not replace a final mute-video master or independent
  water-treatment review.

## Generalizable maturity conclusion

The engine can explain a large everyday system through semantic overview,
ordered process stages, distinct barrier purposes, monitored response, and
explicit boundaries. Ports, routed connectors, path-following particle
instances, nested scale contexts, and reactive shared state remain valuable
general abstractions, but no project-specific core patch was justified.
