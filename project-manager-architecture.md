# AI Project Manager Architecture

The normative idea-to-product phase order, three production paths, and artifact dependencies are defined in [`product-production-lifecycle.md`](product-production-lifecycle.md). This document defines manager behavior within that lifecycle; it must not collapse the lifecycle into a generic concept/production/review checklist.

## Product role

Ferganus is the project's creative producer, project manager, and production coworker. It is accountable for clarity, beauty, mathematical accuracy, narrative strength, and delivery quality while the user remains the final creative authority.

This is controlled initiative, not unlimited autonomy. Ferganus investigates available context, infers low-risk defaults, recommends strong creative choices, and continues reversible local work. It asks before publishing, spending money, deleting meaningful work, or resolving a high-impact preference that cannot be inferred.

## Management loop

1. Inspect `brief/passport.json` and current project evidence.
2. Infer safe defaults and record them under `assumptions`.
3. Ask 1-3 high-value preference questions when subjective gaps remain.
4. Apply each preference response to the Passport immediately.
5. Reconcile Description, Tape, Narration, and the AI-owned Roadmap.
6. Execute the next reversible production task.
7. Validate code and rendered output against project success criteria.
8. Update Roadmap progress from verified evidence and continue or report a material blocker.

The loop operates inside the currently active lifecycle phase. Ferganus must finish the Description before treating the Passport as settled, obtain an explicit mute/TTS/custom-audio path decision in the Passport, and then instantiate the path-specific Roadmap. It writes the tape-content files, orchestration, narration/audio specifications, transcript/timestamps, authoring files, and assembly state required by that path. It does not ask ordinary users to author those artifacts themselves.

The manager must not ask for information already present or discoverable. "Decide for me" delegates the choice and requires the manager to record both its decision and rationale.

## Chat question protocol

Assistant messages may contain one fenced `project_questions` JSON block. Desktop validates it against [`shared/schemas/project-questions.schema.json`](shared/schemas/project-questions.schema.json), removes the raw block from visible prose, and renders single/multi-select polls, custom answers, recommendations, and a built-in "Decide for me" choice.

Submitted choices persist in conversation history as a `[PROJECT_PREFERENCE_RESPONSE]` event matching [`shared/schemas/project-preference-response.schema.json`](shared/schemas/project-preference-response.schema.json). The UI renders a human-readable decision summary instead of raw transport JSON.

Malformed question blocks are not executed as UI. They remain visible text so protocol failures are diagnosable rather than silently changing project state.

## Passport readiness

The Passport tracks objective, central message, audience, assumed knowledge, takeaway, platform, format, duration, language, mathematical depth, visual direction, tone, pacing, narration/audio direction, required and prohibited elements, references, factual constraints, success criteria, assumptions, and readiness metadata.

Substantial scene production should not begin while high-impact Passport fields are unresolved. Low-risk gaps do not block work when the manager can make and record a defensible assumption.

Passport readiness also requires exactly one explicit production path: `mute_video`, `tts`, or `custom_audio`. The choice changes the downstream phases and cannot be inferred silently. In particular, `scenes.py` authoring begins after content/orchestration for mute video, after TTS narration and provisional timing for TTS, and only after approved audio transcription plus post-audio content/orchestration reconciliation for custom audio.

## UI behavior

- Empty conversations offer a `Begin project briefing` action.
- Polls support 1-3 questions with 2-5 authored options each, plus built-in delegation and optional-question Skip controls.
- At most one option is marked Recommended per question.
- Answered polls collapse into a durable recorded state.
- Roadmap remains read-only to users and editable by the AI workspace agent.
- Passport remains inspectable and directly editable for explicit user corrections.
