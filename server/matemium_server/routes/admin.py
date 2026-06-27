from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..config import settings
from ..deps import AuthUser, require_admin
from ..services.llm import scene_authoring_system_prompt
from ..services.llm_management import get_autonomous_status, get_spend_summary
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


class AdminUserDetail(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    plan: str
    lemon_customer_id: str | None = None
    ai_calls_count: int = 0
    created_at: str | None = None
    subscription: SubscriptionRow | None = None


class UpdateUserRequest(BaseModel):
    plan: str | None = None
    role: str | None = None
    ai_calls_count: int | None = None
    llm_credits: int | None = None  # admin can grant/revoke platform tokens


class UpdateSubscriptionRequest(BaseModel):
    status: str | None = None
    plan: str | None = None
    current_period_end: str | None = None
    lemon_subscription_id: str | None = None


class LLMInfo(BaseModel):
    model: str
    api_base: str
    stub: bool
    prompt_loaded: bool
    total_ai_calls: int = 0


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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, description="Search email or name"),
) -> list[ProfileRow]:
    rows = await supabase.list_profiles(limit=limit + offset)  # simple; client filters
    # Basic in-process search + pagination (good enough for admin scale)
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in (r.get("email", "") or "").lower() or ql in (r.get("full_name", "") or "").lower()]
    rows = rows[offset : offset + limit]
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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, description="Search user_id or lemon id"),
) -> list[SubscriptionRow]:
    rows = await supabase.list_subscriptions(limit=limit + offset)
    if q:
        ql = q.lower()
        rows = [
            r
            for r in rows
            if ql in (r.get("user_id", "") or "").lower()
            or ql in (r.get("lemon_subscription_id", "") or "").lower()
        ]
    rows = rows[offset : offset + limit]
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


