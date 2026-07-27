# Domain review — Fourier Epicycles

**Review date:** 2026-07-27  
**Reviewer:** AI source-and-calculation review; independent expert review still recommended before public scientific sign-off.

## Claims checked

1. The unit square wave can be represented using odd sine harmonics with
   coefficient `4/(πn)` for odd `n`.
2. Uniform circular motion has sinusoidal Cartesian projections.
3. Higher odd harmonics sharpen a square-wave partial sum.
4. Near a jump, Fourier partial sums exhibit Gibbs ringing whose region narrows
   as more terms are included while the overshoot does not simply vanish.
5. The scene must not claim uniform convergence at the jump.

## Evidence

- Eric W. Weisstein, “Fourier Series—Square Wave,” Wolfram MathWorld:
  https://mathworld.wolfram.com/FourierSeriesSquareWave.html
- MIT Mathematics, Gilbert Strang, “Fourier Series and Integrals,” section 4.1:
  https://math.mit.edu/~gs/cse/websections/cse41.pdf
- Eric W. Weisstein, “Gibbs Phenomenon,” Wolfram MathWorld:
  https://mathworld.wolfram.com/GibbsPhenomenon.html

## Deterministic checks

- `square_wave_terms(count)` generates harmonics `1, 3, 5, …`.
- Each amplitude is computed as `4/(πn)`.
- `partial_sum(t, count)` sums exactly those generated terms.
- Plot samples are generated locally from those functions; no dataset or
  external media is used.

## Assumptions and simplifications

- The reference square wave is normalized to values `−1` and `+1`.
- The value assigned exactly at a discontinuity is a plotting convention and
  is not used to claim pointwise equality there.
- The epicycle view displays the vector sum in a local geometric scale. It is
  a conceptual coordinate representation rather than a physical mechanism.
- The video introduces Fourier series, not the Fourier transform or formal
  convergence proofs.

## Unresolved review items

- Obtain independent mathematics review before labeling the final-quality
  master “domain approved.”
- The preview’s equations and qualitative Gibbs language are source-consistent;
  no numerical overshoot percentage is claimed.
