# Agent Phase 2: Structured Model Gateway

**Implemented:** 2026-07-18

Phase 2 defines one internal structured protocol for cloud and local model families. It does not execute tools or authorize completion.

## Internal response contract

`matemium/agent/model_gateway.py` defines:

- `StructuredModelRequest`: model, full ordered conversation, available tools, and parallel-call policy.
- `StructuredModelResponse`: progress summary, normalized action calls, optional plan revision, optional finish proposal, usage, provider identity, and finish reason.
- `StructuredToolCall`: stable call ID, validated object arguments, tool name, and workspace-mutation classification.
- `PlanRevision` and `FinishProposal`: explicit control objects. A finish proposal is not a completed run.
- `MalformedModelResponse`: typed protocol failure including bounded-attempt metadata.

The gateway requires at least one action, plan revision, or finish proposal. Prose without structured intent is malformed and receives at most one repair attempt by default.

## Cloud providers

OpenAI, Groq, xAI, OpenRouter, Together, and Fireworks use the OpenAI-compatible native function-calling contract already configured by the server. The gateway:

1. sends native JSON-schema tool definitions;
2. preserves every supplied conversation message, including tool results;
3. normalizes multiple native tool calls;
4. models `update_plan` and `finish_task` as reserved structured control calls;
5. rejects undefined tools and non-object arguments;
6. records native usage fields;
7. performs one bounded native-protocol repair by default.

`server/matemium_server/services/llm.py::complete_structured_agent` remains a compatibility helper for tests and old server boundaries. Current desktop external model calls use the user's locally stored OpenRouter key and talk to OpenRouter directly from the device.

## Local models

`LocalStructuredModelGateway` uses the same request and response types. It sends:

- the complete ordered conversation;
- tool definitions and mutation metadata;
- the Pydantic-generated local response schema;
- `AGENT_RESPONSE_JSON_GBNF`, a recursive JSON grammar.

`LocalInferenceRunner.generate_structured_agent` connects this adapter to local inference. Ollama receives its native JSON-schema `format`; llama.cpp receives the recursive GBNF grammar. Both outputs undergo semantic Pydantic validation and at most one repair generation by default.

Markdown wrappers and legacy `<thought>/<tool_call>` XML are not accepted by the v2 protocol. The XML parser remains isolated inside `legacy-react-v1` only for compatibility during migration.

## Multiple-call scheduling contract

`execution_batches` groups adjacent read-only calls for parallel execution and places every workspace-mutating call in its own serial batch. Later execution phases consume these batches; Phase 2 does not run them.

## Contract evidence

Recorded OpenAI-compatible responses are stored at:

`tests/fixtures/agent_model_gateway/openai-compatible-responses.json`

`tests/test_agent_model_gateway.py` verifies:

- all six configured provider families;
- native action, plan, and finish normalization;
- full conversation preservation;
- multiple calls and write serialization;
- schema/grammar delivery to local inference;
- bounded repair and typed malformed failure;
- undefined-tool rejection;
- synchronous and asynchronous transports.

## Activation boundary

The structured gateway is complete, but `state-machine-v2` remains unavailable as an end-user autonomous runtime. Enabling it before tool safety, policy, and verification phases would create a false impression of production autonomy. The legacy route remains explicitly versioned as `legacy-react-v1` until those phases are connected.
