"""Verified state generation for the Dijkstra execution flagship.

The visible execution board is derived from a real heap-based run.  Its
``queue`` label shows the logical frontier (the best known entry for each
unsettled node), not stale heap entries retained as an implementation detail.
Alphabetical node names provide deterministic tie-breaking.
"""

from __future__ import annotations

import heapq
from math import inf

BG = "#07131d"
WHITE = "#f4f8fc"
MUTED = "#617386"
UNSEEN = "#33475b"
FRONTIER = "#4da3ff"
CURRENT = "#ffd166"
SETTLED = "#56d6c2"
PATH = "#82e66f"
ACCEPT = "#5ce1a8"
REJECT = "#ff7b72"
EDGE = "#75889b"
PANEL = "#142434"

GRAPH: dict[str, dict[str, int]] = {
    "A": {"B": 4, "C": 2},
    "B": {"A": 4, "C": 1, "D": 5},
    "C": {"A": 2, "B": 1, "D": 8, "E": 10},
    "D": {"B": 5, "C": 8, "E": 2, "F": 6},
    "E": {"C": 10, "D": 2, "F": 3},
    "F": {"D": 6, "E": 3},
}

POSITIONS = {
    "A": (-5.3, 1.2),
    "B": (-3.55, -0.45),
    "C": (-3.55, 2.35),
    "D": (-1.25, -0.35),
    "E": (-0.85, 2.2),
    "F": (0.9, 0.95),
}


def _frontier(
    distances: dict[str, float],
    settled: set[str],
) -> list[tuple[float, str]]:
    return sorted(
        (distance, node)
        for node, distance in distances.items()
        if node not in settled and distance < inf
    )


def dijkstra_trace(
    source: str = "A",
) -> tuple[list[dict[str, object]], dict[str, float], dict[str, str]]:
    """Run Dijkstra and retain a complete post-event state for authoring."""

    distances = {node: inf for node in GRAPH}
    predecessors: dict[str, str] = {}
    distances[source] = 0
    heap: list[tuple[float, str]] = [(0, source)]
    settled: set[str] = set()
    events: list[dict[str, object]] = [
        {
            "kind": "initialize",
            "node": source,
            "distances": dict(distances),
            "predecessors": dict(predecessors),
            "settled": tuple(),
            "queue": tuple(_frontier(distances, settled)),
            "message": "Initialize · A=0 · others=∞",
        }
    ]

    while heap:
        distance, node = heapq.heappop(heap)
        if node in settled:
            continue
        settled.add(node)
        events.append(
            {
                "kind": "settle",
                "node": node,
                "distance": distance,
                "distances": dict(distances),
                "predecessors": dict(predecessors),
                "settled": tuple(sorted(settled)),
                "queue": tuple(_frontier(distances, settled)),
                "message": f"Choose {node} · minimum {distance:g} · settle {node}",
            }
        )
        for neighbor, weight in sorted(GRAPH[node].items()):
            candidate = distance + weight
            previous = distances[neighbor]
            accepted = candidate < previous
            if accepted:
                distances[neighbor] = candidate
                predecessors[neighbor] = node
                heapq.heappush(heap, (candidate, neighbor))
            old_label = "∞" if previous == inf else f"{previous:g}"
            events.append(
                {
                    "kind": "relax",
                    "node": node,
                    "neighbor": neighbor,
                    "edge": f"{node}→{neighbor}",
                    "candidate": candidate,
                    "previous": previous,
                    "accepted": accepted,
                    "distances": dict(distances),
                    "predecessors": dict(predecessors),
                    "settled": tuple(sorted(settled)),
                    "queue": tuple(_frontier(distances, settled)),
                    "message": (
                        f"{node}→{neighbor}: {distance:g}+{weight}={candidate:g} "
                        f"vs {old_label} — {'UPDATE' if accepted else 'KEEP'}"
                    ),
                }
            )
    return events, distances, predecessors


def reconstruct(predecessors: dict[str, str], target: str) -> list[str]:
    path = [target]
    while path[-1] in predecessors:
        path.append(predecessors[path[-1]])
    return list(reversed(path))


def _node(
    node_id: str,
    label: str,
    position: tuple[float, float],
    *,
    width: float,
    height: float,
    color: str,
    font_size: int = 20,
    shape: str = "rounded",
) -> dict[str, object]:
    return {
        "id": node_id,
        "label": label,
        "position": list(position),
        "shape": shape,
        "width": width,
        "height": height,
        "color": color,
        "fill_color": color,
        "fill_opacity": 0.24,
        "font_size": font_size,
    }


def _unique_edges() -> list[tuple[str, str, int]]:
    return [
        (left, right, weight)
        for left, neighbors in GRAPH.items()
        for right, weight in neighbors.items()
        if left < right
    ]


