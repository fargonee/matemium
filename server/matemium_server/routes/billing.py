from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import AuthUser, require_user
from ..services.billing import BillingService
from ..services.supabase import SupabaseService, get_supabase_service

router = APIRouter(tags=["billing"])


class CheckoutRequest(BaseModel):
    plan_id: str = "pro"


class UrlResponse(BaseModel):
    url: str


def _billing_service(supabase: SupabaseService = Depends(get_supabase_service)) -> BillingService:
    return BillingService(supabase)


@router.post("/billing/checkout", response_model=UrlResponse, operation_id="createCheckout")
async def create_checkout(
    body: CheckoutRequest,
    user: Annotated[AuthUser, Depends(require_user)],
    billing: BillingService = Depends(_billing_service),
) -> UrlResponse:
    if body.plan_id != "pro":
        raise HTTPException(status_code=400, detail="Unsupported plan")
    try:
        url = await billing.create_checkout_session(user)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return UrlResponse(url=url)


@router.post("/billing/portal", response_model=UrlResponse, operation_id="createPortal")
async def create_portal(
    user: Annotated[AuthUser, Depends(require_user)],
    billing: BillingService = Depends(_billing_service),
) -> UrlResponse:
    try:
        url = await billing.create_portal_session(user)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UrlResponse(url=url)