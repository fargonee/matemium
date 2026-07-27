"""Portrait chemistry flagship: a concerted SN2 substitution."""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings, LayoutBox
from canvas.builder import CanvasBuilder

from .helpers import (
    BG,
    BREAKING,
    BROMINE,
    ENERGY,
    FORMING,
    OXYGEN,
    SOFT,
    WHITE,
    energy_marker,
    energy_plot_series,
    mechanism_diagram,
    steric_access_diagram,
)

DIAGRAM_STYLE = {"width": 7.6, "height": 5.15, "margin-bottom": 0.55}
PLOT_STYLE = {"width": 7.6, "height": 4.15, "margin-bottom": 0.55}
PLOT_OPTIONS = {
    "x_range": [0.0, 1.0, 0.25],
    "y_range": [-0.25, 1.1, 0.25],
    "width": 6.2,
    "height": 3.55,
    "tips": False,
}


def diagram_target(state: str) -> CanvasElement:
    nodes, edges = mechanism_diagram(state)
    return CanvasElement(
        id=f"mechanism_{state}",
        type="Diagram",
        content={"nodes": nodes, "edges": edges},
        layout=LayoutBox(width=7.6, height=5.15, margin_bottom=0.55),
    )


def energy_target(state: str) -> CanvasElement:
    return CanvasElement(
        id=f"energy_{state}",
        type="DataPlot",
        content={
            "series": energy_plot_series(),
            "markers": energy_marker(state),
            **PLOT_OPTIONS,
        },
        layout=LayoutBox(width=7.6, height=4.15, margin_bottom=0.55),
    )


def steric_target(crowded: bool) -> CanvasElement:
    nodes, edges = steric_access_diagram(crowded)
    state = "crowded" if crowded else "open"
    return CanvasElement(
        id=f"steric_{state}",
        type="Diagram",
        content={"nodes": nodes, "edges": edges},
        layout=LayoutBox(width=7.6, height=4.7, margin_bottom=0.55),
    )


# ---DIV: Opening---
def part_opening(b: CanvasBuilder) -> None:
    b.add_heading(
        [b.run("ONE STEP.", color=FORMING, bold=True, font_size=48)],
        style={"width": 7.6, "margin-bottom": 0.08},
    )
    b.add_heading(
        [b.run("TWO BONDS.", color=BREAKING, bold=True, font_size=48)],
        style={"width": 7.6, "margin-bottom": 0.55},
    )
    b.add_body(
        "How can a new bond form at the same moment another bond breaks?",
        style={"width": 7.2, "align": "center", "margin-bottom": 0.6},
    )
    b.add_math(
        r"\mathrm{Nu^- + R{-}Br \longrightarrow R{-}Nu + Br^-}",
        style={"width": 7.2, "margin-bottom": 0.9},
        run_time=1.3,
    )
    b.add_body(
        "SN2 is a concerted substitution: one coordinated passage, not two separate reactions.",
        style={"width": 7.2, "align": "center", "margin-bottom": 1.1},
    )


# ---DIV: Roles and backside attack---
def part_mechanism(b: CanvasBuilder) -> None:
    nodes, edges = mechanism_diagram("reactants")
    b.add_heading(
        "Backside attack sets the geometry",
        style={"width": 7.5, "margin-bottom": 0.4},
    )
    mechanism_id = b.add_diagram(
        nodes,
        edges,
        id="sn2_mechanism",
        style=DIAGRAM_STYLE,
        run_time=1.35,
    )
    b.add_body(
        "HO⁻ approaches the electrophilic carbon opposite the C—Br bond.",
        style={"width": 7.2, "align": "center", "margin-bottom": 1.05},
    )
    b.add_state_transition(
        [
            {
                "target_id": f"{mechanism_id}::node:nu",
                "changes": {"fill_opacity": 0.75, "scale": 1.1},
            },
            {
                "target_id": f"{mechanism_id}::edge:leaving",
                "changes": {"stroke_width": 9},
            },
        ],
        run_time=0.75,
    )
    b.add_element_morph(
        mechanism_id,
        diagram_target("transition"),
        run_time=1.4,
    )
    b.add_body(
        "TRANSITION STATE\nBoth C···O and C···Br are partial. There is no isolable intermediate.",
        style={"width": 7.2, "align": "center", "margin-bottom": 0.65},
    )
    b.add_element_morph(
        mechanism_id,
        diagram_target("products"),
        run_time=1.4,
    )
    b.add_body(
        "The three substituents emerge on the opposite side: stereochemical inversion.",
        style={"width": 7.2, "align": "center", "margin-bottom": 1.0},
    )


