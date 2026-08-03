"""From DNA to Protein — an explicit multiscale teaching journey.

One registered world preserves identity while short, isolated tapes clarify the
sequence mapping.  The spatial world now shows each biological transformation
instead of asking the viewer to infer it from an abstract morph.
"""

from __future__ import annotations

from canvas import CanvasElement, CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

from .helpers import (
    BG,
    COMPARTMENT,
    DNA,
    EXON,
    INTRON,
    MUTED,
    PROTEIN,
    RIBOSOME,
    RNA,
    WHITE,
    bio_text_element,
    biology_world_state,
    sequence_records,
)

WORLD_ID = "biology_scale_world"


def world_target(stage: str, *, sequence_index: int = 0) -> CanvasElement:
    return CanvasElement(
        id=WORLD_ID,
        type="BiologyScaleWorld",
        content=biology_world_state(stage, sequence_index=sequence_index),
        auto_focus=False,
    )


def bio_spec(
    b: CanvasBuilder,
    element_id: str,
    text: str,
    color: str = WHITE,
    *,
    font_size: int = 34,
    bold: bool = False,
    width: float = 10.8,
    height: float = 0.8,
) -> dict:
    return b.element_spec(
        bio_text_element(element_id, text, color=color, font_size=font_size, bold=bold),
        style={"width": width, "height": height, "align": "center"},
    )


def token_card(b: CanvasBuilder, element_id: str, value: str, color: str, *, font_size: int = 30) -> dict:
    return bio_spec(
        b,
        element_id,
        value,
        color,
        font_size=font_size,
        bold=True,
        width=2.05,
        height=0.76,
    )


def step_card(b: CanvasBuilder, element_id: str, number: str, label: str, color: str) -> dict:
    return bio_spec(
        b,
        element_id,
        f"{number}\n{label}",
        color,
        font_size=27,
        bold=True,
        width=2.55,
        height=1.35,
    )


def author_scale_tape(b: CanvasBuilder, tape) -> None:
    tape.add_flex_row(
        [bio_spec(b, "scale_title", "Four levels, one selected region", font_size=42, bold=True, width=11.3)],
        justify_content="center",
        style={"margin-bottom": 0.38},
    )
    tape.add_flex_row(
        [
            token_card(b, "scale_cell", "CELL", COMPARTMENT, font_size=31),
            token_card(b, "scale_nucleus", "NUCLEUS", DNA, font_size=31),
            token_card(b, "scale_chromosome", "CHROMOSOME", EXON, font_size=29),
            token_card(b, "scale_dna", "DNA REGION", RNA, font_size=29),
        ],
        gap=0.34,
        justify_content="center",
        style={"margin-bottom": 0.34},
    )
    tape.add_flex_row(
        [bio_spec(b, "scale_note", "Cinematic levels of detail — not a literal scale ruler.", EXON, font_size=30, bold=True, width=10.7)],
        justify_content="center",
        style={"margin-bottom": 0.18},
    )


def author_sequence_tape(b: CanvasBuilder, tape) -> None:
    tape.add_flex_row(
        [bio_spec(b, "sequence_title", "One sequence, three readable rows", font_size=40, bold=True, width=11.4)],
        justify_content="center",
        style={"margin-bottom": 0.28},
    )
    records = sequence_records()
    tape.add_flex_row(
        [bio_spec(b, "sequence_dna_label", "DNA template   3′ → 5′", DNA, font_size=29, bold=True)],
        justify_content="center",
        style={"margin-bottom": 0.1},
    )
    tape.add_flex_row(
        [token_card(b, f"sequence_dna_{record['index']}", record["dna"], DNA) for record in records],
        gap=0.12,
        justify_content="center",
        style={"margin-bottom": 0.14},
    )
    tape.add_flex_row(
        [bio_spec(b, "sequence_rna_label", "mRNA   5′ → 3′", RNA, font_size=29, bold=True)],
        justify_content="center",
        style={"margin-bottom": 0.1},
    )
    tape.add_flex_row(
        [token_card(b, f"sequence_rna_{record['index']}", record["rna"], RNA) for record in records],
        gap=0.12,
        justify_content="center",
        style={"margin-bottom": 0.14},
    )
    tape.add_flex_row(
        [
            token_card(
                b,
                f"sequence_amino_{record['index']}",
                record["amino"].upper(),
                MUTED if record["amino"] == "Stop" else PROTEIN,
                font_size=27,
            )
            for record in records
        ],
        gap=0.12,
        justify_content="center",
        style={"margin-bottom": 0.12},
    )


