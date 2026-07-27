"""Transparent linear-market data for the economics flagship.

All values are fictional teaching quantities.  The graph uses quantity on the
x-axis and price on the y-axis:

    demand: P = a - Q
    supply: P = Q + c
"""

from __future__ import annotations

BG = "#07131d"
WHITE = "#f4f8fc"
MUTED = "#64788c"
DEMAND = "#4da3ff"
SUPPLY = "#ff9f5a"
SHOCK = "#ff6b6b"
EQUILIBRIUM = "#ffd166"
ADAPT = "#5ce1a8"
RECOVERY = "#7fe36a"
PERSIST = "#c779ff"

STATES = {
    "baseline": {"demand_intercept": 100.0, "supply_intercept": 20.0},
    "shock": {"demand_intercept": 100.0, "supply_intercept": 40.0},
    "adapt": {"demand_intercept": 90.0, "supply_intercept": 40.0},
}


def equilibrium(demand_intercept: float, supply_intercept: float) -> tuple[float, float]:
    """Solve ``Qd = a-P`` and ``Qs = P-c``; return (price, quantity)."""

    price = (demand_intercept + supply_intercept) / 2.0
    quantity = demand_intercept - price
    return price, quantity


def state_equilibrium(name: str) -> tuple[float, float]:
    state = STATES[name]
    return equilibrium(
        float(state["demand_intercept"]),
        float(state["supply_intercept"]),
    )


def curve_points(name: str, curve: str, samples: int = 81) -> list[list[float]]:
    state = STATES[name]
    points: list[list[float]] = []
    for index in range(samples):
        quantity = 80.0 * index / (samples - 1)
        if curve == "demand":
            price = float(state["demand_intercept"]) - quantity
        elif curve == "supply":
            price = quantity + float(state["supply_intercept"])
        else:
            raise ValueError(f"Unknown curve: {curve}")
        points.append([quantity, price])
    return points


def market_series(name: str) -> list[dict[str, object]]:
    supply_color = SUPPLY if name == "baseline" else SHOCK
    return [
        {
            "id": "demand",
            "points": curve_points(name, "demand"),
            "color": DEMAND,
            "stroke_width": 6,
        },
        {
            "id": "supply",
            "points": curve_points(name, "supply"),
            "color": supply_color,
            "stroke_width": 6,
        },
    ]


def equilibrium_marker(name: str) -> list[dict[str, object]]:
    price, quantity = state_equilibrium(name)
    return [
        {
            "id": "equilibrium",
            "point": [quantity, price],
            "color": EQUILIBRIUM,
            "radius": 0.13,
        }
    ]


def scenarios() -> list[dict[str, float | str]]:
    return [
        {
            "name": "baseline",
            "price": state_equilibrium("baseline")[0],
            "quantity": state_equilibrium("baseline")[1],
        },
        {
            "name": "shock",
            "price": state_equilibrium("shock")[0],
            "quantity": state_equilibrium("shock")[1],
        },
        {
            "name": "demand adapts",
            "price": state_equilibrium("adapt")[0],
            "quantity": state_equilibrium("adapt")[1],
        },
    ]


def price_paths() -> list[dict[str, object]]:
    """Illustrative adjustment paths sharing the same initial shock."""

    return [
        {
            "id": "quick_recovery",
            "points": [[0, 60], [1, 70], [2, 68], [3, 65], [4, 62], [5, 60], [6, 60]],
            "color": RECOVERY,
            "stroke_width": 6,
            "smooth": True,
        },
        {
            "id": "persistent",
            "points": [[0, 60], [1, 70], [2, 70], [3, 70], [4, 70], [5, 70], [6, 70]],
            "color": PERSIST,
            "stroke_width": 6,
            "smooth": True,
        },
        {
            "id": "adaptation",
            "points": [[0, 60], [1, 70], [2, 68], [3, 66], [4, 65], [5, 65], [6, 65]],
            "color": ADAPT,
            "stroke_width": 6,
            "smooth": True,
        },
    ]


def _node(
    node_id: str,
    label: str,
    position: tuple[float, float],
    color: str,
    *,
    width: float = 2.1,
    height: float = 0.9,
    font_size: int = 19,
) -> dict[str, object]:
    return {
        "id": node_id,
        "label": label,
        "position": list(position),
        "shape": "rounded",
        "width": width,
        "height": height,
        "color": color,
        "fill_color": color,
        "fill_opacity": 0.24,
        "font_size": font_size,
    }


def causal_chain() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    nodes = [
        _node("harvest", "1  HARVEST\nFAILURE", (-5.0, 0.0), SHOCK),
        _node("available", "2  AVAILABLE\nGRAIN ↓", (-2.5, 0.0), SUPPLY),
        _node("supply", "3  SUPPLY AT\nEACH PRICE ↓", (0.2, 0.0), SUPPLY, width=2.35),
        _node("market", "4  NEW\nEQUILIBRIUM", (3.0, 0.0), EQUILIBRIUM, width=2.35),
        _node("choices", "5  HOUSEHOLDS +\nPRODUCERS ADAPT", (5.6, 0.0), ADAPT, width=2.5),
    ]
    # The ordered node row carries the causal sequence.  A separate text arrow
    # chain is used below it so arrowheads never obscure compact node labels.
    return nodes, []


def assumptions_diagram() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    nodes = [
        _node("model", "LINEAR\nTEACHING MODEL", (0.0, 0.0), EQUILIBRIUM, width=2.5),
        _node("demand", "demand fixed\ninitially", (-3.8, 0.5), DEMAND),
        _node("product", "one fictional\nproduct", (3.8, 0.5), MUTED),
        _node("timing", "equilibrium is\nnot instant", (-3.8, -0.5), SUPPLY),
        _node("omitted", "inventories, policy,\nexpectations omitted", (3.8, -0.5), ADAPT, width=2.8),
    ]
    edges = [
        {"id": "demand", "from": "model", "to": "demand", "directed": False, "buff": 0.45, "color": MUTED, "stroke_width": 3},
        {"id": "product", "from": "model", "to": "product", "directed": False, "buff": 0.45, "color": MUTED, "stroke_width": 3},
        {"id": "timing", "from": "model", "to": "timing", "directed": False, "buff": 0.45, "color": MUTED, "stroke_width": 3},
        {"id": "omitted", "from": "model", "to": "omitted", "directed": False, "buff": 0.45, "color": MUTED, "stroke_width": 3},
    ]
    return nodes, edges
