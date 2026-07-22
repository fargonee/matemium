from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import AuthUser, require_user

router = APIRouter(tags=["settings"])


class LLMSettingsUpdate(BaseModel):
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    tts_provider: str | None = None
    tts_api_key: str | None = None
    tts_voice: str | None = None


@router.patch("/settings/llm", operation_id="updateLLMSettings")
async def update_llm_settings(
    body: LLMSettingsUpdate,
    user: Annotated[AuthUser, Depends(require_user)],
) -> dict:
    """Deprecated. Provider API keys are stored on the user's computer."""
    _ = (body, user)
    raise HTTPException(
        status_code=410,
        detail="Provider keys are stored locally in the Matemium desktop app, not on Matemium servers.",
    )
