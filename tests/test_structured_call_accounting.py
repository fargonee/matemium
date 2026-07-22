from __future__ import annotations

import asyncio

from matemium.agent.model_gateway import (
    AgentMessage,
    ModelUsage,
    StructuredModelRequest,
    StructuredModelResponse,
    FinishProposal,
)


def request() -> StructuredModelRequest:
    return StructuredModelRequest(
        model="test-model",
        messages=[AgentMessage(role="user", content="test")],
    )


def response() -> StructuredModelResponse:
    return StructuredModelResponse(
        provider_response_id="provider-request",
        model="provider-model",
        finish_proposal=FinishProposal(summary="Ready"),
        usage=ModelUsage(input_tokens=100, output_tokens=20, total_tokens=120),
    )


def test_byo_structured_call_is_recorded_without_credit_charge(monkeypatch) -> None:
    from server.matemium_server.services import llm

    async def resolve(*args, **kwargs):
        return {"mode": "byo_external", "provider": "openrouter", "base_url": "http://unused", "api_key": "secret"}

    async def complete(self, req):
        return response()

    monkeypatch.setattr(llm, "resolve_llm_for_user", resolve)
    monkeypatch.setattr("matemium.agent.model_gateway.StructuredModelGateway.complete", complete)
    result = asyncio.run(llm.complete_structured_agent(request(), user_id="user-1"))
    assert result.call_accounting is not None
    assert result.call_accounting.provider == "openrouter"
    assert result.call_accounting.billing_mode == "byo_external"
    assert result.call_accounting.charged_credits == 0


def test_legacy_personal_resolution_is_reported_as_byo(monkeypatch) -> None:
    from server.matemium_server.services import llm

    async def resolve(*args, **kwargs):
        return {"mode": "byo_external", "provider": "openrouter", "base_url": "http://unused", "api_key": "user-key"}

    async def complete(self, req):
        return response()

    monkeypatch.setattr(llm, "resolve_llm_for_user", resolve)
    monkeypatch.setattr("matemium.agent.model_gateway.StructuredModelGateway.complete", complete)
    result = asyncio.run(
        llm.complete_structured_agent(request(), user_id="user-1", use_personal=True)
    )
    assert result.call_accounting is not None
    assert result.call_accounting.billing_mode == "byo_external"
    assert result.call_accounting.charged_credits == 0
    assert result.call_accounting.cost_usd == 0
