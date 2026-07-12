from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import settings
from ..deps import AuthUser, require_user
from ..models import ChatCompletionRequest, ChatCompletionResponse
from ..rate_limit import enforce_rate_limit
from ..services.llm import complete_chat
from ..services.llm_management import record_platform_usage
from ..services.supabase import get_supabase_service

router = APIRouter(tags=["chat"])


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    user: Annotated[AuthUser, Depends(require_user)],
) -> ChatCompletionResponse:
    """
    Secure LLM proxy.

    - use_personal_llm=True or user has stored key for llm_provider → BYO (user's key, we only proxy).
    - Otherwise → our platform pool. We log real cost and deduct priced credits.
    """
    await enforce_rate_limit(request, user.id, user.plan)

    use_personal = bool(body.use_personal_llm)
    provider = body.llm_provider

    # Resolve early to know the mode (without exposing key to client)
    supabase = get_supabase_service()
    personal = await supabase.get_user_personal_key(user.id, provider) if use_personal else None
    using_platform = not personal

    if using_platform and not settings.llm_stub:
        if not await supabase.has_sufficient_credits(user.id, 1):
            raise HTTPException(
                status_code=402,
                detail="Insufficient platform credits. Buy more tokens or configure your own LLM keys.",
            )

    response = await complete_chat(
        body,
        user_id=user.id,
        provider=provider,
        use_personal=use_personal,
        model_override=body.model,
    )

    try:
        await supabase.increment_ai_calls(user.id, 1)

        if using_platform and not settings.llm_stub:
            # Try to extract usage if the provider returned it in the (future enhanced) response
            usage_info = getattr(response, "usage", None) or {}
            await record_platform_usage(
                user_id=user.id,
                provider_name=provider or "openai",
                model=response.model,
                call_type="chat",
                prompt_tokens=usage_info.get("prompt_tokens"),
                completion_tokens=usage_info.get("completion_tokens"),
                request_id=getattr(request.state, "request_id", None),
            )
        # else: BYO - no deduction from our pool
    except Exception:
        pass

    return response