def author_processing_tape(b: CanvasBuilder, tape) -> None:
    tape.add_flex_row(
        [bio_spec(b, "processing_title", "RNA is edited before export", font_size=42, bold=True, width=11.3)],
        justify_content="center",
        style={"margin-bottom": 0.36},
    )
    tape.add_flex_row(
        [
            step_card(b, "processing_1", "1", "pre-mRNA", RNA),
            step_card(b, "processing_2", "2", "remove introns", INTRON),
            step_card(b, "processing_3", "3", "join exons", EXON),
            step_card(b, "processing_4", "4", "mature mRNA", RNA),
        ],
        gap=0.18,
        justify_content="center",
        style={"margin-bottom": 0.4},
    )
    tape.add_flex_row(
        [bio_spec(b, "processing_note", "Nucleus first · cytoplasm after the nuclear pore", COMPARTMENT, font_size=30, bold=True, width=10.7)],
        justify_content="center",
        style={"margin-bottom": 0.16},
    )


def author_translation_tape(b: CanvasBuilder, tape) -> None:
    tape.add_flex_row(
        [bio_spec(b, "translation_title", "Translation repeats one clear cycle", font_size=41, bold=True, width=11.3)],
        justify_content="center",
        style={"margin-bottom": 0.36},
    )
    tape.add_flex_row(
        [
            bio_spec(b, "translation_1", "1   Highlight one codon", RNA, font_size=30, bold=True, width=5.15),
            bio_spec(b, "translation_2", "2   Bring in matching tRNA", EXON, font_size=30, bold=True, width=5.15),
        ],
        gap=0.35,
        justify_content="center",
        style={"margin-bottom": 0.2},
    )
    tape.add_flex_row(
        [
            bio_spec(b, "translation_3", "3   Attach its amino acid", PROTEIN, font_size=30, bold=True, width=5.15),
            bio_spec(b, "translation_4", "4   Move the ribosome", RIBOSOME, font_size=30, bold=True, width=5.15),
        ],
        gap=0.35,
        justify_content="center",
        style={"margin-bottom": 0.3},
    )
    tape.add_flex_row(
        [bio_spec(b, "translation_stop", "UGA is a stop signal, not an amino acid.", MUTED, font_size=31, bold=True, width=10.7)],
        justify_content="center",
        style={"margin-bottom": 0.16},
    )


def author_model_boundary(b: CanvasBuilder, tape) -> None:
    tape.add_flex_row(
        [bio_spec(b, "model_title", "A teaching trace — not a structure prediction", PROTEIN, font_size=39, bold=True, width=11.4)],
        justify_content="center",
        style={"margin-bottom": 0.38},
    )
    tape.add_flex_row(
        [bio_spec(b, "model_chain", "MET — PRO — LYS — GLY", WHITE, font_size=35, bold=True, width=10.8)],
        justify_content="center",
        style={"margin-bottom": 0.22},
    )
    tape.add_flex_row(
        [bio_spec(b, "model_note", "Four residues track information; they do not model a real protein.", WHITE, font_size=28, width=10.8)],
        justify_content="center",
        style={"margin-bottom": 0.18},
    )


def author_finale(b: CanvasBuilder, tape) -> None:
    tape.add_flex_row(
        [
            bio_spec(b, "final_dna", "DNA", DNA, font_size=38, bold=True, width=1.55),
            bio_spec(b, "final_arrow_1", "→", WHITE, font_size=38, bold=True, width=0.7),
            bio_spec(b, "final_rna", "RNA", RNA, font_size=38, bold=True, width=1.55),
            bio_spec(b, "final_arrow_2", "→", WHITE, font_size=38, bold=True, width=0.7),
            bio_spec(b, "final_codons", "CODONS", EXON, font_size=38, bold=True, width=2.6),
            bio_spec(b, "final_arrow_3", "→", WHITE, font_size=38, bold=True, width=0.7),
            bio_spec(b, "final_protein", "PROTEIN", PROTEIN, font_size=38, bold=True, width=2.8),
        ],
        gap=0.1,
        justify_content="center",
        style={"margin-bottom": 0.38},
    )
    tape.add_flex_row(
        [bio_spec(b, "final_message", "One message across space, scale, and form.", WHITE, font_size=34, bold=True, width=10.8)],
        justify_content="center",
        style={"margin-bottom": 0.16},
    )


