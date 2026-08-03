"""Deterministic sequence and geometry for the DNA-to-protein flagship.

The short sequence is fictional and chosen for transparent teaching:

    DNA template  3′-TAC GGA TTT CCG ACT-5′
    mature mRNA   5′-AUG CCU AAA GGC UGA-3′
    peptide          Met Pro Lys Gly Stop
"""

from __future__ import annotations

import math

import numpy as np
from manim import (
    LEFT,
    RIGHT,
    UP,
    Arc,
    Circle,
    Dot,
    Dot3D,
    Line,
    Line3D,
    RoundedRectangle,
    Sphere,
    Text,
    VGroup,
    VMobject,
)

from canvas import CanvasElement, register_object_kind

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


def bio_text_element(
    element_id: str,
    text: str,
    *,
    color: str = WHITE,
    font_size: int = 34,
    bold: bool = False,
) -> CanvasElement:
    """A project-local, explicitly sans-serif tape label."""

    return CanvasElement(
        id=element_id,
        type="BioText",
        content={
            "text": text,
            "color": color,
            "font_size": font_size,
            "bold": bold,
        },
        auto_focus=False,
    )


def _build_bio_text(elem, wrap, target_width, surface_factory):
    content = dict(elem.content or {})
    mob = Text(
        str(content.get("text", "")),
        font="DejaVu Sans",
        font_size=int(content.get("font_size", 34)),
        weight="BOLD" if bool(content.get("bold", False)) else "NORMAL",
        color=str(content.get("color", WHITE)),
        line_spacing=1.1,
    )
    if target_width and mob.width > float(target_width):
        mob.set_width(float(target_width))
    return mob


def _measure_bio_text(elem, *, usable_width, style_width, style_height, wrap):
    mob = _build_bio_text(elem, False, None, None)
    width = float(style_width) if style_width is not None else min(float(mob.width), float(usable_width))
    height = float(style_height) if style_height is not None else float(mob.height)
    return width, height, False


def _validate_bio_text(content: object) -> list[str]:
    if not isinstance(content, dict):
        return ["content must be a mapping"]
    if not str(content.get("text", "")).strip():
        return ["text must be non-empty"]
    return []


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


# ---------------------------------------------------------------------------
# Project-local multiscale biology world
# ---------------------------------------------------------------------------

WORLD_STAGES = {
    "cell",
    "nucleus",
    "chromosome",
    "gene",
    "dna_open",
    "transcription",
    "pre_mrna",
    "splicing",
    "mature_mrna",
    "export",
    "translation",
    "protein",
}


def biology_world_state(stage: str, *, sequence_index: int = 0) -> dict[str, object]:
    if stage not in WORLD_STAGES:
        raise ValueError(f"unknown biology world stage: {stage}")
    index = int(sequence_index)
    if not 0 <= index <= len(sequence_records()) - 1:
        raise ValueError("sequence_index must address one of the five teaching codons")
    return {"stage": stage, "sequence_index": index}


def _curve(points, color: str, width: float = 5.0, opacity: float = 1.0) -> VMobject:
    path = VMobject(color=color, stroke_width=width)
    path.set_points_smoothly(np.array(points, dtype=float)).set_stroke(opacity=opacity)
    return path


def _helix(*, length: float = 6.0, turns: float = 2.5, samples: int = 54):
    xs = np.linspace(-length / 2.0, length / 2.0, samples)
    first = np.array(
        [[x, 0.58 * math.sin(turns * 2.0 * math.pi * (x / length)), 0.58 * math.cos(turns * 2.0 * math.pi * (x / length))] for x in xs]
    )
    second = first.copy()
    second[:, 1:] *= -1.0
    strands = VGroup(_curve(first, DNA, 5.0), _curve(second, "#8cc8ff", 5.0))
    for index in range(2, samples - 2, 5):
        strands.add(
            Line3D(first[index], second[index], thickness=0.016, color=EXON, resolution=6).set_opacity(0.7)
        )
    return strands


def _empty_parts() -> dict[str, VGroup]:
    return {
        "cell": VGroup(),
        "nucleus": VGroup(),
        "chromosome": VGroup(),
        "gene": VGroup(),
        "dna": VGroup(),
        "template": VGroup(),
        "rna": VGroup(),
        "exons": VGroup(),
        "introns": VGroup(),
        "pore": VGroup(),
        "ribosome": VGroup(),
        "codon": VGroup(),
        "trna": VGroup(),
        "amino": VGroup(),
        "peptide": VGroup(),
        "protein": VGroup(),
        "labels": VGroup(),
    }


