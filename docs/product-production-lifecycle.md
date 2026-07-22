# Matemium AI-Led Production Lifecycle

**Status:** Normative product and AI-experience specification

**Last updated:** 2026-07-22

**Audience:** Product, desktop, agent-runtime, prompt, workspace, rendering, audio, and brief-system contributors

This document defines how a Matemium project must progress from a user's idea to a finished product. It is the source of truth for production phases, phase-specific brief artifacts, the three production paths, and the division of responsibility between the user and the AI.

## 1. Product premise

Most Matemium users are idea owners, not animation engineers. The user supplies the idea, preferences, corrections, and final creative authority. The AI is the active creative producer and production coworker: it discovers intent, recommends choices, writes and maintains project artifacts, authors the animation, renders it, diagnoses failures, and carries the project to delivery.

The default experience must not require the user to know what belongs in a brief, how to design a Manim scene, or how to edit `scenes.py`. `scenes.py`, `helpers.py`, raw Markdown, JSON, timestamp files, and detailed audio controls remain accessible to advanced users, but they are implementation and advanced-editing surfaces—not prerequisites for ordinary users.

The AI must therefore guide the user through conversation, short questions, concrete alternatives, and polls. It should infer low-risk defaults, explain consequential choices in plain language, and fill or revise project files itself. It must not merely tell the user what to do next.

## 2. Phases are product gates

A phase is a meaningful production commitment with a durable artifact and an observable state. It is not a cosmetic checklist item or an internal chain-of-thought label.

For every phase, the AI must:

1. inspect all approved upstream decisions and current project evidence;
2. identify only the uncertainties that matter to this phase;
3. guide the user with focused conversation or polls, while offering a recommendation and a `Decide for me` route;
4. create or update the phase's artifacts itself;
5. present a human-readable summary or preview for correction;
6. record approval, assumptions, open issues, and evidence in the AI-owned Roadmap; and
7. advance only when the phase is sufficiently settled for the next commitment.

Approval need not be a bureaucratic modal for every edit. Natural-language agreement, an accepted recommendation, or `Decide for me` can settle a decision. However, the production-path choice in Phase 2 must be explicit because it changes the remainder of the project.

Approved upstream decisions are stable project memory. The AI must not repeatedly reopen them without new conflicting evidence or a user-requested change. If an upstream decision changes, it must identify and reconcile every affected downstream artifact.

## 3. Shared foundation

All projects begin with the following phases.

### Phase 0 — Project creation

Create the project identity and workspace. This is the shell in which durable creative and production state will live. A title or initial one-sentence idea is enough to begin; the user must not be forced to complete a large form during creation.

**Exit condition:** a valid project exists and the user's initial idea is preserved.

### Phase 1 — Project description

Turn the initial idea into a clear, human-readable description through back-and-forth collaboration. The AI should help the user articulate what the product is, what it should communicate or teach, and why it matters. Users may type the description manually, but manual specification is optional.

The description is intentionally rare-changing. It is the durable conceptual anchor, not a scratchpad for implementation details, shot timing, or code.

**Primary artifact:** `brief/description.md`

**Exit condition:** the user and AI share a stable understanding of the intended product.

### Phase 2 — Passport and production-path decision

Translate the description into a production-ready Passport. Through questions, polls, recommendations, and safe assumptions, resolve the audience, assumed knowledge, central message, takeaway, platform, orientation, duration, language, mathematical depth, visual direction, tone, pacing, constraints, success criteria, and audio direction.

The Passport must also record exactly one production path:

1. **Mute video** — Matemium produces a finished animation without a final audio track because the user intends to add or edit audio independently.
2. **End-to-end with TTS** — Matemium plans narration and timing, authors and validates the animation, generates TTS, and combines it with the video.
3. **End-to-end with custom audio** — Matemium specifies and generates an audio performance through external services, validates its transcript and timing, then adapts and authors the visuals against that approved audio.

This selection is a hard branch. The AI must explain the consequences, obtain an explicit selection or explicit delegation, persist it in the Passport, and instantiate the matching Roadmap. It must not begin substantial content or scene production with this decision unresolved.

**Primary artifact:** `brief/passport.json`

**Exit condition:** the Passport is production-ready and exactly one production path has been selected.

## 4. Shared content design after the Passport

Every production path next separates **what appears on the mathematical reasoning sheet** from **how the complete visual production is staged**.

### Tape-content phase

