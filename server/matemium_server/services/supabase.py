"""Supabase Auth verification and profile access for the cloud API."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from ..config import settings


class SupabaseService:
    def __init__(self) -> None:
        self._base = settings.supabase_url.rstrip("/")
        self._anon = settings.supabase_anon_key
        self._service = settings.supabase_service_role_key

    def _auth_configured(self) -> bool:
        return bool(self._base and self._anon)

    def _db_configured(self) -> bool:
        return bool(self._base and self._service)

    async def verify_access_token(self, access_token: str) -> dict[str, Any] | None:
        if not self._auth_configured():
            return None

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self._base}/auth/v1/user",
                headers={
                    "apikey": self._anon,
                    "Authorization": f"Bearer {access_token}",
                },
            )
        if response.status_code != 200:
            return None
        return response.json()

    async def get_profile(self, user_id: str) -> dict[str, Any] | None:
        rows = await self._rest_get("profiles", {"id": f"eq.{user_id}", "select": "*"})
        return rows[0] if rows else None

    async def list_profiles(self, limit: int = 100) -> list[dict[str, Any]]:
        return await self._rest_get(
            "profiles",
            {"select": "*", "order": "created_at.desc", "limit": str(limit)},
        )

    async def list_subscriptions(self, limit: int = 100) -> list[dict[str, Any]]:
        return await self._rest_get(
            "subscriptions",
            {"select": "*", "order": "created_at.desc", "limit": str(limit)},
        )

    async def get_latest_subscription(self, user_id: str) -> dict[str, Any] | None:
        rows = await self._rest_get(
            "subscriptions",
            {
                "user_id": f"eq.{user_id}",
                "select": "status,plan,current_period_end",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    async def count_profiles(self, plan: str | None = None) -> int:
        params: dict[str, str] = {"select": "id"}
        if plan:
            params["plan"] = f"eq.{plan}"
        rows = await self._rest_get("profiles", params)
        return len(rows)

    async def count_subscriptions(self, status: str) -> int:
        rows = await self._rest_get("subscriptions", {"status": f"eq.{status}", "select": "id"})
        return len(rows)

    async def update_profile(self, user_id: str, data: dict[str, Any]) -> None:
        await self._rest_patch("profiles", {"id": f"eq.{user_id}"}, data)

    async def upsert_subscription(self, data: dict[str, Any]) -> None:
        await self._rest_post("subscriptions", data, upsert=True, on_conflict="lemon_subscription_id")

    async def update_subscription_by_lemon_id(
        self, lemon_subscription_id: str, data: dict[str, Any]
    ) -> None:
        await self._rest_patch(
            "subscriptions",
            {"lemon_subscription_id": f"eq.{lemon_subscription_id}"},
            data,
        )

    async def _rest_get(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        if not self._db_configured():
            return []

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self._base}/rest/v1/{table}",
                params=params,
                headers=self._service_headers(),
            )
        if response.status_code != 200:
            return []
        return response.json()

    async def _rest_patch(
        self, table: str, match: dict[str, str], data: dict[str, Any]
    ) -> None:
        if not self._db_configured():
            return

        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.patch(
                f"{self._base}/rest/v1/{table}",
                params=match,
                json=data,
                headers={**self._service_headers(), "Prefer": "return=minimal"},
            )

    async def _rest_post(
        self,
        table: str,
        data: dict[str, Any],
        *,
        upsert: bool = False,
        on_conflict: str | None = None,
    ) -> None:
        if not self._db_configured():
            return

        headers = self._service_headers()
        if upsert:
            prefer = "resolution=merge-duplicates,return=minimal"
            if on_conflict:
                prefer = f"{prefer},on_conflict={on_conflict}"
            headers["Prefer"] = prefer

        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"{self._base}/rest/v1/{table}",
                json=data,
                headers=headers,
            )

    def _service_headers(self) -> dict[str, str]:
        return {
            "apikey": self._service,
            "Authorization": f"Bearer {self._service}",
            "Content-Type": "application/json",
        }


@lru_cache
def get_supabase_service() -> SupabaseService:
    return SupabaseService()