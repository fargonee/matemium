# Matemium Flagship Example Library

This file indexes the authoring briefs for the real examples intended to replace the legacy engine-test projects in the desktop Example Library.

Authoring, testing, and any engine work discovered through these projects must follow
[`../REAL_PROJECT_ENGINE_WORKFLOW_PROMPT.md`](../REAL_PROJECT_ENGINE_WORKFLOW_PROMPT.md).

| Subject | Project | Authoring brief | Production status |
| --- | --- | --- | --- |
| Mathematics | Fourier Series: Drawing With Rotating Circles | `fourier_epicycles/brief/description.md` | Preview accepted; final master pending |
| Physics | Why an Orbit Is a Continuous Fall | `orbital_mechanics/brief/description.md` | Preview accepted; final master pending |
| Chemistry | Inside an SN2 Reaction | `sn2_reaction/brief/description.md` | Preview accepted; final master pending |
| Computer Science | What Really Happens During Dijkstra’s Algorithm | `dijkstra_execution/brief/description.md` | Preview accepted; final master pending |
| Engineering | How Feedback Stabilizes a System | `feedback_control/brief/description.md` | Preview accepted; final master pending |
| Economics | How a Supply Shock Moves Through a Market | `supply_shock/brief/description.md` | Preview accepted; final master pending |
| Biology | From DNA to Protein | `dna_to_protein/brief/description.md` | Preview accepted; final master pending |
| History | The Chain Reaction That Began World War I | `wwi_chain_reaction/brief/description.md` | Prototype only |
| Philosophy | The Ship of Theseus as an Argument Map | `ship_of_theseus/brief/description.md` | Prototype only |
| Language Learning | How One Thought Changes Across Languages | `sentence_across_languages/brief/description.md` | Prototype only |
| General Education | How a City Gets Clean Water | `clean_water_system/brief/description.md` | Prototype only |

## Portfolio-wide expectations

Each project must:

- answer one memorable question rather than survey an entire subject;
- create understanding through staged visual reasoning, not decorative motion;
- demonstrate a visual grammar meaningfully different from the other flagships;
- keep domain content in reviewable structured data where practical;
- state simplifications, assumptions, and disputed interpretations;
- remain useful as a source-only bundled project without required video files;
- render deterministically without network access;
- include clean reusable helpers instead of one monolithic scene;
- pass domain-accuracy, narrative, layout, render, and source-readability review;
- produce a website-quality master video and an editable desktop example.

## Authoring order

The initial anchor set is:

1. `dijkstra_execution`
2. `orbital_mechanics`
3. `dna_to_protein`
4. `feedback_control`

This order establishes algorithms, physical reasoning, multiscale biological processes, and engineered feedback before the remaining subjects are authored.

All eleven projects now have a deterministic `helpers.py`, a complete first-pass `scenes.py`, and an
`AUTHORING_FEEDBACK.md` written against the pre-mutation engine. Every scene imported and produced a
zero-error structural DSL during the authoring gate.

They must still not be presented as completed showcases. Mathematics, physics,
chemistry, computer science, engineering, economics, and biology have completed
the authoring and preview-acceptance cycle; the other four remain prototypes.
Final-quality masters and independent domain
sign-off remain separate publication gates for every project. The cross-project
engine conclusions and injection boundaries are in
[`../ENGINE_ABSTRACTION_PLAN.md`](../ENGINE_ABSTRACTION_PLAN.md).
