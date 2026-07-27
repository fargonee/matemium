# Domain review — Feedback Control

**Review date:** 2026-07-27  
**Reviewer:** AI source-and-model review; independent controls review still
recommended before public sign-off.

## Claims checked

1. Closed-loop feedback compares measured output with a reference and uses the
   resulting error to affect the input.
2. PI control combines proportional error and accumulated error.
3. Integral action can remove steady error from a constant disturbance in the
   disclosed model.
4. Tuning and actuator dynamics affect transient drop, overshoot, oscillation,
   and settling.
5. Open loop cannot respond to an unmeasured change in hill load.

## Evidence

- MIT OpenCourseWare, *Analysis and Design of Feedback Control Systems*,
  course calendar and PID/control topics:
  https://ocw.mit.edu/courses/2-14-analysis-and-design-of-feedback-control-systems-spring-2014/pages/calendar/
- MIT OpenCourseWare, velocity-control laboratory using feedback and PI action:
  https://live.ocw.mit.edu/courses/2-14-analysis-and-design-of-feedback-control-systems-spring-2014/b933910c9c9271162ffa40dd6f652330_MIT2_14S14_Lab_6.pdf
- NASA Technical Reports Server, *Practical Loop-Shaping Design of Feedback
  Control Systems*:
  https://ntrs.nasa.gov/citations/20100023371

## Deterministic checks

- Every case contains 501 samples from 0 to 20 s; the hill begins at 3 s.
- Slow tuning minimum: about `22.07 m/s`; final: about `24.24 m/s`.
- Balanced tuning minimum: about `23.22 m/s`; final: about `24.98 m/s`.
- Aggressive tuning ranges from about `23.94` to `25.50 m/s` and oscillates.
- Open-loop final speed is about `17.67 m/s`.

## Assumptions and simplifications

- Vehicle speed uses a first-order longitudinal balance coupled to a
  first-order actuator lag.
- Units for the abstract command/load are normalized; only speed and time carry
  displayed physical units.
- No saturation, noise, delay beyond actuator lag, gear changes, road geometry,
  drag nonlinearity, or safety logic is modeled.
- Euler integration is used for deterministic teaching data, not controller
  certification.

## Unresolved review items

- Obtain independent controls review before final domain approval.
- The preview is not the final 1920×1080 website master.
