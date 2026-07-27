# Production report — Fourier Epicycles

## Outcome

- **Project behavior completed:** Seven-beat mute explanation connecting
  rotation, sinusoid, odd-harmonic spectrum, partial sums, synchronized
  geometry/plot states, and Gibbs behavior.
- **Engine behavior changed:** None during this flagship reauthoring.
- **Project-local helpers added:** Fourier coefficients, deterministic sampling,
  reconstruction plots, spectra, epicycle diagrams, and stable visual palette.
- **Authoring check:** `check_project` passed with 77 timeline items, no errors,
  and no warnings after the first visual-repair pass.
- **First preview render:** Completed at 960×540, 15 fps, landscape, 97.265
  seconds, 3,633,591 bytes, 109 rendered animations.
- **First visual inspection:** Sampled contact sheets at 8- and 12-second
  intervals. Found formula overflow, dense spectrum legend, residual
  cross-section content, and compressed final rich text.
- **Repairs made:** Replaced expanded formulas with compact harmonic counts,
  removed the redundant spectrum legend, enlarged section gaps, and rebuilt
  the final definitions as three flex cards.
- **Second preview render:** Completed and inspected; it proved the formula,
  legend, and spacing repairs, but exposed compressed rich-run cards in the
  finale.
- **Third/final authoring preview:** Completed at 960×540, 15 fps, landscape,
  96.797396 seconds, 3,303,185 bytes, and 107 rendered animations.
- **Final visual inspection:** Inspected an 8-second-interval contact sheet and
  the full-resolution preview frame at 90 seconds. The opening, single-circle
  projection, spectrum, successive partial sums, paired epicycle/plot state,
  Gibbs close-up, and finale are legible and remain inside the frame. The
  revised two-line frequency/amplitude/phase cards are balanced and readable.
- **Mute verification:** `ffprobe` reported no audio stream.
- **Deterministic checks:** Odd harmonic sequence, `4/π` first coefficient, and
  the one-term value at `π/2` passed exact-tolerance assertions.
- **Domain review:** Source-and-calculation review recorded in
  `brief/domain-review.md`; independent expert sign-off remains pending.
- **Backward compatibility:** Scene class remains `FourierEpicycles`; no public
  engine API changed.
- **Known limitations:** Phase-linked views use paired sequential morphs rather
  than a general shared-clock binding. Preview evidence is not a final-quality
  1080p master.
- **Honest readiness level:** Authoring-stage preview accepted. The source is a
  bundled flagship candidate; a final-quality 1920×1080 render and independent
  mathematics sign-off remain required before public showcase acceptance.
