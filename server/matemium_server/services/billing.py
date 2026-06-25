"""Lemon Squeezy checkout, customer portal, and webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx

from ..config import settings
from ..deps import AuthUser
from .supabase import SupabaseService

LEMON_API = "https://api.lemonsqueezy.com/v1"

ACTIVE_STATUSES = {"active", "on_trial"}
INACTIVE_STATUSES = {"cancelled", "expired", "unpaid"}


class BillingService:
    def __init__(self, supabase: SupabaseService) -> None:
        self._supabase = supabase

    def _headers(self) -> dict[str, str]:
        if not settings.lemon_squeezy_api_key:
            raise RuntimeError("MATEMIUM_LEMON_SQUEEZY_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {settings.lemon_squeezy_api_key}",
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
        }

    async def create_checkout_session(self, user: AuthUser) -> str:
        if not settings.lemon_squeezy_store_id:
            raise RuntimeError("MATEMIUM_LEMON_SQUEEZY_STORE_ID is not configured")
        if not settings.lemon_squeezy_variant_pro_monthly:
            raise RuntimeError("MATEMIUM_LEMON_SQUEEZY_VARIANT_PRO_MONTHLY is not configured")

        payload = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_options": {
                        "embed": False,
                        "button_color": "#2d5bff",
                    },
                    "checkout_data": {
                        "email": user.email,
                        "custom": {
                            "supabase_user_id": user.id,
                            "plan": "pro",
                        },
                    },
                    "product_options": {
                        "redirect_url": f"{settings.site_url}/dashboard/billing?checkout=success",
                    },
                    "test_mode": settings.lemon_squeezy_test_mode,
                },
                "relationships": {
                    "store": {
                        "data": {"type": "stores", "id": str(settings.lemon_squeezy_store_id)}
                    },
                    "variant": {
                        "data": {
                            "type": "variants",
                            "id": str(settings.lemon_squeezy_variant_pro_monthly),
                        }
                    },
                },
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{LEMON_API}/checkouts",
                json=payload,
                headers=self._headers(),
            )
        if response.status_code >= 400:
            raise RuntimeError(f"Lemon Squeezy checkout failed: {response.text}")

        data = response.json().get("data", {})
        url = (data.get("attributes") or {}).get("url")
        if not url:
            raise RuntimeError("Lemon Squeezy checkout missing url")
        return url

    async def create_portal_session(self, user: AuthUser) -> str:
        sub = await self._supabase.get_latest_subscription(user.id)
        lemon_sub_id = (sub or {}).get("lemon_subscription_id")
        if not lemon_sub_id:
            raise RuntimeError("No Lemon Squeezy subscription for this user")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{LEMON_API}/subscriptions/{lemon_sub_id}",
                headers=self._headers(),
            )
        if response.status_code >= 400:
            raise RuntimeError("Could not load subscription from Lemon Squeezy")

        attrs = response.json().get("data", {}).get("attributes", {})
        url = (attrs.get("urls") or {}).get("customer_portal")
        if not url:
            raise RuntimeError("Customer portal URL unavailable")
        return url

    async def handle_webhook(self, payload: bytes, signature: str | None) -> None:
        if not settings.lemon_squeezy_webhook_secret:
            raise RuntimeError("MATEMIUM_LEMON_SQUEEZY_WEBHOOK_SECRET is not configured")
        if not signature:
            raise ValueError("Missing X-Signature header")

        expected = hmac.new(
            settings.lemon_squeezy_webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid Lemon Squeezy signature")

        event = json.loads(payload)
        event_name = (event.get("meta") or {}).get("event_name", "")
        custom = (event.get("meta") or {}).get("custom_data") or {}
        data = event.get("data") or {}
        attrs = data.get("attributes") or {}

        if event_name in {
            "subscription_created",
            "subscription_updated",
            "subscription_payment_success",
        }:
            await self._on_subscription_event(data, attrs, custom)
        elif event_name in {"subscription_cancelled", "subscription_expired"}:
            await self._on_subscription_cancelled(data, attrs, custom)

    async def _on_subscription_event(
        self,
        data: dict[str, Any],
        attrs: dict[str, Any],
        custom: dict[str, Any],
    ) -> None:
        user_id = custom.get("supabase_user_id")
        customer_id = attrs.get("customer_id")
        if not user_id and customer_id is not None:
            rows = await self._supabase._rest_get(  # noqa: SLF001
                "profiles",
                {"lemon_customer_id": f"eq.{customer_id}", "select": "id", "limit": "1"},
            )
            if rows:
                user_id = rows[0]["id"]
        if not user_id:
            return

        status = self._map_status(attrs.get("status", "active"))
        plan = "pro" if status in {"active", "trialing"} else "free"
        lemon_sub_id = str(data.get("id", ""))
        variant_id = attrs.get("variant_id")
        renews_at = attrs.get("renews_at")

        await self._supabase.upsert_subscription(
            {
                "user_id": user_id,
                "lemon_subscription_id": lemon_sub_id,
                "lemon_variant_id": str(variant_id) if variant_id else None,
                "status": status,
                "plan": "pro",
                "current_period_end": renews_at,
            }
        )

        profile_update: dict[str, Any] = {"plan": plan}
        if customer_id is not None:
            profile_update["lemon_customer_id"] = str(customer_id)
        await self._supabase.update_profile(user_id, profile_update)

    async def _on_subscription_cancelled(
        self,
        data: dict[str, Any],
        attrs: dict[str, Any],
        custom: dict[str, Any],
    ) -> None:
        user_id = custom.get("supabase_user_id")
        lemon_sub_id = str(data.get("id", ""))

        if lemon_sub_id:
            await self._supabase.update_subscription_by_lemon_id(
                lemon_sub_id, {"status": "canceled"}
            )
        if user_id:
            await self._supabase.update_profile(user_id, {"plan": "free"})

    @staticmethod
    def _map_status(lemon_status: str) -> str:
        if lemon_status == "on_trial":
            return "trialing"
        if lemon_status in ACTIVE_STATUSES:
            return "active"
        if lemon_status == "past_due":
            return "past_due"
        if lemon_status in INACTIVE_STATUSES:
            return "canceled"
        return "incomplete"