def build_production() -> CanvasBuilder:
    b = CanvasBuilder(
        canvas_settings=CanvasSettings.for_youtube(
            title="From DNA to Protein",
            background_color=BG,
        )
    )
    scale = b.add_tape("scale", frame_width=12.2, frame_height=5.8)
    sequence = b.add_tape("sequence", frame_width=12.2, frame_height=6.4)
    processing = b.add_tape("processing", frame_width=12.2, frame_height=5.8)
    translation = b.add_tape("translation", frame_width=12.2, frame_height=5.8)
    model = b.add_tape("model", frame_width=12.2, frame_height=5.5)
    finale = b.add_tape("finale", frame_width=12.2, frame_height=5.2)

    b.add_object("BiologyScaleWorld", id=WORLD_ID, content=biology_world_state("cell"))
    b.add_camera_inspect(
        WORLD_ID,
        path=[
            b.inspect_shot(phi=38, theta=-72, zoom=1.12, run_time=1.4, hold=0.7),
            b.inspect_shot(phi=24, theta=-88, zoom=1.32, run_time=1.3, hold=0.75),
        ],
        return_to_sheet=False,
    )

    b.add_element_morph(WORLD_ID, world_target("nucleus"), run_time=1.35)
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=22, theta=-88, zoom=1.3, run_time=1.1, hold=0.8)],
        return_to_sheet=False,
    )
    b.add_element_morph(WORLD_ID, world_target("chromosome"), run_time=1.3)
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=18, theta=-90, zoom=1.34, run_time=1.0, hold=0.75)],
        return_to_sheet=False,
    )
    b.add_element_morph(WORLD_ID, world_target("gene"), run_time=1.35)
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=16, theta=-90, zoom=1.38, run_time=1.0, hold=0.85)],
        return_to_sheet=False,
    )
    author_scale_tape(b, scale)

    b.add_element_morph(WORLD_ID, world_target("dna_open"), run_time=1.4)
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=16, theta=-90, zoom=1.34, run_time=1.15, hold=0.85)],
        return_to_sheet=False,
    )
    for index in range(5):
        b.add_element_morph(WORLD_ID, world_target("transcription", sequence_index=index), run_time=1.05)
        b.add_camera_inspect(
            WORLD_ID,
            path=[b.inspect_shot(phi=12, theta=-90, zoom=1.32, run_time=0.4, hold=0.42)],
            return_to_sheet=False,
        )
    author_sequence_tape(b, sequence)

    b.add_element_morph(WORLD_ID, world_target("pre_mrna"), run_time=1.25)
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=10, theta=-90, zoom=1.36, run_time=0.8, hold=0.8)],
        return_to_sheet=False,
    )
    b.add_element_morph(WORLD_ID, world_target("splicing"), run_time=1.45)
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=10, theta=-90, zoom=1.36, run_time=0.65, hold=0.9)],
        return_to_sheet=False,
    )
    b.add_element_morph(WORLD_ID, world_target("mature_mrna"), run_time=1.35)
    b.add_camera_inspect(
        WORLD_ID,
        path=[b.inspect_shot(phi=10, theta=-90, zoom=1.38, run_time=0.65, hold=0.9)],
        return_to_sheet=False,
    )
    author_processing_tape(b, processing)

    b.add_element_morph(WORLD_ID, world_target("export"), run_time=1.35)
    b.add_camera_inspect(
        WORLD_ID,
        path=[
            b.inspect_shot(phi=18, theta=-90, zoom=1.24, run_time=1.0, hold=0.55),
            b.inspect_shot(phi=12, theta=-90, zoom=1.38, target_offset=(0.55, 0.0, 0.0), run_time=1.25, hold=0.9),
        ],
        return_to_sheet=False,
    )
    author_translation_tape(b, translation)

    for index in range(5):
        b.add_element_morph(WORLD_ID, world_target("translation", sequence_index=index), run_time=1.05)
        b.add_camera_inspect(
            WORLD_ID,
            path=[b.inspect_shot(phi=10, theta=-90, zoom=1.1, run_time=0.48, hold=0.58)],
            return_to_sheet=False,
        )

    author_model_boundary(b, model)
    b.add_element_morph(WORLD_ID, world_target("protein"), run_time=1.7)
    b.add_camera_inspect(
        WORLD_ID,
        path=[
            b.inspect_shot(phi=10, theta=-90, zoom=1.18, run_time=1.1, hold=0.75),
            b.inspect_shot(phi=4, theta=-90, zoom=1.12, run_time=1.2, hold=0.9),
        ],
        return_to_sheet=False,
    )
    author_finale(b, finale)
    return b


class DNAToProtein(CanvasScene):
    def __init__(self, **kwargs):
        super().__init__(dsl=build_production().build(), **kwargs)