def _text_label(
    text: str,
    position: tuple[float, float, float],
    color: str = WHITE,
    *,
    font_size: int = 34,
    background: bool = True,
) -> VGroup:
    """High-contrast project-local label for mostly top-down world shots."""

    label = Text(text, font="DejaVu Sans", font_size=font_size, weight="BOLD", color=color)
    label.move_to(np.array(position, dtype=float))
    if not background:
        return VGroup(label)
    plate = RoundedRectangle(
        width=label.width + 0.34,
        height=label.height + 0.22,
        corner_radius=0.12,
        stroke_color=color,
        stroke_width=1.4,
        fill_color=BG,
        fill_opacity=0.9,
    ).move_to(label)
    return VGroup(plate, label)


def _chromosome_curve(*, scale: float = 1.0, color: str = EXON) -> VGroup:
    first = _curve(
        [[0.9 * math.sin(t), 1.65 * math.sin(2.0 * t), 0.16 * math.cos(1.4 * t)] for t in np.linspace(-1.45, 1.45, 40)],
        color,
        10.0,
        0.96,
    )
    second = first.copy().rotate(math.pi / 2.0)
    return VGroup(first, second).scale(scale)


def _cell_scene(parts: dict[str, VGroup], *, nucleus_only: bool = False) -> None:
    if nucleus_only:
        nucleus = Sphere(radius=2.65, resolution=(18, 12))
        nucleus.set_fill(DNA, opacity=0.07).set_stroke(DNA, width=1.5, opacity=0.55)
        parts["nucleus"].add(nucleus)
        parts["chromosome"].add(_chromosome_curve(scale=0.62))
        parts["labels"].add(
            _text_label("NUCLEUS", (0.0, 3.25, 0.25), DNA, font_size=38),
            _text_label("chromosome", (0.0, -2.25, 0.35), EXON, font_size=27),
        )
        return

    membrane = Sphere(radius=3.05, resolution=(18, 12))
    membrane.set_fill(COMPARTMENT, opacity=0.045).set_stroke(COMPARTMENT, width=1.4, opacity=0.45)
    nucleus = Sphere(radius=1.08, resolution=(16, 10))
    nucleus.set_fill(DNA, opacity=0.12).set_stroke(DNA, width=1.4, opacity=0.72)
    nucleus.shift(np.array([0.35, 0.05, 0.18]))
    chromosome = _chromosome_curve(scale=0.22).shift(np.array([0.35, 0.05, 0.22]))
    parts["cell"].add(membrane)
    parts["nucleus"].add(nucleus)
    parts["chromosome"].add(chromosome)
    parts["labels"].add(
        _text_label("CELL", (0.0, 3.65, 0.15), COMPARTMENT, font_size=40),
        _text_label("nucleus", (0.35, -1.45, 0.35), DNA, font_size=28),
    )


def _chromosome_scene(parts: dict[str, VGroup]) -> None:
    chromosome = _chromosome_curve(scale=1.05)
    parts["chromosome"].add(chromosome)
    parts["labels"].add(
        _text_label("CHROMOSOME", (0.0, 3.1, 0.2), EXON, font_size=38),
        _text_label("condensed DNA", (0.0, -2.75, 0.25), WHITE, font_size=25),
    )


def _gene_scene(parts: dict[str, VGroup]) -> None:
    chromosome_points = [
        [2.8 * math.sin(1.25 * t), 1.45 * math.sin(2.0 * t), 0.45 * math.cos(1.7 * t)]
        for t in np.linspace(-2.2, 2.2, 46)
    ]
    chromosome = _curve(chromosome_points, MUTED, 7.0, 0.58)
    parts["chromosome"].add(chromosome)
    middle = chromosome_points[19:29]
    parts["gene"].add(_curve(middle, EXON, 13.0, 1.0))
    parts["labels"].add(
        _text_label("ONE GENE REGION", (0.0, 3.0, 0.35), EXON, font_size=38),
        _text_label("selected information", (0.0, -2.7, 0.35), WHITE, font_size=25),
    )


