# Agent Phase 6: Structured Context and Durable Memory

**Implemented:** 2026-07-18

**Context authority:** Desktop/Tauri

Phase 6 replaces ever-growing transcript replay with a bounded `ContextBundle` assembled from durable run state and source-linked memory.

## Prompt bundle

`desktop/src-tauri/src/agent_context.rs` builds structured context containing:

- run ID and normalized objective;
- acceptance criteria;
- current plan and active step;
- bounded changed-file records;
- bounded latest verification records;
- lossless mandatory memory;
- pinned long-term facts;
- resolved source-linked summaries;
- remaining model, tool, token, cost, time, compile, and render budgets;
- omitted-item count and approximate token size.

The bundle is directly serializable for the Phase 2 structured model request. It does not require replaying the chat/tool transcript.

## Durable memory records

The Phase 1 SQLite database now includes `agent_context_items` with:

- stable item and run IDs;
- event sequence;
- typed kind and resolution;
- source reference;
- bounded summary;
- full raw JSON;
- pinned and compacted flags;
- creation time.

Supported kinds are facts, resolved observations, unresolved diagnostics, pending patches, and verification evidence. Raw items are limited to 1 MiB and summaries to 2 KiB to prevent accidental unbounded storage.

## Compaction rules

Resolved observations enter prompts through their concise source-linked summaries. Compaction marks old resolved records without deleting their raw payload.

Pinned facts are selected before ordinary recent summaries. This preserves early user constraints even in long runs.

Unresolved items are mandatory. In particular:

- unresolved diagnostics include their exact structured error payload;
- pending patches include exact search and replacement text.

They are never silently shortened or replaced by a summary. When explicitly marked resolved, they may leave mandatory prompt context, while their raw record remains reloadable.

## Budget behavior

The engine first assembles objective, plan, budgets, bounded run state, mandatory lossless items, and pinned constraints. If those cannot fit, it returns `MandatoryContextTooLarge` rather than losing required information.

Optional resolved summaries are then added newest-first until `max_prompt_bytes` is reached. The bundle reports how many resolved items were omitted and estimates tokens using a conservative four-bytes-per-token measurement.

## Raw evidence reload

`raw_item(item_id)` retrieves the exact stored record regardless of whether it is compacted or currently included in the prompt. This lets later actions reload precise evidence only when needed.

## Long-run verification

`desktop/src-tauri/tests/agent_context_engine.rs` verifies:

- an early pinned mathematical constraint survives more than 500 resolved observations;
- unresolved diagnostics and pending patch text remain exact;
- compacted raw output remains reloadable;
- resolved diagnostics leave mandatory context but retain raw storage;
- mandatory oversized context fails explicitly;
- prompt size remains bounded while history grows from 20 to 1,000 observations;
- omitted resolved-item counts grow instead of prompt size.

These measurements exercise context growth and fact retention without an LLM.
