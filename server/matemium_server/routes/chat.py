from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ..deps import AuthUser, require_user
from ..models import ChatCompletionRequest, ChatCompletionResponse
from ..rate_limit import enforce_rate_limit
from ..services.llm import complete_chat
from ..services.supabase import SupabaseService, get_supabase_service

router = APIRouter(tags=["chat"])


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    user: Annotated[AuthUser, Depends(require_user)],
) -> ChatCompletionResponse:
    """Proxy chat to LLM; requires valid Supabase bearer token (or dev stub)."""
    # Enforce per-plan rate limits (also populates rate limit headers on state)
    await enforce_rate_limit(request, user.id, user.plan)

    response = await complete_chat(body)

    # Record usage for dashboard visibility (only on successful proxy)
    try:
        supabase: SupabaseService = get_supabase_service()
        await supabase.increment_ai_calls(user.id, 1)
    except Exception:
        # Never fail the user request because of usage counter
        pass

    # Best-effort rate limit headers on success
    rl_headers = getattr(request.state, "rate_limit_headers", {})
    # FastAPI will merge via response if we return a custom response, but simple path is ok
    # Consumers can rely on headers on 429 primarily.
    return response