def _dna_open_scene(parts: dict[str, VGroup]) -> None:
    left = _helix(length=2.7, turns=1.15, samples=30).shift(LEFT * 2.25)
    right = _helix(length=2.7, turns=1.15, samples=30).shift(RIGHT * 2.25)
    top = _curve([[-0.95, 0.6, 0.12], [0.0, 1.25, 0.12], [0.95, 0.6, 0.12]], DNA, 7.0)
    bottom = _curve([[-0.95, -0.6, 0.12], [0.0, -1.25, 0.12], [0.95, -0.6, 0.12]], "#8cc8ff", 7.0)
    parts["dna"].add(left, top, bottom, right)
    parts["gene"].add(
        RoundedRectangle(width=2.4, height=2.9, corner_radius=0.2, color=EXON, stroke_width=2.2)
        .set_fill(EXON, opacity=0.04)
    )
    parts["labels"].add(
        _text_label("DNA REGION OPENS", (0.0, 3.1, 0.3), DNA, font_size=38),
        _text_label("template exposed", (0.0, -2.45, 0.3), EXON, font_size=27),
    )


def _codon_card(codon: str, center: np.ndarray, color: str, *, active: bool = False) -> VGroup:
    card = RoundedRectangle(
        width=1.68,
        height=0.82,
        corner_radius=0.14,
        stroke_color=WHITE if active else color,
        stroke_width=3.0 if active else 1.5,
        fill_color=color,
        fill_opacity=0.28 if active else 0.13,
    )
    text = Text(codon, font="DejaVu Sans", font_size=28, weight="BOLD", color=WHITE if active else color)
    return VGroup(card, text).move_to(center)


def _transcription_scene(parts: dict[str, VGroup], sequence_index: int) -> None:
    records = sequence_records()
    x_positions = np.linspace(-3.8, 3.8, len(records))
    for record, x_pos in zip(records, x_positions):
        parts["template"].add(_codon_card(record["dna"], np.array([x_pos, 0.65, 0.0]), DNA))
    for record, x_pos in zip(records[: sequence_index + 1], x_positions):
        parts["rna"].add(
            _codon_card(
                record["rna"],
                np.array([x_pos, -0.65, 0.15]),
                RNA,
                active=int(record["index"]) == sequence_index + 1,
            )
        )
        parts["rna"].add(Line([x_pos, 0.2, 0.05], [x_pos, -0.2, 0.1], color=EXON, stroke_width=2.0))
    endpoint = float(x_positions[sequence_index])
    polymerase = Sphere(radius=0.5, resolution=(14, 8))
    polymerase.stretch(1.35, dim=0).set_fill(RIBOSOME, opacity=0.62).set_stroke(RIBOSOME, width=1.2)
    polymerase.move_to(np.array([endpoint, 0.0, 0.65]))
    parts["gene"].add(polymerase)
    parts["labels"].add(
        _text_label("DNA template  3′ → 5′", (0.0, 2.25, 0.2), DNA, font_size=30),
        _text_label("pre-mRNA grows  5′ → 3′", (0.0, -2.25, 0.25), RNA, font_size=30),
        _text_label("RNA polymerase", (endpoint, 1.45, 0.75), RIBOSOME, font_size=23),
    )


def _processing_scene(parts: dict[str, VGroup], stage: str) -> None:
    block_specs = [
        ("EXON 1", EXON, 1.65),
        ("intron", INTRON, 1.45),
        ("EXON 2", EXON, 1.65),
        ("intron", INTRON, 1.45),
        ("EXON 3", EXON, 1.65),
    ]
    if stage == "mature_mrna":
        block_specs = [item for item in block_specs if item[0].startswith("EXON")]
    total = sum(width for _, _, width in block_specs) + 0.18 * (len(block_specs) - 1)
    cursor = -total / 2.0
    for index, (label, color, width) in enumerate(block_specs):
        center_x = cursor + width / 2.0
        y_pos = 0.0
        opacity = 0.28
        if stage == "splicing" and label == "intron":
            y_pos = -1.45
            opacity = 0.08
        card = RoundedRectangle(
            width=width,
            height=0.95,
            corner_radius=0.13,
            stroke_color=color,
            stroke_width=2.0,
            fill_color=color,
            fill_opacity=opacity,
        )
        text = Text(label, font="DejaVu Sans", font_size=22, weight="BOLD", color=color)
        group = VGroup(card, text).move_to(np.array([center_x, y_pos, 0.0]))
        if label == "intron":
            parts["introns"].add(group)
        else:
            parts["exons"].add(group)
        cursor += width + 0.18
    if stage == "pre_mrna":
        title, subtitle = "PRE-mRNA", "exons and introns"
    elif stage == "splicing":
        title, subtitle = "RNA SPLICING", "introns leave · exons move together"
        parts["rna"].add(
            Arc(radius=1.25, start_angle=0.15, angle=1.2, color=WHITE, stroke_width=3.0).shift(LEFT * 1.2 + UP * 0.55),
            Arc(radius=1.25, start_angle=1.8, angle=1.2, color=WHITE, stroke_width=3.0).shift(RIGHT * 1.2 + UP * 0.55),
        )
    else:
        title, subtitle = "MATURE mRNA", "joined exons are ready for export"
    parts["labels"].add(
        _text_label(title, (0.0, 2.35, 0.25), RNA, font_size=38),
        _text_label(subtitle, (0.0, -2.25, 0.25), WHITE, font_size=26),
    )


