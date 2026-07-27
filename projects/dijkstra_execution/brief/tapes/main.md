# Visible content — Dijkstra Execution

## C00 — Hook

- “DIJKSTRA / SHORTEST PATH AS CHANGING STATE”
- Ask how a route can become certain before every complete route is tried.
- Introduce the fixed graph and registered execution board.

## C01 — One complete cycle

- Choose A as the minimum tentative node.
- Relax A→B and A→C.
- Choose C and show both an accepted improvement and a rejected candidate.
- Resolve the contrast as two explicit verdict lines.

## C02 — Repeat

- Explain tentative, settled, and current colors.
- Advance selected verified snapshots through A, C, B, D, E, and F.
- Show the complete settled order.

## C03 — Reconstruct

- Highlight predecessor edges as the final route.
- State `A → C → B → D → E → F`, cost 13.

## C04 — Validity boundary

- Show `S→A=2`, `S→B=5`, and `B→A=−4`.
- Explain that A can appear final at 2 even though the later route costs 1.

## C05 — Synthesis

- State the invariant: smallest tentative distance plus non-negative remaining
  edges means the node cannot improve later.