The AI collaborates with the user to write one or more Markdown files containing the actual content that appears on the tapes: mathematical statements, reasoning steps, equations, labels, diagrams, examples, conclusions, and intentional holds or reveals. These files describe what the viewer must see on a plain mathematical reasoning sheet. They must not be overloaded with camera direction, 3D-world choreography, or implementation code.

This is a separate and important phase because once the on-tape reasoning is correct and approved, later visual production becomes substantially more mechanical. Multiple tape-content files are allowed and preferred when the project has distinct tapes, chapters, or reasoning tracks.

**Primary artifacts:** `brief/tapes/*.md`

**Exit condition:** the visible mathematical/narrative content is complete, ordered, accurate, and approved independently of animation mechanics.

### Orchestration phase

The AI writes a separate orchestration document describing how the whole production works together: the 3D world, tape placement and transitions, camera movements, reveals, transformations, supporting visuals, focus, pacing intent, and relationships among tapes.

Orchestration may refer to tape content by stable section or beat identifiers, but it must not become a duplicate copy of that content. Likewise, tape-content files must remain understandable without scene code.

**Primary artifact:** `brief/orchestration.md`

**Exit condition:** every content beat has a coherent visual treatment and the overall visual journey is settled enough for the selected production path.

## 5. Path A — Mute video

The mute path is deliberately shorter because the user will handle audio independently.

1. Complete and approve the tape-content phase.
2. Complete and approve the orchestration phase.
3. **Authoring phase:** create `scenes.py` and, when useful, `helpers.py` from the approved Description, Passport, tape content, and orchestration. Ordinary users are not expected to edit these files.
4. **Render and visual-repair phase:** render the animation, inspect actual visual evidence, and fix unexpected layout, camera, animation, mathematical, timing, or rendering behavior. Repeat until the applicable completion gates pass.
5. Deliver the validated mute video for the user's own audio editing.

The Roadmap must not create narration, TTS generation, transcription, or audio-mux phases for this path unless the user later changes the Passport's production path.

## 6. Path B — End-to-end with TTS

The TTS path plans speech and provisional timing before authoring, but generates the final audio only after the rendered animation has been validated and timing has received a final regulation pass.

1. Complete and approve the tape-content phase.
2. Complete and approve the orchestration phase.
3. **TTS narration phase:** write `brief/tts-narration.md` in delivery order, aligned to stable content/orchestration beat identifiers. Wording, pronunciation, emphasis, pauses, holds, and intended timing must be deliberate.
4. When voice treatment cannot be expressed adequately in the narration file, create `brief/tts-narration-style.md` describing voice, tone, energy, pace, pronunciation conventions, and provider-supported performance controls.
5. Establish well-reasoned provisional timestamps. They must constrain scene pacing early enough to prevent animations from becoming implausibly fast or unnecessarily slow.
6. **Authoring phase:** create `scenes.py` and, when useful, `helpers.py` from all approved artifacts.
7. **Render and visual-repair phase:** render the animation, inspect the output, and repair unexpected visual, mathematical, camera, animation, or pacing behavior.
8. **Final timing-regulation phase:** make a focused final adjustment to timestamps in the authoring files and `brief/tts-narration.md` before calling a TTS service. This is a distinct, smaller phase and must account for the actual validated render rather than only initial estimates.
9. **TTS generation phase:** generate the audio from the final narration, applying `brief/tts-narration-style.md` where the selected provider supports it. Preserve the generated audio as a managed project asset and record provider/result metadata needed for reproducibility.
10. **Final assembly phase:** combine the approved TTS audio with the approved animation using FFmpeg without avoidable quality loss. Prefer stream-copying the already approved video when container/codec compatibility permits; do not re-render or re-encode the video merely to attach audio.

The phase order above is intentional. Calling paid or external TTS before final timing regulation risks needless regeneration; ignoring speech timing until after authoring risks unusably rushed or slow animation.

## 7. Path C — End-to-end with custom audio

The custom-audio path becomes audio-first after its initial content and orchestration drafts. The approved, freshly transcribed audio is the timing authority for final visual planning and authoring.

1. Complete the initial tape-content phase.
2. Complete the initial orchestration phase.
3. **Audio specification phase:** create an audio description and narration with strict instructions for performance, holds, silence, emphasis, pronunciation, and pace. These must be suitable for the selected external audio-generation service rather than vague creative notes.
   - Primary artifacts: `brief/audio-description.md` and `brief/custom-narration.md`.
