# From DNA to Protein

## Project identity

- **Subject:** Biology
- **Project slug:** `dna_to_protein`
- **Status:** Revised 1440×810, 30 fps flagship draft visually inspected; final 1920×1080 master and independent molecular-biology sign-off pending
- **Central question:** How does information stored in DNA become a working protein?
- **Primary audience:** Secondary-school and introductory biology learners
- **Target format:** 16:9 mute flagship master, approximately 65–75 seconds

## Purpose

This project must present gene expression as a sequence of information transformations across cellular spaces and scales. It should connect nucleotide sequence, transcription, RNA processing, translation, and the emergence of a protein without implying that the process is perfectly linear or fully captured by the simplified model.

The central visual idea is continuity of information: a small highlighted sequence should remain traceable as its representation changes.

## Learning outcomes

The viewer should understand:

- DNA stores sequence information;
- transcription produces a complementary RNA molecule;
- eukaryotic RNA may be processed before export;
- ribosomes read mRNA codons and tRNAs deliver amino acids;
- amino-acid sequence influences protein folding and function;
- different stages occur in different cellular locations.

## Narrative arc

1. **Move inward:** Establish cell, nucleus, chromosome, and one DNA region with large labels.
2. **Expose DNA:** Open the selected region before any RNA appears.
3. **Transcription:** Assemble complementary RNA codon-by-codon along the template.
4. **Processing:** Separate introns, move exons together, and identify mature mRNA.
5. **Export:** Move mature mRNA through a clearly labelled nuclear pore.
6. **Translation:** Repeat codon highlight, matching tRNA arrival, amino-acid delivery, and ribosome movement.
7. **Growing chain:** Keep codons and amino acids synchronized through the stop signal.
8. **Model boundary:** State that the four-residue trace is not a real protein or structure prediction.
9. **Synthesis:** Close on `DNA → RNA → CODONS → PROTEIN` without claiming an unshown function.

## Visual and motion direction

- Establish a stable camera journey through authored levels of detail: cell,
  nucleus, DNA region, molecular machinery.
- Use consistent base and amino-acid color mapping without relying on color alone.
- Keep directionality explicit: template reading direction, RNA growth, and ribosome movement.
- Use spatial transitions to show location changes rather than arbitrary scene cuts.
- Depict molecules schematically and label the level of simplification.
- Avoid presenting DNA as a continuously uncoiling decorative helix.

## Matemium capabilities this project must demonstrate

- multiscale camera transitions;
- a persistent multiscale 3D world with staged biological processes;
- sequence transformations;
- repeated data-driven molecular units;
- synchronized codon, tRNA, and amino-acid states;
- spatial compartments and transport;
- reusable helpers for strands, bases, ribosomes, and molecular annotations.

## Required source and assets

- Use a short fictional or carefully reviewed sequence chosen for teaching clarity.
- Generate bases, codons, amino acids, and process states from structured data.
- Keep the project self-contained and procedural.
- If a protein silhouette is used, include it as a small source vector with provenance rather than a raster video asset.

## Scope boundaries

- Do not imply that one gene always maps simply to one protein.
- Do not omit directionality where doing so creates a misconception.
- Do not depict transcription and translation in the same cellular location for a eukaryotic example.
- Do not claim that sequence alone makes folding visually predictable in the simplified animation.
- Avoid excessive biochemical detail that obscures the information-flow story.

## Acceptance criteria

- A biology reviewer verifies complementarity, directionality, codon grouping, and cellular locations.
- One highlighted information segment remains traceable from DNA through amino-acid sequence.
- Scale transitions preserve orientation and narrative continuity.
- The conclusion stops at protein unless a specific protein function is actually visualized.
- The scene renders from source with no required external video.
- The output demonstrates that Matemium can explain complex, multiscale living processes.
