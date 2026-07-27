# Domain review — Dijkstra Execution

**Review date:** 2026-07-27  
**Reviewer:** AI source-and-execution review; independent computer-science
review still recommended before public sign-off.

## Claims checked

1. Dijkstra's method repeatedly selects a minimum tentative-distance vertex
   and relaxes adjacent edges.
2. Settled distances are final under the non-negative edge-weight assumption.
3. Predecessor links recover a shortest route.
4. A negative edge can invalidate the greedy finality argument.
5. The displayed route from A to F has cost 13.

## Evidence

- NIST Dictionary of Algorithms and Data Structures, “Dijkstra's algorithm”:
  https://xlinux.nist.gov/dads/HTML/dijkstraalgo.html
- E. W. Dijkstra, “A note on two problems in connexion with graphs,”
  *Numerische Mathematik* 1 (1959), 269–271:
  https://doi.org/10.1007/BF01386390

## Deterministic checks

- The heap-based run emits 25 post-event snapshots.
- Final distances are `A=0`, `C=2`, `B=3`, `D=8`, `E=10`, `F=13`.
- Final predecessors are `C←A`, `B←C`, `D←B`, `E←D`, `F←E`.
- Reconstruction returns `A,C,B,D,E,F`; edge weights sum to 13.
- Settled order is `A,C,B,D,E,F`.
- The negative-edge example has direct `S→A=2` but
  `S→B→A=5+(−4)=1`.

## Assumptions and simplifications

- The main graph is undirected; each stored adjacency is symmetric.
- Alphabetical node names provide deterministic tie-breaking.
- The visible frontier shows one current best entry per unsettled node rather
  than stale entries retained by the heap implementation.
- The scene explains correctness intuition, not a formal proof or complexity
  analysis.

## Unresolved review items

- Obtain independent algorithms review before labeling the final master
  “domain approved.”
- The preview is not the final 1920×1080 website master.
