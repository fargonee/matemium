from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from ..deps import AuthUser, require_user
from ..models import ChatCompletionRequest, ChatCompletionResponse
from ..rate_limit import enforce_rate_limit

router = APIRouter(tags=["chat"])


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    user: Annotated[AuthUser, Depends(require_user)],
) -> ChatCompletionResponse:
    """
    Deprecated compatibility endpoint.

    Desktop clients call OpenRouter directly from the user's computer. Matemium
    servers do not proxy external AI model requests or store provider keys.
    """
    await enforce_rate_limit(request, user.id, user.plan)
    _ = body
    raise HTTPException(
        status_code=410,
        detail="Matemium no longer proxies external AI requests. Connect OpenRouter in the desktop app so your computer talks to OpenRouter directly.",
    )


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    body: ChatCompletionRequest,
    user: Annotated[AuthUser, Depends(require_user)],
):
    """Legacy streaming endpoint retained as a non-streaming API boundary."""
    await enforce_rate_limit(request, user.id, user.plan)
    raise HTTPException(
        status_code=410,
        detail=(
            "Streaming chat through Matemium servers is disabled. Use the desktop app's direct OpenRouter connection."
        ),
    )
