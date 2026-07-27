"""Deterministic sequence and geometry for the DNA-to-protein flagship.

The short sequence is fictional and chosen for transparent teaching:

    DNA template  3′-TAC GGA TTT CCG ACT-5′
    mature mRNA   5′-AUG CCU AAA GGC UGA-3′
    peptide          Met Pro Lys Gly Stop
"""

from __future__ import annotations

BG = "#07131d"
WHITE = "#f4f8fc"
MUTED = "#71879a"
DNA = "#58a6ff"
RNA = "#5ce1a8"
EXON = "#ffd166"
INTRON = "#c779ff"
RIBOSOME = "#ff9f5a"
PROTEIN = "#ff6b9d"
COMPARTMENT = "#7692a8"

DNA_TEMPLATE = "TAC GGA TTT CCG ACT"
CODON_TABLE = {
    "AUG": "Met",
    "CCU": "Pro",
    "AAA": "Lys",
    "GGC": "Gly",
    "UGA": "Stop",
}


def transcribe(template: str = DNA_TEMPLATE) -> str:
    """Return complementary RNA written in the opposite, 5′→3′ direction."""

    return template.translate(str.maketrans({"A": "U", "T": "A", "C": "G", "G": "C"}))


def translate(mrna: str) -> list[str]:
    return [CODON_TABLE[codon] for codon in mrna.split()]


def sequence_records() -> list[dict[str, str]]:
    mrna = transcribe()
    return [
        {"index": str(index + 1), "dna": dna, "rna": rna, "amino": CODON_TABLE[rna]}
        for index, (dna, rna) in enumerate(zip(DNA_TEMPLATE.split(), mrna.split()))
    ]


def _node(
    node_id: str,
    label: str,
    position: tuple[float, float],
    color: str,
    *,
    width: float = 2.2,
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
        "fill_opacity": 0.22,
        "font_size": font_size,
    }


def function_diagram() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """A deliberately schematic protein-function hook."""

    nodes = [
        _node("substrate", "SUBSTRATE", (-4.2, 0.0), EXON),
        _node("protein", "FOLDED\nPROTEIN", (0.0, 0.0), PROTEIN, width=2.6),
        _node("product", "PRODUCT", (4.2, 0.0), RNA),
    ]
    return nodes, []


def scale_diagram() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    nodes = [
        _node("cell", "CELL", (-4.8, 0.0), COMPARTMENT),
        _node("nucleus", "NUCLEUS", (-1.7, 0.0), DNA),
        _node("gene", "GENE\nREGION", (1.7, 0.0), EXON),
        _node("sequence", "15-BASE\nTEACHING WINDOW", (4.8, 0.0), RNA, width=2.7),
    ]
    return nodes, []


def processing_diagram() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Spatially separate eukaryotic nuclear processing from translation."""

    nodes = [
        _node("dna", "DNA\nNUCLEUS", (-5.2, 0.0), DNA),
        _node("pre", "PRE-mRNA", (-2.6, 0.0), RNA),
        _node("splice", "EXONS JOIN\nINTRON REMOVED", (0.0, 0.0), INTRON, width=2.7),
        _node("mature", "MATURE mRNA", (2.8, 0.0), RNA, width=2.4),
        _node("cytoplasm", "EXPORT TO\nCYTOPLASM", (5.5, 0.0), COMPARTMENT, width=2.5),
    ]
    return nodes, []


def translation_diagram() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    nodes: list[dict[str, object]] = []
    x_positions = (-5.0, -2.5, 0.0, 2.5, 5.0)
    for record, x_pos in zip(sequence_records(), x_positions):
        amino = record["amino"].upper()
        color = MUTED if amino == "STOP" else PROTEIN
        nodes.append(
            _node(
                f"codon_{record['index']}",
                f"{record['rna']}\n{amino}",
                (x_pos, 0.0),
                color,
                width=2.0,
                height=1.15,
                font_size=21,
            )
        )
    return nodes, []


def chain_nodes(*, folded: bool = False) -> list[dict[str, object]]:
    amino_acids = [record["amino"] for record in sequence_records() if record["amino"] != "Stop"]
    if folded:
        positions = [(-3.1, 0.15), (-0.9, 0.55), (1.1, -0.35), (3.1, 0.3)]
    else:
        positions = [(-4.0, 0.0), (-1.35, 0.0), (1.35, 0.0), (4.0, 0.0)]
    colors = (RIBOSOME, PROTEIN, EXON, RNA)
    return [
        _node(
            f"aa_{index + 1}",
            amino.upper(),
            position,
            color,
            width=1.85,
            height=0.85,
            font_size=20,
        )
        for index, (amino, position, color) in enumerate(zip(amino_acids, positions, colors))
    ]


def chain_edges() -> list[dict[str, object]]:
    # The ordered nodes carry sequence. Diagram connectors currently cross
    # compact labels, so bonds are represented by a separate text chain.
    return []
