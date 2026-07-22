from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import AuthUser, require_user

router = APIRouter(tags=["billing"])


class CheckoutRequest(BaseModel):
    plan_id: str = "pro"


class UrlResponse(BaseModel):
    url: str


@router.post("/billing/checkout", response_model=UrlResponse, operation_id="createCheckout")
async def create_checkout(
    body: CheckoutRequest,
    user: Annotated[AuthUser, Depends(require_user)],
) -> UrlResponse:
    _ = (body, user)
    raise HTTPException(
        status_code=410,
        detail="Matemium is free and no longer offers paid checkout.",
    )


@router.post("/billing/portal", response_model=UrlResponse, operation_id="createPortal")
async def create_portal(
    user: Annotated[AuthUser, Depends(require_user)],
) -> UrlResponse:
    _ = user
    raise HTTPException(
        status_code=410,
        detail="Matemium is free and no longer offers paid billing portals.",
    )
