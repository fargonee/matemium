from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import AuthUser, require_user
from ..services.supabase import SupabaseService, get_supabase_service

router = APIRouter(tags=["account"])


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    plan: str
    lemon_customer_id: str | None = None
    # Deprecated compatibility field. Matemium no longer sells credits.
    llm_credits: int = 0
    llm_provider: str | None = None
    has_own_llm_key: bool = False
    tts_provider: str | None = None
    has_own_tts_key: bool = False


class SubscriptionResponse(BaseModel):
    status: str | None = None
    plan: str | None = None
    current_period_end: str | None = None


class UsageResponse(BaseModel):
    ai_calls_count: int = 0


class AccountResponse(BaseModel):
    profile: MeResponse
    subscription: SubscriptionResponse | None = None
    usage: UsageResponse | None = None


@router.get("/me", response_model=AccountResponse, operation_id="getMe")
async def get_me(
    user: Annotated[AuthUser, Depends(require_user)],
    supabase: SupabaseService = Depends(get_supabase_service),
) -> AccountResponse:
    profile = await supabase.get_profile(user.id)
    ai_calls = await supabase.get_ai_calls_count(user.id)
    llm_cfg = await supabase.get_user_llm_config(user.id)

    return AccountResponse(
        profile=MeResponse(
            id=user.id,
            email=user.email,
            full_name=(profile or {}).get("full_name"),
            role=user.role,
            plan=user.plan,
            lemon_customer_id=user.lemon_customer_id,
            llm_credits=llm_cfg.get("llm_credits", 0),
            llm_provider=llm_cfg.get("llm_provider"),
            has_own_llm_key=False,
            tts_provider=llm_cfg.get("tts_provider"),
            has_own_tts_key=False,
        ),
        subscription=None,
        usage=UsageResponse(ai_calls_count=ai_calls),
    )
