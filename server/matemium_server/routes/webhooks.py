from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..services.billing import BillingService
from ..services.supabase import SupabaseService, get_supabase_service

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/lemonsqueezy")
async def lemon_squeezy_webhook(request: Request) -> dict[str, bool]:
    payload = await request.body()
    signature = request.headers.get("x-signature")
    billing = BillingService(get_supabase_service())

    try:
        await billing.handle_webhook(payload, signature)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"received": True}