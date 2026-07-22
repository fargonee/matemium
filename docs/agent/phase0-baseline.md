# Agent Phase 0 Baseline

**Captured:** 2026-07-18

**Runtime under test:** `legacy-react-v1`

This baseline inventories all known autonomous entry points and records the limitations that the state-machine runtime must improve. It is evidence for migration decisions, not a claim that the legacy runtime is production-ready.

## Entry-point inventory

| Surface | Entry point | Implementation | Behavior today | Target disposition |
|---|---|---|---|---|
| Cloud chat | `POST /chat/completions`, `use_autonomous_agent=true` | `server/matemium_server/routes/chat.py` → `ReActAgentRunner.run_loop_async` | Runs the XML/regex loop and returns its last assistant message | Versioned state-machine run; keep legacy compatibility during rollout |
| Cloud stream | `POST /chat/stream` | Same route → SSE callback → `ReActAgentRunner.run_loop_async` | Streams status, thought, tool call, and output events | Versioned run events with cancel/resume and no private reasoning |
| Desktop cloud chat | `cloud_chat` Tauri command | `desktop/src-tauri/src/commands.rs` → `cloud.rs` | Passes the autonomous opt-in flag to the cloud API | Pass an explicit runtime version and consume run IDs/events |
| Desktop UI | Autonomous setting | `desktop/app/src/App.tsx`, `SettingsScreen.tsx` | Boolean opt-in; no runtime identity | Versioned feature selection with legacy/new labeling |
| Local generation pipeline | `LifecycleCoordinator.run` / `run_lifecycle` | `matemium/agent/coordinator.py` | Fixed Director → Engineer → Critic lifecycle | Reuse domain operations; do not treat as the autonomy state machine |
| Local LLM handlers | `local_director_agent`, `local_engineer_agent` | `matemium/agent/local_agent.py` | Replaces coordinator handlers with local inference | Adapt behind the structured model gateway |
| Pydantic bridge | `PydanticAIAgent.run_sync` | `matemium/agent/pydantic_ai_bridge.py` | Parses a structured final model payload for fixed phases | Reuse validation patterns where compatible |
| MCP lifecycle helpers | `lifecycle_status`, `create_tape_content` | `matemium/mcp_server.py` | Inspects the gated Roadmap and creates bounded tape-content artifacts | Never expose the legacy `run_lifecycle` bypass; production advances through the normative phase state |
| MCP authoring tools | `view_file`, `edit_file`, `compile_manim`, `retrieve` | `matemium/mcp_server.py` | Mixed direct execution and proposed-patch behavior | Normalize behind typed tool results and capability policy |
| Tests/scratch | Direct runner/coordinator calls | `tests/test_react_runner.py`, `tests/test_agent_coordinator.py`, `verification_scratch.py` | Mock loop and lifecycle verification | Retain as legacy regression coverage; add benchmark harness |

## Legacy runtime failure audit

| ID | Failure mode | Repository evidence | User impact | Required mitigation |
|---|---|---|---|---|
| L-01 | Unstructured XML protocol | `react_runner.py::parse_llm_response` uses regex and JSON extraction | Model formatting variations break actions | Provider-native tools plus constrained local adapter |
| L-02 | No-tool response equals completion | Both loops break whenever `tool_name` is absent | False success after malformed or premature replies | Finish proposal followed by verifier-controlled gates |
| L-03 | Full transcript growth | Each generation receives the complete `messages` list | Token/cost growth and eventual context loss | Structured state and source-linked compaction |
| L-04 | Tool failures become prose | Exceptions are converted to `"Error executing tool: ..."` | No reliable recovery classification | Typed result envelope and stable codes |
| L-05 | Prompt-only policy | Inspect-before-edit and compile rules live in the prompt | Models can bypass required safety/validation | Orchestrator policy enforcement |
| L-06 | Compile treated as sufficient | Prompt defines successful compile as completion | Visually or semantically wrong output can pass | Task-specific semantic/render/visual gates |
| L-07 | Last-message objective truncation | Routes set `user_prompt = body.messages[-1].content` | Earlier user constraints disappear | Preserve or deliberately summarize conversation |
| L-08 | Incomplete accounting | Route increments one AI-call counter after a multi-call run | Incorrect cost, credits, and telemetry | Record each provider invocation |
| L-09 | No durable run state | Runner returns an in-memory message list | Crash/restart loses progress; no resume | Durable `AgentRunState` checkpoints |
| L-10 | No cancellation/time budget | Only a turn counter bounds the loop | Long model/render calls cannot be controlled | Cancellation plus independent budgets/timeouts |
| L-11 | No stall signatures | Equivalent actions may repeat until `max_turns` | Wasted calls and poor failure reporting | Action/observation fingerprints and bounded recovery |
| L-12 | One parsed call per response | Parser extracts only the first matching tool block | Inefficient exploration; ambiguous extra calls | Internal multi-call response with write serialization |
| L-13 | Reasoning streamed | `<thought>` content is emitted to clients | Brittle UX and unnecessary private reasoning exposure | Concise action rationales only |
| L-14 | MCP edit is not grounded execution | MCP `edit_file` returns proposed patches with `ok: true` | Callers may mistake proposal for applied mutation | Accurate typed status and mutation evidence |
| L-15 | Tests overfit mocked happy paths | `test_react_runner.py` validates prepared XML sequence | Weak evidence of real task completion | Scenario evaluation suite and false-success measurement |

## Baseline benchmark contract

The machine-readable suite is in:

- `evals/agent/phase0-benchmarks.json`
- `evals/agent/phase0-thresholds.json`

Cases cover generation, localized editing, syntax/import/LaTeX recovery, stale edits, visual false-success, cancellation, resume, stall detection, context compaction, and per-call accounting.

Phase 0 defines the cases and release thresholds. It does not fabricate legacy scores: actual model/provider runs require a later harness, pinned fixtures, and recorded run manifests. Results must state runtime version, model profile, fixture revision, and sample size.

## Runtime version contract

- `legacy-react-v1` identifies the currently executable XML/regex runner.
- `state-machine-v2` is reserved for the target runtime and is rejected until implemented.
- Omitted selectors resolve to `legacy-react-v1` for compatibility.
- Autonomous API responses and the first streaming event identify the resolved runtime.
- Unknown or unavailable runtime selectors fail explicitly; they never silently fall back.

## Phase 0 exit evidence

- Entry points: inventoried above.
- Failure modes: documented above with code locations and mitigations.
- Benchmarks and thresholds: committed as machine-readable JSON.
- Runtime versioning: implemented in `matemium.agent.runtime_version` and exposed by cloud autonomous responses/events.
- Checkpoint decision: recorded in `docs/agent/adr-001-agent-checkpoints.md`.

The dataset is approved for implementation planning by its inclusion in the normative roadmap. Production approval still requires the Phase 9 evaluation review.