# ---DIV: Energy coordinate---
def part_energy(b: CanvasBuilder) -> None:
    b.add_heading(
        "One mechanism. One energy barrier.",
        style={"width": 7.5, "margin-bottom": 0.4},
    )
    plot_id = b.add_data_plot(
        energy_plot_series(),
        markers=energy_marker("reactants"),
        id="sn2_energy",
        style=PLOT_STYLE,
        run_time=1.3,
        **PLOT_OPTIONS,
    )
    b.add_body(
        "REACTANTS\nseparate nucleophile and substrate",
        style={"width": 6.9, "align": "center", "margin-bottom": 0.45},
    )
    b.add_element_morph(plot_id, energy_target("transition"), run_time=1.0)
    b.add_body(
        "ENERGY MAXIMUM\none transition state with two partial bonds",
        style={"width": 6.9, "align": "center", "margin-bottom": 0.45},
    )
    b.add_state_transition(
        [
            {
                "target_id": f"{plot_id}::series:profile",
                "changes": {"stroke_color": ENERGY, "stroke_width": 9},
            },
            {
                "target_id": f"{plot_id}::marker:progress",
                "changes": {"scale": 1.45},
            },
        ],
        run_time=0.7,
    )
    b.add_element_morph(plot_id, energy_target("products"), run_time=1.0)
    b.add_body(
        "PRODUCTS\nnew C—O bond; bromide has departed",
        style={"width": 6.9, "align": "center", "margin-bottom": 0.45},
    )
    b.add_body(
        "STANDARD ELEMENTARY CASE",
        style={"width": 6.9, "align": "center", "margin-bottom": 0.25},
    )
    b.add_math(
        r"\mathrm{rate}=k[\mathrm{Nu^-}][\mathrm{R{-}Br}]",
        style={"width": 6.4, "margin-bottom": 1.0},
        run_time=1.2,
    )


# ---DIV: Steric access---
def part_sterics(b: CanvasBuilder) -> None:
    nodes, edges = steric_access_diagram(False)
    b.add_heading(
        "Backside access can be blocked",
        style={"width": 7.4, "margin-bottom": 0.4},
    )
    steric_id = b.add_diagram(
        nodes,
        edges,
        id="steric_access",
        style={"width": 7.6, "height": 4.7, "margin-bottom": 0.55},
        run_time=1.25,
    )
    b.add_body(
        "LESS CROWDED\nThe nucleophile can reach the carbon along the backside path.",
        style={"width": 7.2, "align": "center", "margin-bottom": 0.55},
    )
    b.add_element_morph(steric_id, steric_target(True), run_time=1.25)
    b.add_body(
        "MORE CROWDED\nBulky groups obstruct approach and slow the SN2 pathway.",
        style={"width": 7.2, "align": "center", "margin-bottom": 1.0},
    )


# ---DIV: Synthesis---
def part_finale(b: CanvasBuilder) -> None:
    b.add_heading(
        "CONCERTED",
        style={"width": 7.3, "margin-bottom": 0.45},
    )
    b.add_body(
        "BACKSIDE APPROACH\n+  BOND-MAKING\n+  BOND-BREAKING\n+  INVERSION",
        style={"width": 7.0, "align": "center", "margin-bottom": 0.8},
    )
    b.add_body(
        "Four observations. One molecular event.",
        style={"width": 7.0, "align": "center", "margin-bottom": 0.55},
    )
    b.add_math(
        r"\mathrm{Nu^- \;\cdots\; C \;\cdots\; Br}",
        id="sn2_signature",
        style={"width": 6.2, "margin-bottom": 0.7},
        run_time=1.2,
    )
    b.add_camera_focus(
        "sn2_signature",
        mode="isolate",
        zoom=1.35,
        hold_time=0.9,
        run_time=0.7,
        reset_run_time=0.6,
    )


class SN2Reaction(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_reels(
            title="Inside an SN2 Reaction",
            background_color=BG,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        part_opening(builder)
        part_mechanism(builder)
        part_energy(builder)
        part_sterics(builder)
        part_finale(builder)
        super().__init__(dsl=builder.build(), **kwargs)
