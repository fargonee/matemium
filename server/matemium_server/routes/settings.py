from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import AuthUser, require_user
from ..services.supabase import SupabaseService, get_supabase_service

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
    supabase: SupabaseService = Depends(get_supabase_service),
) -> dict:
    """Allow authenticated user to configure their own LLM / TTS credentials (BYO).

    Keys are stored (encrypt in production).
    """
    data = body.model_dump(exclude_unset=True)
    if data:
        await supabase.set_user_llm_config(user.id, data)
    return {"ok": True, "updated": list(data.keys())}