"""Provider-independent structured model protocol for the v2 agent runtime."""

from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


class GatewayError(RuntimeError):
    """Base error for structured model gateway failures."""


class MalformedModelResponse(GatewayError):
    def __init__(self, message: str, *, attempts: int, raw: str | None = None):
        super().__init__(message)
        self.attempts = attempts
        self.raw = raw


class AgentMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_call_id: str | None = None
    name: str | None = None

    @model_validator(mode="after")
    def validate_tool_message(self) -> "AgentMessage":
        if self.role == "tool" and not self.tool_call_id:
            raise ValueError("tool messages require tool_call_id")
        return self


class ToolDefinition(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    input_schema: dict[str, Any]
    mutates_workspace: bool = False


class StructuredToolCall(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any]
    mutates_workspace: bool = False


class PlanRevision(BaseModel):
    steps: list[dict[str, Any]]
    reason: str = Field(min_length=1)


class FinishProposal(BaseModel):
    summary: str = Field(min_length=1)
    claimed_outcomes: list[str] = Field(default_factory=list)
    requested_verification: list[str] = Field(default_factory=list)


class ModelUsage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class CallAccounting(BaseModel):
    provider: str
    model: str
    request_id: str
    billing_mode: Literal["byo_external", "local"]
    latency_ms: int = Field(ge=0)
    cost_usd: float = Field(default=0.0, ge=0)
    charged_credits: int = Field(default=0, ge=0)


class StructuredModelResponse(BaseModel):
    provider_response_id: str | None = None
    model: str | None = None
    progress_summary: str | None = None
    tool_calls: list[StructuredToolCall] = Field(default_factory=list)
    plan_revision: PlanRevision | None = None
    finish_proposal: FinishProposal | None = None
    usage: ModelUsage = Field(default_factory=ModelUsage)
    raw_finish_reason: str | None = None
    call_accounting: CallAccounting | None = None

    @model_validator(mode="after")
    def require_action(self) -> "StructuredModelResponse":
        if not self.tool_calls and self.plan_revision is None and self.finish_proposal is None:
            raise ValueError("structured response must contain a tool call, plan revision, or finish proposal")
        return self


class StructuredModelRequest(BaseModel):
    model: str
    messages: list[AgentMessage]
    tools: list[ToolDefinition] = Field(default_factory=list)
    allow_parallel_tools: bool = True


def _usage(raw: dict[str, Any]) -> ModelUsage:
    return ModelUsage(
        input_tokens=int(raw.get("prompt_tokens", raw.get("input_tokens", 0)) or 0),
        output_tokens=int(raw.get("completion_tokens", raw.get("output_tokens", 0)) or 0),
        total_tokens=int(raw.get("total_tokens", 0) or 0),
    )


def _arguments(value: Any, *, call_id: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        raise MalformedModelResponse(f"tool call {call_id} arguments must be JSON object", attempts=1)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise MalformedModelResponse(
            f"tool call {call_id} has invalid JSON arguments: {exc}", attempts=1, raw=value
        ) from exc
    if not isinstance(parsed, dict):
        raise MalformedModelResponse(f"tool call {call_id} arguments must decode to an object", attempts=1, raw=value)
    return parsed


def parse_openai_compatible_response(
    payload: dict[str, Any], tools: Sequence[ToolDefinition]
) -> StructuredModelResponse:
    """Normalize OpenAI, Groq, xAI, OpenRouter, Together, and Fireworks responses."""
    try:
        choice = payload["choices"][0]
        message = choice["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise MalformedModelResponse("provider response has no choices[0].message", attempts=1) from exc

    definitions = {tool.name: tool for tool in tools}
    actions: list[StructuredToolCall] = []
    plan_revision: PlanRevision | None = None
    finish_proposal: FinishProposal | None = None

    for index, raw_call in enumerate(message.get("tool_calls") or []):
        function = raw_call.get("function") or {}
        name = function.get("name")
        call_id = raw_call.get("id") or f"provider-call-{index}"
        if not name:
            raise MalformedModelResponse(f"tool call {call_id} has no function name", attempts=1)
        arguments = _arguments(function.get("arguments", "{}"), call_id=call_id)
        if name == "update_plan":
            if plan_revision is not None:
                raise MalformedModelResponse("response contains multiple update_plan calls", attempts=1)
            try:
                plan_revision = PlanRevision.model_validate(arguments)
            except ValidationError as exc:
                raise MalformedModelResponse(
                    f"invalid update_plan arguments: {exc}", attempts=1
                ) from exc
        elif name == "finish_task":
            if finish_proposal is not None:
                raise MalformedModelResponse("response contains multiple finish_task calls", attempts=1)
            try:
                finish_proposal = FinishProposal.model_validate(arguments)
            except ValidationError as exc:
                raise MalformedModelResponse(
                    f"invalid finish_task arguments: {exc}", attempts=1
                ) from exc
        else:
            definition = definitions.get(name)
            if definition is None:
                raise MalformedModelResponse(f"model called undefined tool '{name}'", attempts=1)
            actions.append(
                StructuredToolCall(
                    id=call_id,
                    name=name,
                    arguments=arguments,
                    mutates_workspace=definition.mutates_workspace,
                )
            )

    try:
        return StructuredModelResponse(
            provider_response_id=payload.get("id"),
            model=payload.get("model"),
            progress_summary=(message.get("content") or "").strip() or None,
            tool_calls=actions,
            plan_revision=plan_revision,
            finish_proposal=finish_proposal,
            usage=_usage(payload.get("usage") or {}),
            raw_finish_reason=choice.get("finish_reason"),
        )
    except ValidationError as exc:
        raise MalformedModelResponse(f"invalid structured provider response: {exc}", attempts=1) from exc


class LocalResponseEnvelope(BaseModel):
    progress_summary: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    plan_revision: PlanRevision | None = None
    finish_proposal: FinishProposal | None = None


def parse_local_response(
    raw: str,
    tools: Sequence[ToolDefinition],
    *,
    repair_fn: Callable[[str, str, dict[str, Any]], str] | None = None,
    max_repairs: int = 1,
) -> StructuredModelResponse:
    """Parse the schema-constrained local envelope with a bounded repair attempt."""
    definitions = {tool.name: tool for tool in tools}
    candidate = raw.strip()
    attempts = 0
    while True:
        attempts += 1
        try:
            decoded = json.loads(candidate)
            envelope = LocalResponseEnvelope.model_validate(decoded)
            calls: list[StructuredToolCall] = []
            for index, item in enumerate(envelope.tool_calls):
                name = item.get("name")
                call_id = str(item.get("id") or f"local-call-{index}")
                if name not in definitions:
                    raise ValueError(f"local model called undefined tool '{name}'")
                arguments = item.get("arguments", {})
                if not isinstance(arguments, dict):
                    raise ValueError(f"tool call {call_id} arguments must be an object")
                calls.append(
                    StructuredToolCall(
                        id=call_id,
                        name=name,
                        arguments=arguments,
                        mutates_workspace=definitions[name].mutates_workspace,
                    )
                )
            return StructuredModelResponse(
                progress_summary=envelope.progress_summary,
                tool_calls=calls,
                plan_revision=envelope.plan_revision,
                finish_proposal=envelope.finish_proposal,
            )
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            if repair_fn is None or attempts > max_repairs:
                raise MalformedModelResponse(
                    f"local structured response failed after {attempts} attempt(s): {exc}",
                    attempts=attempts,
                    raw=candidate,
                ) from exc
            candidate = repair_fn(candidate, str(exc), LocalResponseEnvelope.model_json_schema()).strip()


def openai_request_payload(request: StructuredModelRequest) -> dict[str, Any]:
    """Build a native function-calling request without discarding conversation history."""
    messages: list[dict[str, Any]] = []
    for message in request.messages:
        item: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.tool_call_id:
            item["tool_call_id"] = message.tool_call_id
        if message.name:
            item["name"] = message.name
        messages.append(item)

    definitions = list(request.tools) + control_tool_definitions()
    return {
        "model": request.model,
        "messages": messages,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            for tool in definitions
        ],
        "tool_choice": "auto",
        "parallel_tool_calls": request.allow_parallel_tools,
    }


def control_tool_definitions() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="update_plan",
            description="Replace or revise the current task plan.",
            input_schema={
                "type": "object",
                "properties": {
                    "steps": {"type": "array", "items": {"type": "object"}},
                    "reason": {"type": "string", "minLength": 1},
                },
                "required": ["steps", "reason"],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="finish_task",
            description="Propose finishing the task. The verifier decides whether completion is allowed.",
            input_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "minLength": 1},
                    "claimed_outcomes": {"type": "array", "items": {"type": "string"}},
                    "requested_verification": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["summary"],
                "additionalProperties": False,
            },
        ),
    ]


