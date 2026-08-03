# Domain review — SN2 Reaction

**Review date:** 2026-08-03
**Reviewer:** AI source-and-structure review; independent chemistry review still
recommended before public scientific sign-off.

## Claims checked

1. The standard SN2 teaching mechanism is concerted and has no reaction
   intermediate.
2. Nucleophilic attack occurs from the side opposite the leaving group.
3. The transition state contains partial nucleophile–carbon and
   carbon–leaving-group bonds.
4. Backside passage produces stereochemical inversion at the reacting center.
5. A one-maximum reaction-coordinate profile is consistent with the scene's
   concerted, no-intermediate explanation.

## Evidence

- OpenStax Organic Chemistry, “11.2 The SN2 Reaction”:
  https://openstax.org/books/organic-chemistry/pages/11-2-the-sn2-reaction
- OpenStax Organic Chemistry, “11.3 Characteristics of the SN2 Reaction”:
  https://openstax.org/books/organic-chemistry/pages/11-3-characteristics-of-the-sn2-reaction
- IUPAC Gold Book, “nucleophilic substitution”:
  https://goldbook.iupac.org/terms/view/08191/html

## Deterministic checks

- Molecule geometry and energy marker are derived from the same normalized
  `progress` value.
- At progress 0.5, both dashed partial bonds and the energy maximum are shown.
- Reactant, transition-state, and product observations preserve stable atom and
  substituent identities.
- No intermediate state or intermediate energy well is presented.

## Assumptions and simplifications

- `HO⁻ + R–Br` is a generic teaching example, not a specified solvent/temperature
  experiment.
- H, CH3, and CH2CH3 are labelled persistent identities in a procedural 3D
  teaching geometry; this is not a named, optimized molecular structure.
- Atom spheres and straight bond segments are explanatory notation, not scale
  models of electron density or molecular motion.
- The energy curve is qualitative and intentionally omits solvent, entropy,
  isotope, and competing-pathway effects.
- The molecular and energy views share a continuous authored progress value,
  but that value is not a physical simulation or general engine clock.

## Unresolved review items

- Obtain independent organic-chemistry review before labeling the final master
  “domain approved.”
- Verify the exact stereochemical labelling and teaching geometry against the
  final master during independent review.
