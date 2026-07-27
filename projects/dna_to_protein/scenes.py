"""Landscape biology flagship: information flow from DNA to protein."""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings, LayoutBox
from canvas.builder import CanvasBuilder

from .helpers import (
    BG,
    DNA,
    EXON,
    MUTED,
    PROTEIN,
    RNA,
    WHITE,
    chain_edges,
    chain_nodes,
    function_diagram,
    processing_diagram,
    scale_diagram,
    sequence_records,
    transcribe,
    translation_diagram,
)


def folded_chain_target() -> CanvasElement:
    return CanvasElement(
        id="folded_chain_target",
        type="Diagram",
        content={"nodes": chain_nodes(folded=True), "edges": chain_edges()},
        layout=LayoutBox(width=10.5, height=3.6, margin_bottom=0.5),
    )


def part_hook(b: CanvasBuilder) -> None:
    b.add_heading(
        [
            b.run("FROM DNA", color=DNA, bold=True),
            b.run("  TO  "),
            b.run("PROTEIN", color=PROTEIN, bold=True),
        ],
        style={"width": 11.5, "margin-bottom": 0.35},
    )
    b.add_body(
        "A protein can bind, carry, signal, or catalyze. Where does its amino-acid order come from?",
        style={"width": 11.7, "align": "center", "margin-bottom": 0.5},
    )
    nodes, edges = function_diagram()
    b.add_diagram(
        nodes,
        edges,
        id="function_hook",
        style={"width": 10.8, "height": 2.7, "margin-bottom": 0.35},
        run_time=1.3,
    )
    b.add_body(
        "SUBSTRATE  →  SHAPE-SPECIFIC INTERACTION  →  PRODUCT",
        style={"width": 11.0, "align": "center", "margin-bottom": 0.7},
    )


def part_scale(b: CanvasBuilder) -> None:
    b.add_heading(
        "01  KEEP THE SAME INFORMATION IN VIEW",
        style={"margin-top": 2.6, "margin-bottom": 0.55},
    )
    nodes, edges = scale_diagram()
    scale_id = b.add_diagram(
        nodes,
        edges,
        id="scale_ladder",
        style={"width": 11.8, "height": 3.0, "margin-bottom": 0.35},
        run_time=1.3,
    )
    for node_id in ("cell", "nucleus", "gene", "sequence"):
        b.add_state_transition(
            [
                {
                    "target_id": f"{scale_id}::node:{node_id}",
                    "changes": {"scale": 1.08},
                }
            ],
            run_time=0.45,
        )
    b.add_body(
        "CELL  →  NUCLEUS  →  GENE REGION  →  ONE SHORT TEACHING WINDOW",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.65},
    )


def part_transcription(b: CanvasBuilder) -> None:
    b.add_heading(
        "02  TRANSCRIPTION: COMPLEMENTARY, ANTIPARALLEL",
        style={"margin-top": 2.6, "margin-bottom": 0.5},
    )
    b.add_body(
        "DNA template read  3′ → 5′",
        style={"width": 10.5, "align": "center", "margin-bottom": 0.2},
    )
    b.add_flex_row(
        [
            b.text_spec(
                f"{record['dna']}\n↓\n{record['rna']}",
                style={"width": 2.15},
            )
            for record in sequence_records()
        ],
        gap=0.25,
        justify_content="center",
        style={"margin-bottom": 0.2},
    )
    b.add_body(
        "RNA transcript built  5′ → 3′",
        style={"width": 10.5, "align": "center", "margin-bottom": 0.3},
    )
    b.add_math(
        r"T\leftrightarrow A,\quad A\leftrightarrow U,\quad C\leftrightarrow G,\quad G\leftrightarrow C",
        style={"width": 10.0, "margin-bottom": 0.55},
        run_time=1.1,
    )