4. **Audio generation phase:** generate the audio through the configured external API or tool according to those approved files. Store each candidate as a managed asset with enough metadata to distinguish attempts.
5. **Transcription and validation phase:** use an external transcription/alignment tool to extract a fresh transcript and timestamps from the generated audio. Check the actual wording, omissions, pronunciations, holds, pace, timing, and overall result against the audio specification and narration.
6. If the result is not acceptable, revise the appropriate audio artifact and regenerate. Repeat generation, transcription, and validation until the audio meets expectations. A requested script is not proof of what the audio actually contains; the latest verified transcript and timestamps are authoritative.
7. **Post-audio content reconciliation phase:** recheck and edit the tape-content files and `brief/orchestration.md` against the approved transcript's exact wording and fresh timing. Prefer adapting visuals when this preserves the accepted audio: holding an animation, accelerating a feasible visual, or adding a cheap supporting visual is normally less expensive than regenerating already acceptable audio.
8. **Authoring phase:** only now create `scenes.py` and, when useful, `helpers.py` from the approved audio, latest transcript/timestamps, reconciled tape content, orchestration, Passport, and Description.
9. **Render and visual-repair phase:** render against the approved audio timing, inspect actual output, and fix mathematical, layout, camera, animation, synchronization, or rendering defects until completion gates pass.
10. **Final assembly phase:** combine the approved custom audio with the approved animation without avoidable video-quality loss.

Suggested durable outputs for the transcription phase are `brief/transcript.md` and a machine-readable timestamp/alignment file such as `brief/timestamps.json`. Whatever exact schema is implemented, the workspace and Roadmap must identify one latest approved transcript/timestamp pair; stale attempts must never silently drive authoring.

## 8. Artifact dependency and change policy

The dependency direction is:

```text
Project creation
  -> Description
  -> Passport + production path
  -> Tape content
  -> Orchestration
  -> path-specific narration/audio/timing
  -> scenes.py + helpers.py
  -> render evidence and repair
  -> final audio/video assembly where applicable
```

The custom-audio path intentionally adds a feedback edge from the verified transcript/timestamps back to tape content and orchestration before authoring.

When an artifact changes, the AI must mark affected downstream phases as needing reconciliation rather than pretending they remain verified. Not every wording correction requires restarting the entire project: the agent should invalidate only what the change can materially affect and retain still-valid work.

## 9. Roadmap and user experience requirements

`brief/roadmap.json` is the AI-owned, human-readable projection of this lifecycle. Its phases must be derived from the production path, not from a universal three-item `concept / production / review` checklist.

The workspace must show the current phase, what decision or evidence is needed, completed approvals, and any invalidated downstream phase. The AI should speak in user-facing creative language; internal filenames and phase IDs should be shown only when useful or requested.

The AI must continue safe, reversible work within the active phase. It should pause for user input only when a consequential subjective decision cannot be inferred, a phase approval is genuinely required, an external service needs authority or configuration, or completion is blocked.

External generation and transcription may cost money, consume quotas, or transmit project material. Existing permission, provider, privacy, and accounting rules still apply; this lifecycle does not grant silent authority to spend or publish.

## 10. Completion definition

A project is complete only when the selected path's phases have passed their applicable gates:

- **Mute video:** approved content and orchestration, verified authoring code, and a visually validated mute render.
- **TTS:** all mute-video requirements plus final regulated narration/timing, generated and approved TTS, and quality-preserving final assembly.
- **Custom audio:** approved generated audio, verified fresh transcript/timestamps, post-audio visual reconciliation, visually and synchronously validated render, and quality-preserving final assembly.

Possessing `scenes.py`, obtaining a successful compile, generating an audio file, or producing an FFmpeg output is never sufficient by itself. Matemium finishes when the selected product has been verified as the product the user and AI agreed to make.

## 11. Authority and related specifications

This document is authoritative for the product lifecycle and phase ordering. [`project-manager-architecture.md`](../project-manager-architecture.md) defines the manager's questioning and ownership behavior. [`agentic_ai_goal.md`](../agentic_ai_goal.md) defines runtime execution and verification guarantees. [`ai-agent-architecture.md`](../ai-agent-architecture.md) defines tool and workspace boundaries. [`desktop-architecture.md`](../desktop-architecture.md) defines how the lifecycle and artifacts appear in the desktop product.

If an older template, prompt, allow-list, schema, or three-phase Roadmap conflicts with this lifecycle, that component is legacy and must be migrated; it does not override this specification.
