# Authoring feedback — Sentence across languages

## Current evidence

- Structured sentence records keep actor, action, object, and time identities
  stable across English and Uzbek.
- An element morph reorders the same semantic nodes and changes their language
  expressions.
- A two-row contrast preserves both arrangements for direct inspection.
- Morpheme records expose `kitob-ni` and `o‘qi-yap-ti`.
- Sequential semantic state transitions provide a silent reading cue path.
- `check_project` passes with 34 timeline items and no diagnostics.
- One repaired 1905×5823 full-tape PNG was inspected and accepted.

## Engine changes required

None. Unicode text, semantic diagrams, element morphs, addressable state,
rich-text ranges, flex layout, and tape travel cover the current source-only
mute example.

## Authoring and visual findings

- Auto-sized flex cells exaggerated short tokens. Fixed-size semantic token
  nodes produced consistent multilingual typography.
- Stable role colors make reordering visible without implying word-for-word
  equivalence.
- Separate syntax, morphology, reading-path, and variation sections prevent a
  gloss from being mistaken for a natural translation.
- The source demonstrates timed token highlighting but intentionally ships no
  unreviewed audio.

## Honest remaining limitations

- Native-speaker review is still required for final Uzbek wording,
  pronunciation, and any future recording.
- The silent reading path is not phonetic transcription or pronunciation
  instruction.
- Dependency and constituency structure are not shown; the project focuses on
  semantic roles, neutral order, and selected morphology.
- Full-tape acceptance does not replace a final mute-video master.

## Generalizable maturity conclusion

The engine can teach symbolic transformation with stable identities, spatial
reordering, morpheme-level explanation, multilingual Unicode, and timed
semantic cues. Audio synchronization, font-coverage preflight, text-range
addressing, and reusable dependency graphs remain general future abstractions,
not reasons for a language-specific patch.
