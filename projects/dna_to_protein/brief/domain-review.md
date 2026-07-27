# Domain review — DNA to Protein

**Review date:** 2026-07-27  
**Reviewer:** AI source-and-sequence review; independent molecular-biology
review remains recommended before public sign-off.

## Claims checked

1. RNA is synthesized from a complementary DNA template during transcription.
2. The template is read `3′→5′` while RNA synthesis proceeds `5′→3′`.
3. Eukaryotic RNA processing occurs in the nucleus before mature mRNA export
   and cytoplasmic translation.
4. Ribosomes read mRNA in codons; tRNAs link codon recognition to amino-acid
   delivery.
5. `AUG` encodes methionine/start in this teaching context; `UGA` is a stop
   signal and does not encode an amino acid.
6. Translation is not the end of protein production; folding, chaperones, and
   chemical modification can affect mature function.

## Evidence

- NHGRI, DNA Fact Sheet, transcription of DNA information to mRNA and
  translation into amino-acid order:
  https://www.genome.gov/about-genomics/fact-sheets/Deoxyribonucleic-Acid-Fact-Sheet
- NHGRI, Codon glossary, triplet units that encode amino acids or termination:
  https://www.genome.gov/genetics-glossary/Codon
- NCBI Bookshelf, *From RNA to Protein*, codon-by-codon translation,
  eukaryotic processing/export, stop signaling, and protein folding:
  https://www.ncbi.nlm.nih.gov/books/NBK26829/
- NCBI Bookshelf, *Expression of Genetic Information*, complementary
  transcription, tRNA adaptor function, and the standard codon table:
  https://www.ncbi.nlm.nih.gov/books/NBK9842/

## Deterministic checks

- Template: `TAC GGA TTT CCG ACT`.
- Complement: `AUG CCU AAA GGC UGA`.
- Translation table result: `Met, Pro, Lys, Gly, Stop`.
- Base substitutions used by the helper are `T→A`, `A→U`, `C→G`, and `G→C`.
- All five codon records are generated from one source sequence.

## Assumptions and simplifications

- The sequence is fictional and intentionally tiny.
- Its four-residue product is not presented as a realistic protein.
- The processing diagram is generic; the short displayed coding sequence does
  not explicitly model exon coordinates, caps, tails, splice variants, or
  regulatory regions.
- Transcription and translation machinery are semantic diagrams rather than
  molecular structures.
- The fold morph is a conceptual spatial change, not structure prediction.
- Regulation, editing, degradation, localization, post-translational
  modification detail, and genetic-code exceptions are outside scope.

## Unresolved review items

- Obtain independent molecular-biology review before final domain approval.
- The preview is not the final 1920×1080 website master.
