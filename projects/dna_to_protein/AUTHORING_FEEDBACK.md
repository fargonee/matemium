# Authoring feedback — DNA to Protein

## Current evidence

- Structured sequence records generate the DNA template, complementary mRNA,
  codons, amino-acid labels, and stop signal from one source.
- `Diagram` expresses spatial scale, nuclear processing/export, translation,
  and the amino-acid chain.
- Semantic `StateTransition` advances through scale contexts and codons.
- `ElementMorph` transforms the ordered residue window into a schematic
  spatial arrangement.
- `check_project` passes with 44 authored timeline items and no diagnostics.

## Engine changes required

None. General diagrams, semantic addressing, transforms, flex layout, math,
root-tape travel, and focus cover the project without biology-specific engine
behavior.

## Authoring and visual findings

- Applying `stroke_width` to a semantic diagram node also thickened its text
  glyphs. Modest scale-only emphasis remained readable.
- Repeating direction labels inside every codon card created clutter. Separate
  strand-direction labels around one aligned sequence row were clearer.
- Diagram connectors crossed compact residue labels even with buffer values;
  ordered nodes plus a separate text chain were safer.
- Structural validity did not catch the scientific implication that a
  four-residue chain might look like a realistic folded protein. Domain review
  prompted an explicit on-screen boundary.

## Honest remaining limitations

- There is no shared sequence cursor binding DNA bases, codons, tRNAs, and
  residues to one reactive index; the project stages semantic snapshots.
- Spatial scale is a traceable ladder, not a nested-coordinate camera journey.
- The fold morph is conceptual and cannot predict or represent molecular
  structure.
- Preview acceptance does not replace a final 1920×1080 render or independent
  molecular-biology review.

## Generalizable maturity conclusion

The engine can explain a multistage biological information transformation with
structured source, semantic tokens, spatial contexts, and geometry morphing.
Keyed sequences, shared cursors, and nested coordinate spaces would be broadly
useful future abstractions, but they should be designed across language,
history, algorithms, and biology rather than as gene-expression special cases.
