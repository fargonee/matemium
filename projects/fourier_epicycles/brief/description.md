# Fourier Series: Drawing With Rotating Circles

## Project identity

- **Subject:** Mathematics
- **Project slug:** `fourier_epicycles`
- **Status:** Flagship authoring complete; preview visually accepted; final-quality website master pending
- **Central question:** How can a collection of simple circular motions reconstruct a complex wave or drawing?
- **Primary audience:** Curious learners who know basic graphs and trigonometry but do not need prior Fourier analysis
- **Target format:** 16:9 flagship master, approximately 90–110 seconds; a portrait adaptation may follow

## Purpose

This project must make Fourier series feel inevitable rather than mysterious. The learner should leave understanding that a periodic signal can be described as a sum of simpler rotating components, that each component contributes a frequency and amplitude, and that adding more components improves an approximation.

The project is not a decorative epicycle animation. It must connect four representations throughout the explanation:

1. circular motion;
2. sine and cosine waves;
3. a frequency spectrum;
4. the reconstructed signal or path.

## Learning outcomes

By the end, the viewer should be able to explain:

- why uniform circular motion produces sinusoidal coordinates;
- what frequency, amplitude, and phase control;
- how several components add into one signal;
- why sharp features require more high-frequency terms;
- why approximation error shrinks but does not disappear uniformly near a jump.

## Narrative arc

1. **The challenge:** Present a square wave or recognizable closed contour and ask how circles could draw it.
2. **One rotating vector:** Track its vertical coordinate and reveal the corresponding sine wave.
3. **A second frequency:** Add a faster, smaller vector and show both geometric and graph-based summation.
4. **Build the spectrum:** Introduce several odd harmonics as labeled frequency bars.
5. **Reconstruction:** Keep epicycles, partial sum, and target visible in synchronized views while terms are added.
6. **The difficult edge:** Zoom into a discontinuity and identify the persistent overshoot without turning the scene into a formal proof.
7. **Synthesis:** Collapse the views into the statement that complex periodic behavior can be assembled from simple rotations.

## Visual and motion direction

- Use one stable color per harmonic across the circle chain, spectrum, formula, and plot.
- Preserve a persistent visual link between the current vector tip and the plotted signal.
- Introduce mathematical notation only after the motion it describes is visible.
- Treat the target curve as a quiet reference and the evolving approximation as the active object.
- Camera movement must communicate a change of scale or representation, never merely add spectacle.
- The final composition should show epicycles, spectrum, and reconstruction operating together.

## Matemium capabilities this project must demonstrate

- synchronized plots, vectors, formulas, and labels;
- parameter-driven repeated structures;
- traced paths and persistent motion history;
- coordinated multi-panel or multi-tape layout;
- smooth camera transitions between overview and local detail;
- deliberate highlighting of corresponding symbols and visual elements;
- reusable helpers for harmonics, spectra, and partial sums.

## Required source and assets

- Author all geometry and plots procedurally; no external image is required.
- Keep harmonic coefficients in a small inspectable data structure.
- Provide helpers for a rotating vector, spectrum bar, and reconstruction trace.
- The example must remain deterministic and render without network access.

## Scope boundaries

- Do not begin with the general complex Fourier transform.
- Do not present a long derivation of coefficient integrals.
- Do not imitate a famous existing Fourier animation shot for shot.
- Do not overload the first minute with more than three simultaneous representations.
- Avoid tiny equations, uncontrolled line crossings, and decorative particles.

## Acceptance criteria

- A learner can verbally connect circular motion to a sinusoid after one viewing.
- Every harmonic uses consistent visual identity across all representations.
- At least three partial sums are compared clearly.
- The final animation contains no overlaps, cropped labels, unreadable formulas, or unexplained symbols.
- The scene renders from bundled source alone and has no required media files.
- Source is organized well enough for a user to change the target signal or number of terms.
- The rendered result is strong enough to serve as the mathematics hero video on the website.
