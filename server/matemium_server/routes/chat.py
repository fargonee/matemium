from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AuthUser, require_user
from ..models import ChatCompletionRequest, ChatCompletionResponse
from ..services.llm import complete_chat

router = APIRouter(tags=["chat"])


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    user: Annotated[AuthUser, Depends(require_user)],
) -> ChatCompletionResponse:
    """Proxy chat to LLM; requires valid Supabase bearer token (or dev stub)."""
    if user.plan == "free":
        # Free tier: allow chat but could rate-limit in production.
        pass
    return await complete_chat(body)