def execution_batches(calls: Sequence[StructuredToolCall]) -> list[list[StructuredToolCall]]:
    """Parallelize reads while serializing every workspace mutation."""
    batches: list[list[StructuredToolCall]] = []
    reads: list[StructuredToolCall] = []
    for call in calls:
        if call.mutates_workspace:
            if reads:
                batches.append(reads)
                reads = []
            batches.append([call])
        else:
            reads.append(call)
    if reads:
        batches.append(reads)
    return batches


Transport = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]
LocalTransport = Callable[[str, dict[str, Any], str], str]


class StructuredModelGateway:
    def __init__(self, transport: Transport, *, max_repairs: int = 1):
        self.transport = transport
        self.max_repairs = max_repairs

    async def complete(self, request: StructuredModelRequest) -> StructuredModelResponse:
        payload = openai_request_payload(request)
        attempts = 0
        while True:
            attempts += 1
            raw = self.transport(payload)
            if inspect.isawaitable(raw):
                raw = await raw
            try:
                return parse_openai_compatible_response(raw, request.tools)
            except (MalformedModelResponse, ValidationError) as exc:
                if attempts > self.max_repairs:
                    raise MalformedModelResponse(
                        f"native structured response failed after {attempts} attempt(s): {exc}",
                        attempts=attempts,
                    ) from exc
                payload = dict(payload)
                payload["messages"] = list(payload["messages"]) + [
                    {
                        "role": "system",
                        "content": (
                            "The previous response violated the structured tool protocol: "
                            f"{exc}. Return only valid native tool calls using the supplied schemas."
                        ),
                    }
                ]