def part_processing(b: CanvasBuilder) -> None:
    b.add_heading(
        "03  EUKARYOTIC RNA IS PROCESSED BEFORE EXPORT",
        style={"margin-top": 2.6, "margin-bottom": 0.5},
    )
    nodes, edges = processing_diagram()
    process_id = b.add_diagram(
        nodes,
        edges,
        id="rna_processing",
        style={"width": 12.2, "height": 3.1, "margin-bottom": 0.35},
        run_time=1.4,
    )
    for node_id in ("dna", "pre", "splice", "mature", "cytoplasm"):
        b.add_state_transition(
            [
                {
                    "target_id": f"{process_id}::node:{node_id}",
                    "changes": {"scale": 1.06},
                }
            ],
            run_time=0.4,
        )
    b.add_body(
        "This teaching window shows the mature coding message; real transcripts can include introns, multiple exons, and alternative processing.",
        style={"width": 12.1, "align": "center", "margin-bottom": 0.65},
    )


def part_translation(b: CanvasBuilder) -> None:
    b.add_heading(
        "04  TRANSLATION: THE RIBOSOME ADVANCES ONE CODON",
        style={"margin-top": 2.6, "margin-bottom": 0.5},
    )
    nodes, edges = translation_diagram()
    translation_id = b.add_diagram(
        nodes,
        edges,
        id="translation",
        style={"width": 11.8, "height": 3.2, "margin-bottom": 0.3},
        run_time=1.4,
    )
    for index in range(1, 6):
        b.add_state_transition(
            [
                {
                    "target_id": f"{translation_id}::node:codon_{index}",
                    "changes": {"scale": 1.08},
                }
            ],
            run_time=0.5,
        )
    b.add_body(
        "AUG starts this teaching message. tRNA anticodons pair with codons while tRNAs deliver amino acids. UGA stops translation; STOP is not an amino acid.",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.25},
    )
    b.add_body(
        f"mRNA  5′  {transcribe()}  3′",
        style={"width": 11.5, "align": "center", "margin-bottom": 0.65},
    )


def part_fold_and_boundary(b: CanvasBuilder) -> None:
    b.add_heading(
        "05  A SEQUENCE ENTERS A CELLULAR FOLDING PROBLEM",
        style={"margin-top": 2.6, "margin-bottom": 0.5},
    )
    chain_id = b.add_diagram(
        chain_nodes(folded=False),
        chain_edges(),
        id="amino_chain",
        style={"width": 10.5, "height": 3.6, "margin-bottom": 0.35},
        run_time=1.4,
    )
    b.add_element_morph(chain_id, folded_chain_target(), run_time=1.3)
    b.add_body(
        "MET  —  PRO  —  LYS  —  GLY",
        style={"width": 9.5, "align": "center", "margin-bottom": 0.25},
    )
    b.add_body(
        "This four-residue teaching chain is not a realistic protein. It stands in for longer sequences whose folding also depends on environment, chaperones, and modifications.",
        style={"width": 12.0, "align": "center", "margin-bottom": 0.35},
    )
    b.add_body(
        "DNA  →  PROCESSED RNA  →  CODONS  →  AMINO-ACID SEQUENCE  →  FOLDING + MATURATION  →  FUNCTION",
        id="information_flow",
        style={"width": 12.4, "align": "center", "margin-bottom": 0.65},
    )
    b.add_camera_focus(
        "information_flow",
        mode="isolate",
        zoom=1.12,
        hold_time=0.85,
        run_time=0.6,
        reset_run_time=0.5,
    )


class DNAToProtein(CanvasScene):
    def __init__(self, **kwargs):
        settings = CanvasSettings.for_youtube(
            title="From DNA to Protein",
            background_color=BG,
        )
        builder = CanvasBuilder(canvas_settings=settings)
        part_hook(builder)
        part_scale(builder)
        part_transcription(builder)
        part_processing(builder)
        part_translation(builder)
        part_fold_and_boundary(builder)
        super().__init__(dsl=builder.build(), **kwargs)
