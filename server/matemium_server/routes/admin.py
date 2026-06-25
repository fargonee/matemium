from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import AuthUser, require_admin
from ..services.supabase import SupabaseService, get_supabase_service

router = APIRouter(tags=["admin"])


class AdminStats(BaseModel):
    total_users: int
    pro_users: int
    active_subscriptions: int


class ProfileRow(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    plan: str
    created_at: str | None = None


class SubscriptionRow(BaseModel):
    id: str
    user_id: str
    lemon_subscription_id: str | None = None
    status: str
    plan: str
    current_period_end: str | None = None


@router.get("/admin/stats", response_model=AdminStats, operation_id="getAdminStats")
async def admin_stats(
    _: Annotated[AuthUser, Depends(require_admin)],
    supabase: SupabaseService = Depends(get_supabase_service),
) -> AdminStats:
    total = await supabase.count_profiles()
    pro = await supabase.count_profiles(plan="pro")
    active = await supabase.count_subscriptions("active")
    return AdminStats(total_users=total, pro_users=pro, active_subscriptions=active)


@router.get("/admin/users", response_model=list[ProfileRow], operation_id="getAdminUsers")
async def admin_users(
    _: Annotated[AuthUser, Depends(require_admin)],
    supabase: SupabaseService = Depends(get_supabase_service),
) -> list[ProfileRow]:
    rows = await supabase.list_profiles()
    return [
        ProfileRow(
            id=row["id"],
            email=row.get("email", ""),
            full_name=row.get("full_name"),
            role=row.get("role", "user"),
            plan=row.get("plan", "free"),
            created_at=row.get("created_at"),
        )
        for row in rows
    ]


@router.get(
    "/admin/subscriptions",
    response_model=list[SubscriptionRow],
    operation_id="getAdminSubscriptions",
)
async def admin_subscriptions(
    _: Annotated[AuthUser, Depends(require_admin)],
    supabase: SupabaseService = Depends(get_supabase_service),
) -> list[SubscriptionRow]:
    rows = await supabase.list_subscriptions()
    return [
        SubscriptionRow(
            id=row["id"],
            user_id=row["user_id"],
            lemon_subscription_id=row.get("lemon_subscription_id"),
            status=row.get("status", "active"),
            plan=row.get("plan", "pro"),
            current_period_end=row.get("current_period_end"),
        )
        for row in rows
    ]