def local_request_prompt(request: StructuredModelRequest) -> str:
    """Build a lossless local-model prompt for the structured envelope."""
    conversation = [message.model_dump(exclude_none=True) for message in request.messages]
    tools = [tool.model_dump() for tool in request.tools]
    return (
        "Return exactly one JSON object matching the supplied response schema. "
        "Do not use markdown or XML. Use tool_calls for actions, plan_revision to revise "
        "the plan, or finish_proposal to request verification. A finish proposal is not success.\n\n"
        f"Conversation:\n{json.dumps(conversation, ensure_ascii=False)}\n\n"
        f"Available tools:\n{json.dumps(tools, ensure_ascii=False)}"
    )


class LocalStructuredModelGateway:
    """Schema/grammar-constrained adapter for GGUF and local chat runtimes."""

    def __init__(self, transport: LocalTransport, *, max_repairs: int = 1):
        self.transport = transport
        self.max_repairs = max_repairs

    def complete(self, request: StructuredModelRequest) -> StructuredModelResponse:
        from .grammars import AGENT_RESPONSE_JSON_GBNF

        schema = LocalResponseEnvelope.model_json_schema()
        prompt = local_request_prompt(request)
        raw = self.transport(prompt, schema, AGENT_RESPONSE_JSON_GBNF)

        def repair(candidate: str, error: str, repair_schema: dict[str, Any]) -> str:
            repair_prompt = (
                f"{prompt}\n\nYour previous response was invalid:\n{candidate}\n\n"
                f"Validation error:\n{error}\nReturn one corrected JSON object only."
            )
            return self.transport(repair_prompt, repair_schema, AGENT_RESPONSE_JSON_GBNF)

        return parse_local_response(
            raw,
            request.tools,
            repair_fn=repair if self.max_repairs else None,
            max_repairs=self.max_repairs,
        )
