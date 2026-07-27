# Authoring feedback: clean-water system

> **Historical evidence:** Recorded against the pre-mutation engine. The current
> engine now provides sampled paths/plots, semantic diagrams, addressable parts,
> state transitions, and morphs. These address part of the process-flow gap,
> but this scene has not been reauthored, engineering-reviewed, or visually
> accepted.

## Current pass

- Eight distinct treatment/distribution stages, material distinctions, a monitoring disturbance, wastewater
  boundary, and safety caveat are represented as structured data.
- The DSL validates cleanly and requires no external assets.

## What the current engine could express

Process-stage cards, comparisons, explanatory text, and ordered reveal work.

## What prevented flagship-quality execution

- Process and infrastructure diagrams need general nodes, ports, routed pipes/connectors, and flow direction.
- Particles need data-driven instancing, motion along paths, filtering/removal, and state changes.
- Overview-to-detail transitions need nested coordinate spaces and reliable semantic camera framing.
- Sensor values and operational responses need shared state/event binding.
- Large networks need viewport-aware routing and labels.

The general abstractions are port graphs, path-following instances, nested scenes, reactive state, and
semantic camera targets—not a water-treatment-specific pipeline.

## Evidence level

Importable and structurally valid; treatment wording is educational, not operational guidance. Spatial
system, particle flow, monitoring synchronization, domain review, and production acceptance remain unmet.
