"""Landscape computer-science flagship: Dijkstra as visible changing state."""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings, LayoutBox
from canvas.builder import CanvasBuilder

from .helpers import (
    ACCEPT,
    BG,
    CURRENT,
    PATH,
    REJECT,
    SETTLED,
    WHITE,
    dijkstra_trace,
    execution_board,
    negative_edge_counterexample,
    reconstruct,
)

BOARD_STYLE = {"width": 13.2, "height": 6.05, "margin-bottom": 0.45}


def board_target(event: dict[str, object], *, final_path=None) -> CanvasElement:
    nodes, edges = execution_board(event, final_path=final_path)
    return CanvasElement(
        id="execution_target",
        type="Diagram",
        content={"nodes": nodes, "edges": edges},
        layout=LayoutBox(width=13.2, height=6.05, margin_bottom=0.45),
    )


def add_board(
    b: CanvasBuilder,
    event: dict[str, object],
    *,
    board_id: str,
    final_path=None,
) -> str:
    nodes, edges = execution_board(event, final_path=final_path)
    return b.add_diagram(
        nodes,
        edges,
        id=board_id,
        style=BOARD_STYLE,
        run_time=1.5,
    )


def morph_board(
    b: CanvasBuilder,
    board_id: str,
    event: dict[str, object],
    *,
    run_time: float = 0.8,
    final_path=None,
) -> None:
    target = board_target(event, final_path=final_path)
    target.id = f"{board_id}_target"
    b.add_element_morph(board_id, target, run_time=run_time)


def part_opening(b: CanvasBuilder, events: list[dict[str, object]]) -> None:
    b.add_heading(
        [
            b.run("DIJKSTRA", color=CURRENT, bold=True),
            b.run("  /  SHORTEST PATH AS CHANGING STATE", color=WHITE, bold=True),
        ],
        style={"width": 13.4, "margin-bottom": 0.4},
    )
    b.add_body(
        "How can one route become certain before every complete route has been tried?",
        style={"width": 12.2, "align": "center", "margin-bottom": 0.45},
    )
    add_board(b, events[0], board_id="opening_board")
    b.add_body(
        "Circle labels show node and tentative distance. The right panel shows predecessors, logical frontier, and active rule.",
        style={"width": 12.8, "align": "center", "margin-bottom": 0.8},
    )


def part_one_cycle(b: CanvasBuilder, events: list[dict[str, object]]) -> None:
    b.add_heading(
        "01  CHOOSE THE SMALLEST — THEN RELAX ITS EDGES",
        style={"margin-top": 2.6, "margin-bottom": 0.35},
    )
    cycle_id = add_board(b, events[1], board_id="first_cycle")
    for index in (2, 3, 4, 5, 6):
        morph_board(b, cycle_id, events[index], run_time=0.8)
    b.add_body(
        [b.run("✓  UPDATE  ·  0 + 2 < ∞  ·  C becomes 2", color=ACCEPT, bold=True)],
        style={"width": 10.5, "align": "center", "margin-bottom": 0.18},
    )
    b.add_body(
        [b.run("×  KEEP  ·  2 + 2 ≥ 0  ·  A stays 0", color=REJECT, bold=True)],
        style={"width": 10.5, "align": "center", "margin-bottom": 0.8},
    )


def part_repeat(b: CanvasBuilder, events: list[dict[str, object]]) -> None:
    b.add_heading(
        "02  THE SAME RULE MOVES THE FRONTIER",
        style={"margin-top": 2.6, "margin-bottom": 0.35},
    )
    b.add_body(
        "Blue values are tentative. Mint values are settled. Gold is the node currently being processed.",
        style={"width": 12.6, "align": "center", "margin-bottom": 0.35},
    )
    repeat_id = add_board(b, events[6], board_id="repeat_board")
    for index in (8, 12, 16, 17, 21, 22):
        morph_board(b, repeat_id, events[index], run_time=0.72)
    b.add_body(
        "Settled order: A → C → B → D → E → F",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_reconstruct(
    b: CanvasBuilder,
    events: list[dict[str, object]],
    distances: dict[str, float],
    predecessors: dict[str, str],
) -> None:
    path = reconstruct(predecessors, "F")
    b.add_heading(
        "03  PREDECESSORS TURN CERTAINTY INTO A ROUTE",
        style={"margin-top": 2.6, "margin-bottom": 0.35},
    )
    final_id = add_board(b, events[22], board_id="final_board")
    morph_board(b, final_id, events[22], final_path=path, run_time=1.2)
    b.add_state_transition(
        [
            {
                "target_id": f"{final_id}::edge:{'_'.join(sorted((left, right)))}",
                "changes": {"stroke_color": PATH, "stroke_width": 10},
            }
            for left, right in zip(path, path[1:])
        ],
        run_time=1.0,
        lag_ratio=0.1,
    )
    b.add_math(
        r"\mathrm{A\to C\to B\to D\to E\to F}\qquad \mathrm{cost}=13",
        style={"width": 11.8, "margin-bottom": 0.35},
        run_time=1.5,
    )
    b.add_body(
        "Read predecessor links backward from F; present the recovered path forward.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_boundary(b: CanvasBuilder) -> None:
    b.add_heading(
        "04  WHY EVERY EDGE WEIGHT MUST BE NON-NEGATIVE",
        style={"margin-top": 2.6, "margin-bottom": 0.35},
    )
    nodes, edges = negative_edge_counterexample()
    b.add_diagram(
        nodes,
        edges,
        id="negative_counterexample",
        style={"width": 12.0, "height": 4.6, "margin-bottom": 0.4},
        run_time=1.5,
    )
    b.add_body(
        "A later negative edge can undercut a node already treated as final. The greedy certainty is gone.",
        style={"width": 11.8, "align": "center", "margin-bottom": 0.7},
    )


def part_finale(b: CanvasBuilder) -> None:
    b.add_heading(
        "THE INVARIANT",
        style={"margin-top": 2.6, "margin-bottom": 0.3},
    )
    b.add_body(
        [
            b.run("smallest tentative distance", color=CURRENT, bold=True, font_size=34),
            b.run("  +  "),
            b.run("non-negative remaining edges", color=SETTLED, bold=True, font_size=34),
        ],
        style={"width": 13.0, "align": "center", "margin-bottom": 0.55},
    )
    b.add_body(
        "That node cannot be improved later — so its distance is final.",
        style={"width": 11.7, "align": "center", "margin-bottom": 0.5},
    )
    b.add_math(
        r"\min_{v\in\mathrm{frontier}} d[v]\quad\Longrightarrow\quad\mathrm{settle}(v)",
        id="dijkstra_invariant",
        style={"width": 9.8, "margin-bottom": 0.7},
        run_time=1.4,
    )
    b.add_camera_focus(
        "dijkstra_invariant",
        mode="isolate",
        zoom=1.22,
        hold_time=0.9,
        run_time=0.65,
        reset_run_time=0.55,
    )


class DijkstraExecution(CanvasScene):
    def __init__(self, **kwargs):
        events, distances, predecessors = dijkstra_trace()
        settings = CanvasSettings.for_youtube(
            title="What Really Happens During Dijkstra's Algorithm",
            background_color=BG,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        part_opening(builder, events)
        part_one_cycle(builder, events)
        part_repeat(builder, events)
        part_reconstruct(builder, events, distances, predecessors)
        part_boundary(builder)
        part_finale(builder)
        super().__init__(dsl=builder.build(), **kwargs)
