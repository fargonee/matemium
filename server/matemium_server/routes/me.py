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


class SubscriptionResponse(BaseModel):
    status: str | None = None
    plan: str | None = None
    current_period_end: str | None = None


class AccountResponse(BaseModel):
    profile: MeResponse
    subscription: SubscriptionResponse | None = None


@router.get("/me", response_model=AccountResponse, operation_id="getMe")
async def get_me(
    user: Annotated[AuthUser, Depends(require_user)],
    supabase: SupabaseService = Depends(get_supabase_service),
) -> AccountResponse:
    profile = await supabase.get_profile(user.id)
    sub = await supabase.get_latest_subscription(user.id)

    return AccountResponse(
        profile=MeResponse(
            id=user.id,
            email=user.email,
            full_name=(profile or {}).get("full_name"),
            role=user.role,
            plan=user.plan,
            lemon_customer_id=user.lemon_customer_id,
        ),
        subscription=(
            SubscriptionResponse(
                status=sub.get("status"),
                plan=sub.get("plan"),
                current_period_end=sub.get("current_period_end"),
            )
            if sub
            else None
        ),
    )