def _export_scene(parts: dict[str, VGroup]) -> None:
    boundary = Circle(radius=2.7, color=COMPARTMENT, stroke_width=8)
    boundary.set_fill(COMPARTMENT, opacity=0.025).set_stroke(opacity=0.65)
    parts["nucleus"].add(boundary)
    pore = VGroup(*[
        RoundedRectangle(width=0.28, height=0.72, corner_radius=0.08, color=EXON, fill_opacity=0.45)
        .move_to(np.array([2.7, offset, 0.12]))
        for offset in (-0.62, -0.2, 0.2, 0.62)
    ])
    parts["pore"].add(pore)
    rna_points = [
        [-1.9 + 0.92 * t, 0.45 * math.sin(1.8 * t), 0.18]
        for t in np.linspace(0.0, 5.2, 48)
    ]
    parts["rna"].add(_curve(rna_points, RNA, 7.0))
    parts["labels"].add(
        _text_label("NUCLEUS", (-1.15, 2.05, 0.3), COMPARTMENT, font_size=30),
        _text_label("NUCLEAR PORE", (3.75, 1.15, 0.3), EXON, font_size=28),
        _text_label("mature mRNA exits", (2.6, -1.8, 0.3), RNA, font_size=27),
    )


def _translation_scene(parts: dict[str, VGroup], sequence_index: int) -> None:
    records = sequence_records()
    x_positions = np.linspace(-4.2, 4.2, len(records))
    for index, (record, x_pos) in enumerate(zip(records, x_positions)):
        card = _codon_card(record["rna"], np.array([x_pos, -0.75, 0.0]), RNA, active=index == sequence_index)
        parts["rna"].add(card)
        if index == sequence_index:
            parts["codon"].add(
                RoundedRectangle(
                    width=1.9,
                    height=1.04,
                    corner_radius=0.17,
                    color=WHITE,
                    stroke_width=2.4,
                ).move_to(card)
            )
    current_x = float(x_positions[sequence_index])
    upper = Sphere(radius=0.88, resolution=(14, 8))
    upper.stretch(1.45, dim=0).stretch(0.58, dim=1).set_fill(RIBOSOME, opacity=0.58).set_stroke(RIBOSOME, width=1.1)
    upper.shift(np.array([current_x, 0.05, 0.5]))
    lower = Sphere(radius=0.62, resolution=(14, 8))
    lower.stretch(1.42, dim=0).stretch(0.52, dim=1).set_fill(EXON, opacity=0.4).set_stroke(EXON, width=1.0)
    lower.shift(np.array([current_x, -0.35, 0.3]))
    parts["ribosome"].add(upper, lower)
    amino_colors = (RIBOSOME, PROTEIN, EXON, RNA)
    residue_count = min(sequence_index + 1, 4)
    peptide_points = []
    for index in range(residue_count):
        point = np.array([current_x - 0.7 + 0.48 * index, 1.15 + 0.36 * index, 0.35])
        peptide_points.append(point)
        residue = Dot3D(point, radius=0.2, color=amino_colors[index], resolution=(8, 8))
        parts["peptide"].add(residue)
    if len(peptide_points) >= 2:
        parts["peptide"].add(_curve(peptide_points, PROTEIN, 4.0))
    current = records[sequence_index]
    if current["amino"] != "Stop":
        stem = VGroup(
            Line([current_x, -2.55, 0.05], [current_x, -1.25, 0.05], color=EXON, stroke_width=6.0),
            Line([current_x - 0.38, -2.0, 0.05], [current_x, -2.35, 0.05], color=EXON, stroke_width=5.0),
            Line([current_x + 0.38, -2.0, 0.05], [current_x, -2.35, 0.05], color=EXON, stroke_width=5.0),
        )
        parts["trna"].add(stem)
        amino_dot = Dot([current_x, -2.75, 0.1], radius=0.23, color=amino_colors[sequence_index])
        parts["amino"].add(amino_dot)
        parts["labels"].add(
            _text_label("tRNA", (current_x - 1.05, -2.0, 0.25), EXON, font_size=24),
            _text_label(current["amino"].upper(), (current_x, -3.25, 0.25), amino_colors[sequence_index], font_size=25),
        )
    else:
        parts["labels"].add(_text_label("STOP · release", (current_x, -2.25, 0.25), MUTED, font_size=28))
    parts["labels"].add(
        _text_label("RIBOSOME", (current_x, 2.65, 0.7), RIBOSOME, font_size=29),
        _text_label("mRNA  5′ → 3′", (0.0, -1.55, 0.2), RNA, font_size=25),
        _text_label("growing peptide", (0.0, 2.05, 0.35), PROTEIN, font_size=25),
    )