@router.get("/admin/users/{user_id}", response_model=AdminUserDetail, operation_id="getAdminUser")
async def admin_user_detail(
    user_id: str,
    _: Annotated[AuthUser, Depends(require_admin)],
    supabase: SupabaseService = Depends(get_supabase_service),
) -> AdminUserDetail:
    row = await supabase.get_detailed_user(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    sub = row.get("subscription")
    sub_model = (
        SubscriptionRow(
            id=sub.get("id", ""),
            user_id=sub.get("user_id", user_id),
            lemon_subscription_id=sub.get("lemon_subscription_id"),
            status=sub.get("status", "active"),
            plan=sub.get("plan", "pro"),
            current_period_end=sub.get("current_period_end"),
        )
        if sub
        else None
    )
    return AdminUserDetail(
        id=row["id"],
        email=row.get("email", ""),
        full_name=row.get("full_name"),
        role=row.get("role", "user"),
        plan=row.get("plan", "free"),
        lemon_customer_id=row.get("lemon_customer_id"),
        ai_calls_count=row.get("ai_calls_count", 0),
        created_at=row.get("created_at"),
        subscription=sub_model,
    )


@router.patch("/admin/users/{user_id}", response_model=AdminUserDetail, operation_id="updateAdminUser")
async def update_admin_user(
    user_id: str,
    body: UpdateUserRequest,
    _: Annotated[AuthUser, Depends(require_admin)],
    supabase: SupabaseService = Depends(get_supabase_service),
) -> AdminUserDetail:
    updates: dict = {}
    if body.plan is not None:
        updates["plan"] = body.plan
    if body.role is not None:
        if body.role not in ("user", "admin"):
            raise HTTPException(400, "Invalid role")
        updates["role"] = body.role
    if body.ai_calls_count is not None:
        updates["ai_calls_count"] = max(0, body.ai_calls_count)
        updates["usage_updated_at"] = "now()"

    if body.llm_credits is not None:
        updates["llm_credits"] = max(0, body.llm_credits)

    if updates:
        await supabase.update_profile(user_id, updates)

    # Return fresh detail
    return await admin_user_detail(user_id, _, supabase)  # type: ignore[arg-type]


@router.patch(
    "/admin/subscriptions/{subscription_id}",
    response_model=SubscriptionRow,
    operation_id="updateAdminSubscription",
)
async def update_admin_subscription(
    subscription_id: str,
    body: UpdateSubscriptionRequest,
    _: Annotated[AuthUser, Depends(require_admin)],
    supabase: SupabaseService = Depends(get_supabase_service),
) -> SubscriptionRow:
    updates: dict = {}
    for field in ("status", "plan", "current_period_end", "lemon_subscription_id"):
        val = getattr(body, field)
        if val is not None:
            updates[field] = val

    if updates:
        await supabase.update_subscription(subscription_id, updates)

    rows = await supabase._rest_get("subscriptions", {"id": f"eq.{subscription_id}", "select": "*"})
    if not rows:
        raise HTTPException(404, "Subscription not found")
    row = rows[0]
    return SubscriptionRow(
        id=row["id"],
        user_id=row["user_id"],
        lemon_subscription_id=row.get("lemon_subscription_id"),
        status=row.get("status", "active"),
        plan=row.get("plan", "pro"),
        current_period_end=row.get("current_period_end"),
    )


@router.get("/admin/llm", response_model=LLMInfo, operation_id="getAdminLLM")
async def admin_llm(
    _: Annotated[AuthUser, Depends(require_admin)],
    supabase: SupabaseService = Depends(get_supabase_service),
) -> LLMInfo:
    """Safe view of LLM integration status for admins."""
    total_calls = await supabase.get_total_ai_calls()
    try:
        prompt = scene_authoring_system_prompt()
        prompt_loaded = bool(prompt and len(prompt) > 50)
    except Exception:
        prompt_loaded = False

    return LLMInfo(
        model=settings.llm_model,
        api_base=settings.llm_api_base,
        stub=settings.llm_stub,
        prompt_loaded=prompt_loaded,
        total_ai_calls=total_calls,
    )


# ==================== Advanced LLM Management (our accounts + autonomous) ====================

class PlatformProviderIn(BaseModel):
    name: str
    display_name: str | None = None
    api_base: str
    api_key: str | None = None   # will be stored; admin only
    is_active: bool = True
    monthly_budget_usd: float | None = None
    auto_replenish: bool = False


class PlatformProviderOut(BaseModel):
    id: str
    name: str
    display_name: str | None = None
    api_base: str
    is_active: bool
    monthly_budget_usd: float | None = None
    auto_replenish: bool
    # Never return the actual key
    has_key: bool


@router.get("/admin/llm/providers", response_model=list[PlatformProviderOut])
async def list_platform_providers(
    _: Annotated[AuthUser, Depends(require_admin)],
    supabase: SupabaseService = Depends(get_supabase_service),
):
    rows = await supabase.list_active_platform_providers()
    return [
        PlatformProviderOut(
            id=r["id"],
            name=r["name"],
            display_name=r.get("display_name"),
            api_base=r["api_base"],
            is_active=r.get("is_active", True),
            monthly_budget_usd=r.get("monthly_budget_usd"),
            auto_replenish=r.get("auto_replenish", False),
            has_key=bool(r.get("api_key")),
        )
        for r in rows
    ]


@router.post("/admin/llm/providers", response_model=PlatformProviderOut)
async def create_platform_provider(
    body: PlatformProviderIn,
    _: Annotated[AuthUser, Depends(require_admin)],
    supabase: SupabaseService = Depends(get_supabase_service),
):
    data = body.model_dump()
    # Never return key
    key = data.pop("api_key", None)
    if key:
        data["api_key"] = key  # stored server-side

    await supabase._rest_post("llm_providers", data)
    # return fresh
    created = await supabase.get_platform_provider(body.name)
    return PlatformProviderOut(
        id=created["id"],
        name=created["name"],
        display_name=created.get("display_name"),
        api_base=created["api_base"],
        is_active=created.get("is_active", True),
        monthly_budget_usd=created.get("monthly_budget_usd"),
        auto_replenish=created.get("auto_replenish", False),
        has_key=bool(created.get("api_key")),
    )


@router.get("/admin/llm/spend")
async def get_llm_spend(
    _: Annotated[AuthUser, Depends(require_admin)],
):
    return await get_spend_summary()


@router.get("/admin/llm/autonomous")
async def get_llm_autonomous(
    _: Annotated[AuthUser, Depends(require_admin)],
):
    return await get_autonomous_status()


class MarginUpdate(BaseModel):
    margin: float


@router.patch("/admin/llm/margin")
async def update_margin(
    body: MarginUpdate,
    _: Annotated[AuthUser, Depends(require_admin)],
    supabase: SupabaseService = Depends(get_supabase_service),
):
    await supabase._rest_post("system_settings", {
        "key": "llm_profit_margin",
        "value": body.margin
    }, upsert=True)
    return {"margin": body.margin}