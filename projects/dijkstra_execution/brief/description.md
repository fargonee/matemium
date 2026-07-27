# What Really Happens During Dijkstra’s Algorithm

## Project identity

- **Subject:** Computer Science
- **Project slug:** `dijkstra_execution`
- **Status:** Landscape flagship preview accepted; final master and independent CS sign-off pending
- **Central question:** How does a computer discover the shortest path without trying every complete route?
- **Primary audience:** Beginning algorithms and data-structures learners
- **Target format:** 16:9 flagship master, approximately 50–70 seconds

## Purpose

This project exposes algorithmic state rather than merely animating a final
path. The graph, tentative-distance/predecessor panel, logical frontier,
essential pseudocode rule, and current event change together as one registered
execution board.

The example should demonstrate Matemium’s ability to explain a process whose meaning lives in changing state.

## Learning outcomes

The viewer should understand:

- what a tentative distance represents;
- why the smallest unsettled distance is selected next;
- what edge relaxation changes;
- when a node’s shortest distance becomes final;
- how predecessor links reconstruct the route;
- why non-negative edge weights matter.

## Narrative arc

1. **The challenge:** Present a small weighted network and ask for the cheapest route from start to destination.
2. **Initialize state:** Set the source to zero, all other distances to infinity, and populate the queue.
3. **Choose:** Highlight the smallest unsettled node simultaneously in graph, queue, and pseudocode.
4. **Relax:** Inspect outgoing edges one by one; animate candidate arithmetic beside the corresponding table cell.
5. **Update or reject:** Show why some candidates improve a distance and others do not.
6. **Repeat:** Accelerate through later iterations while retaining enough state for comprehension.
7. **Reconstruct:** Follow predecessor pointers backward, then reveal the final path forward.
8. **Failure boundary:** Briefly show why a negative edge invalidates the greedy certainty.
9. **Synthesis:** Summarize the invariant: the next settled node cannot later receive a cheaper non-negative route.

## Visual and motion direction

- Use a graph small enough to read completely; the accepted example uses six
  nodes and nine undirected weighted edges.
- Assign fixed spatial positions; nodes must not drift while state changes.
- Use distinct states for unseen, queued, current, settled, and final-path nodes.
- Keep one pseudocode line active at a time.
- Morph the registered board between verified post-event snapshots so every
  changed value has an accompanying action line.
- Provide a persistent legend and avoid edge-label collisions.

## Matemium capabilities this project must demonstrate

- graph and network layout;
- execution traces and discrete state transitions;
- synchronized pseudocode, queue, table, and diagram;
- conditional highlighting for accepted and rejected updates;
- path reconstruction and edge emphasis;
- controlled pacing that can accelerate repeated operations;
- data-driven generation from a graph definition and event trace.

## Required source and assets

- Store the graph in a compact deterministic structure.
- Generate the execution trace from a real implementation or verify it against one.
- Separate algorithm state from rendering helpers.
- Require no external images, fonts, services, or network access.

## Scope boundaries

- Do not use a graph so large that the algorithm becomes unreadable.
- Do not silently reorder equal-priority elements; document the tie-breaking rule.
- Do not describe Dijkstra as valid for negative edges.
- Do not hide the priority queue or replace the algorithm with a vague expanding glow.
- Avoid excessive code; only the essential pseudocode should remain visible.

## Acceptance criteria

- Every displayed distance, predecessor, and queue state matches the verified trace.
- The audience can identify one complete relaxation cycle.
- Accepted and rejected updates are visually distinct.
- The final reconstructed route and cost are correct.
- A learner can edit the graph data and regenerate the animation without rewriting scene structure.
- The result is strong enough to serve as the primary computer-science example in the app and website.