def _protein_scene(parts: dict[str, VGroup]) -> None:
    points = np.array(
        [
            [1.6 * math.sin(1.7 * t), 1.15 * math.sin(2.6 * t), 0.8 * math.cos(2.1 * t)]
            for t in np.linspace(0.0, 2.0 * math.pi, 72)
        ],
        dtype=float,
    )
    parts["protein"].add(_curve(points, PROTEIN, 9.0))
    colors = (RIBOSOME, PROTEIN, EXON, RNA)
    for index, fraction in enumerate((0.08, 0.31, 0.57, 0.82)):
        point = points[int(fraction * (len(points) - 1))]
        parts["peptide"].add(Dot3D(point, radius=0.18, color=colors[index], resolution=(7, 7)))
    parts["labels"].add(
        _text_label("SCHEMATIC PROTEIN", (0.0, 3.05, 0.3), PROTEIN, font_size=38),
        _text_label("form depends on far more than four residues", (0.0, -2.75, 0.3), WHITE, font_size=24),
    )


def _build_biology_world(elem, wrap, target_width, surface_factory):
    content = dict(elem.content or {})
    stage = str(content.get("stage", "cell"))
    index = int(content.get("sequence_index", 0))
    parts = _empty_parts()
    if stage == "cell":
        _cell_scene(parts, nucleus_only=False)
    elif stage == "nucleus":
        _cell_scene(parts, nucleus_only=True)
    elif stage == "chromosome":
        _chromosome_scene(parts)
    elif stage == "gene":
        _gene_scene(parts)
    elif stage == "dna_open":
        _dna_open_scene(parts)
    elif stage == "transcription":
        _transcription_scene(parts, index)
    elif stage in {"pre_mrna", "splicing", "mature_mrna"}:
        _processing_scene(parts, stage)
    elif stage == "export":
        _export_scene(parts)
    elif stage == "translation":
        _translation_scene(parts, index)
    else:
        _protein_scene(parts)
    world = VGroup(*parts.values())
    world.matemium_parts = parts
    return world


def _validate_biology_world(content: object) -> list[str]:
    if not isinstance(content, dict):
        return ["content must be a mapping"]
    stage = str(content.get("stage", ""))
    if stage not in WORLD_STAGES:
        return [f"stage must be one of {sorted(WORLD_STAGES)}"]
    try:
        index = int(content.get("sequence_index", -1))
    except (TypeError, ValueError):
        return ["sequence_index must be an integer"]
    if not 0 <= index < len(sequence_records()):
        return ["sequence_index must address one of the five teaching codons"]
    return []


def _biology_world_parts(content: object) -> set[str]:
    return set(_empty_parts())


register_object_kind(
    "BiologyScaleWorld",
    build=_build_biology_world,
    validate=_validate_biology_world,
    parts=_biology_world_parts,
)

register_object_kind(
    "BioText",
    build=_build_bio_text,
    measure=_measure_bio_text,
    validate=_validate_bio_text,
)
