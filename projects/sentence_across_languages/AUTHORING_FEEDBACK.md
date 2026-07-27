# Authoring feedback: sentence across languages

> **Historical evidence:** Recorded against the pre-mutation engine. The current
> engine now provides semantic diagrams, addressable parts, state transitions,
> and morphs. These address structural transformation, but this scene has not
> been reauthored, linguistically reviewed, or visually accepted; timed
> pronunciation/audio remains outside the current engine mutation.

## Current pass

- One event is separated into semantic roles, then packaged in reviewed English and Uzbek examples.
- Uzbek object marking and verb-final order are shown without implying rigid universal order.
- Morpheme data is structured; the scene validates cleanly.

## What the current engine could express

Unicode multilingual text, styled token cards, reordered flex rows, and explanatory narrative work in the
available environment.

## What prevented flagship-quality execution

- Tokens need stable identity across reordering so a transform can preserve role/color/meaning.
- Dependency/constituency edges need a general routed connector/tree abstraction.
- Character/morpheme ranges are not addressable for persistent highlighting.
- Audio clips, time-aligned cues, and pronunciation playheads have no source-level timeline contract.
- Font coverage/fallback and shaping are not validated before render.

The general abstractions are keyed tokens, reorder/morph actions, graphs, text-range styling, timed media
cues, and preflight—not language-specific engine branches.

## Evidence level

Importable and structurally valid. Linguistic wording still needs native-speaker review; token motion,
pronunciation synchronization, font preflight, and production acceptance remain unmet.
