from __future__ import annotations

import json
import asyncio
from pathlib import Path

import pytest

from matemium.agent.model_gateway import (
    AgentMessage,
    MalformedModelResponse,
    StructuredModelGateway,
    LocalStructuredModelGateway,
    StructuredModelRequest,
    ToolDefinition,
    execution_batches,
    local_request_prompt,
    openai_request_payload,
    parse_local_response,
    parse_openai_compatible_response,
)


FIXTURE = Path(__file__).parent / "fixtures" / "agent_model_gateway" / "openai-compatible-responses.json"


@pytest.fixture
def tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="read_file",
            description="Read a file",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        ),
        ToolDefinition(
            name="search_workspace",
            description="Search workspace",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        ToolDefinition(
            name="edit_file",
            description="Edit a file",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            mutates_workspace=True,
        ),
    ]


def recorded() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("family", recorded()["families"])
def test_supported_openai_compatible_family_contract(family: str, tools: list[ToolDefinition]) -> None:
    # These providers expose the same native chat-completions tool-call contract.
    response = parse_openai_compatible_response(recorded()["tool_response"], tools)
    assert family
    assert [call.name for call in response.tool_calls] == ["read_file", "search_workspace"]
    assert response.usage.total_tokens == 150


def test_control_calls_normalize_plan_and_finish(tools: list[ToolDefinition]) -> None:
    plan = parse_openai_compatible_response(recorded()["plan_response"], tools)
    finish = parse_openai_compatible_response(recorded()["finish_response"], tools)
    assert plan.plan_revision is not None
    assert plan.plan_revision.reason == "Workspace inspection completed"
    assert finish.finish_proposal is not None
    assert finish.finish_proposal.requested_verification == ["project_check"]
    assert finish.tool_calls == []


def test_request_preserves_full_conversation_and_uses_native_tools(tools: list[ToolDefinition]) -> None:
    request = StructuredModelRequest(
        model="test-model",
        messages=[
            AgentMessage(role="system", content="system"),
            AgentMessage(role="user", content="first constraint"),
            AgentMessage(role="assistant", content="progress"),
            AgentMessage(role="tool", content="result", tool_call_id="old-call", name="read_file"),
            AgentMessage(role="user", content="latest request"),
        ],
        tools=tools,
    )
    payload = openai_request_payload(request)
    assert [message["content"] for message in payload["messages"]] == [
        "system", "first constraint", "progress", "result", "latest request"
    ]
    assert payload["messages"][3]["tool_call_id"] == "old-call"
    names = [item["function"]["name"] for item in payload["tools"]]
    assert names == ["read_file", "search_workspace", "edit_file", "update_plan", "finish_task"]
    assert payload["parallel_tool_calls"] is True


def test_multiple_reads_parallelize_but_writes_are_serialized(tools: list[ToolDefinition]) -> None:
    local = parse_local_response(
        json.dumps(
            {
                "tool_calls": [
                    {"id": "r1", "name": "read_file", "arguments": {"path": "scenes.py"}},
                    {"id": "r2", "name": "search_workspace", "arguments": {"query": "intro"}},
                    {"id": "w1", "name": "edit_file", "arguments": {"path": "scenes.py"}},
                    {"id": "r3", "name": "read_file", "arguments": {"path": "assets.py"}}
                ]
            }
        ),
        tools,
    )
    batches = execution_batches(local.tool_calls)
    assert [[call.id for call in batch] for batch in batches] == [["r1", "r2"], ["w1"], ["r3"]]


def test_local_adapter_repairs_once_then_validates(tools: list[ToolDefinition]) -> None:
    repairs = 0

    def repair(raw: str, error: str, schema: dict) -> str:
        nonlocal repairs
        repairs += 1
        assert raw == "not-json"
        assert error
        assert schema["type"] == "object"
        return json.dumps({"finish_proposal": {"summary": "Ready for verification"}})

    response = parse_local_response("not-json", tools, repair_fn=repair, max_repairs=1)
    assert repairs == 1
    assert response.finish_proposal is not None


def test_local_adapter_has_bounded_malformed_response_failure(tools: list[ToolDefinition]) -> None:
    def bad_repair(raw: str, error: str, schema: dict) -> str:
        return "still-not-json"

    with pytest.raises(MalformedModelResponse) as caught:
        parse_local_response("not-json", tools, repair_fn=bad_repair, max_repairs=1)
    assert caught.value.attempts == 2


def test_local_gateway_receives_schema_grammar_and_full_history(tools: list[ToolDefinition]) -> None:
    calls: list[tuple[str, dict, str]] = []

    def transport(prompt: str, schema: dict, grammar: str) -> str:
        calls.append((prompt, schema, grammar))
        return json.dumps({"finish_proposal": {"summary": "Ready for verification"}})

    request = StructuredModelRequest(
        model="local-gguf",
        messages=[
            AgentMessage(role="user", content="earlier constraint"),
            AgentMessage(role="assistant", content="progress"),
            AgentMessage(role="user", content="latest request"),
        ],
        tools=tools,
    )
    result = LocalStructuredModelGateway(transport).complete(request)
    prompt, schema, grammar = calls[0]
    assert "earlier constraint" in prompt and "latest request" in prompt
    assert schema["type"] == "object"
    assert "root" in grammar and "object" in grammar
    assert result.finish_proposal is not None


def test_undefined_tool_is_rejected(tools: list[ToolDefinition]) -> None:
    payload = recorded()["tool_response"]
    payload["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = "run_shell"
    with pytest.raises(MalformedModelResponse, match="undefined tool"):
        parse_openai_compatible_response(payload, tools)


def test_async_gateway_normalizes_transport_response(tools: list[ToolDefinition]) -> None:
    captured: dict = {}

    async def transport(payload: dict) -> dict:
        captured.update(payload)
        return recorded()["finish_response"]

    request = StructuredModelRequest(
        model="test-model",
        messages=[AgentMessage(role="user", content="Keep the earlier conversation")],
        tools=tools,
    )
    result = asyncio.run(StructuredModelGateway(transport).complete(request))
    assert captured["messages"][0]["content"] == "Keep the earlier conversation"
    assert result.finish_proposal is not None


def test_native_gateway_repairs_once_and_is_bounded(tools: list[ToolDefinition]) -> None:
    calls = 0

    async def transport(payload: dict) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"choices": [{"message": {"content": "premature prose"}}]}
        assert "violated the structured tool protocol" in payload["messages"][-1]["content"]
        return recorded()["finish_response"]

    request = StructuredModelRequest(
        model="test-model",
        messages=[AgentMessage(role="user", content="Do the task")],
        tools=tools,
    )
    result = asyncio.run(StructuredModelGateway(transport, max_repairs=1).complete(request))
    assert calls == 2
    assert result.finish_proposal is not None