def execution_board(
    event: dict[str, object],
    *,
    final_path: list[str] | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """One registered graph + distance/queue/code snapshot."""

    distances = event["distances"]
    settled = set(event["settled"])
    queue = list(event["queue"])
    current = str(event.get("node", ""))
    path_nodes = set(final_path or [])
    path_edges = {
        frozenset((left, right))
        for left, right in zip(final_path or [], (final_path or [])[1:])
    }

    nodes: list[dict[str, object]] = []
    for name, position in POSITIONS.items():
        distance = distances[name]
        if name in path_nodes:
            color = PATH
        elif name == current:
            color = CURRENT
        elif name in settled:
            color = SETTLED
        elif distance < inf:
            color = FRONTIER
        else:
            color = UNSEEN
        label_distance = "∞" if distance == inf else f"{distance:g}"
        nodes.append(
            _node(
                f"graph_{name}",
                f"{name}\n{label_distance}",
                position,
                width=0.92,
                height=0.92,
                color=color,
                font_size=19,
                shape="circle",
            )
        )

    distance_positions = {
        "A": (2.55, 2.25),
        "B": (3.95, 2.25),
        "C": (5.35, 2.25),
        "D": (2.55, 1.15),
        "E": (3.95, 1.15),
        "F": (5.35, 1.15),
    }
    predecessors = event["predecessors"]
    for name, position in distance_positions.items():
        distance = distances[name]
        value = "∞" if distance == inf else f"{distance:g}"
        predecessor = predecessors.get(name, "—")
        color = CURRENT if name == current else (SETTLED if name in settled else FRONTIER)
        if distance == inf:
            color = UNSEEN
        nodes.append(
            _node(
                f"distance_{name}",
                f"{name}: {value}\nprev {predecessor}",
                position,
                width=1.18,
                height=0.8,
                color=color,
                font_size=16,
            )
        )

    queue_label = (
        "frontier  "
        + "  ".join(f"{node}:{distance:g}" for distance, node in queue)
        if queue
        else "frontier  ∅"
    )
    nodes.append(
        _node(
            "queue",
            queue_label,
            (3.95, 0.0),
            width=4.55,
            height=0.72,
            color=FRONTIER,
            font_size=17,
        )
    )
    line = {
        "initialize": "dist[source] ← 0",
        "settle": "u ← extract-min(frontier)",
        "relax": "if dist[u] + w(u,v) < dist[v]",
    }[str(event["kind"])]
    nodes.append(
        _node(
            "code",
            line,
            (3.95, -1.0),
            width=4.55,
            height=0.72,
            color=SETTLED,
            font_size=17,
        )
    )
    verdict_color = (
        ACCEPT
        if event.get("accepted") is True
        else REJECT
        if event.get("accepted") is False
        else CURRENT
    )
    nodes.append(
        _node(
            "action",
            str(event["message"]),
            (0.2, -2.1),
            width=10.9,
            height=0.72,
            color=verdict_color,
            font_size=17,
        )
    )

    edges: list[dict[str, object]] = []
    active_pair = (
        frozenset((str(event["node"]), str(event["neighbor"])))
        if event["kind"] == "relax"
        else frozenset()
    )
    for left, right, weight in _unique_edges():
        pair = frozenset((left, right))
        if pair in path_edges:
            color, width = PATH, 8
        elif pair == active_pair:
            color = ACCEPT if event.get("accepted") else REJECT
            width = 7
        else:
            color, width = EDGE, 3
        edges.append(
            {
                "id": f"{left}_{right}",
                "from": f"graph_{left}",
                "to": f"graph_{right}",
                "directed": False,
                "buff": 0.42,
                "color": color,
                "stroke_width": width,
                "label": str(weight),
                "font_size": 16,
            }
        )
    return nodes, edges


def negative_edge_counterexample() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Directed example where a later negative edge improves a settled node."""

    nodes = [
        _node("s", "S\n0", (-3.5, 0.0), width=1.0, height=1.0, color=CURRENT, shape="circle"),
        _node("a", "A\n2", (0.0, 1.4), width=1.0, height=1.0, color=REJECT, shape="circle"),
        _node("b", "B\n5", (0.0, -1.4), width=1.0, height=1.0, color=FRONTIER, shape="circle"),
        _node(
            "warning",
            "A is settled at 2 — but S→B→A costs 1",
            (3.25, 0.0),
            width=4.4,
            height=1.0,
            color=REJECT,
            font_size=19,
        ),
    ]
    edges = [
        {"id": "s_a", "from": "s", "to": "a", "directed": True, "buff": 0.5, "color": EDGE, "stroke_width": 5, "label": "2"},
        {"id": "s_b", "from": "s", "to": "b", "directed": True, "buff": 0.5, "color": EDGE, "stroke_width": 5, "label": "5"},
        {"id": "b_a", "from": "b", "to": "a", "directed": True, "buff": 0.5, "color": REJECT, "stroke_width": 7, "label": "−4"},
    ]
    return nodes, edges
