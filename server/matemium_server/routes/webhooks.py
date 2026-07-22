from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/lemonsqueezy")
async def lemon_squeezy_webhook(
    request: Request,
) -> dict[str, bool]:
    _ = await request.body()
    raise HTTPException(
        status_code=410,
        detail="Lemon Squeezy webhooks are disabled because Matemium is free.",
    )
