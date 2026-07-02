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

    async def get_detailed_user(self, user_id: str) -> dict[str, Any] | None:
        """Return profile + latest subscription + usage for admin detail views."""
        profile = await self.get_profile(user_id)
        if not profile:
            return None
        sub = await self.get_latest_subscription(user_id)
        ai_calls = await self.get_ai_calls_count(user_id)
        profile["ai_calls_count"] = ai_calls
        profile["subscription"] = sub
        return profile

    async def update_subscription(self, subscription_id: str, data: dict[str, Any]) -> None:
        await self._rest_patch("subscriptions", {"id": f"eq.{subscription_id}"}, data)

    async def get_total_ai_calls(self) -> int:
        rows = await self._rest_get("profiles", {"select": "ai_calls_count"})
        return sum(int(r.get("ai_calls_count") or 0) for r in rows)

    # === User LLM / TTS config + platform credits (BYO keys vs platform tokens) ===

    async def get_user_llm_config(self, user_id: str) -> dict[str, Any]:
        rows = await self._rest_get(
            "profiles",
            {
                "id": f"eq.{user_id}",
                "select": "llm_provider,llm_api_key,llm_model,llm_credits,tts_provider,tts_api_key,tts_voice",
            },
        )
        if not rows:
            return {
                "llm_provider": "openai",
                "llm_api_key": None,
                "llm_model": None,
                "llm_credits": 0,
                "tts_provider": "openai",
                "tts_api_key": None,
                "tts_voice": "alloy",
            }
        return rows[0]

    async def get_user_personal_key(self, user_id: str, provider: str | None, for_tts: bool = False) -> dict[str, Any] | None:
        """Return the user's stored personal key/config for a provider, or None."""
        cfg = await self.get_user_llm_config(user_id)
        key_field = "tts_api_key" if for_tts else "llm_api_key"
        prov_field = "tts_provider" if for_tts else "llm_provider"
        if cfg.get(key_field):
            return {
                "provider": cfg.get(prov_field) or provider or "openai",
                "api_key": cfg.get(key_field),
                "model": cfg.get("llm_model") if not for_tts else None,
            }
        return None

    async def set_user_llm_config(self, user_id: str, data: dict[str, Any]) -> None:
        # Only update the provided keys. Never return keys back to client.
        safe_data = {k: v for k, v in data.items() if k in {
            "llm_provider", "llm_model", "tts_provider", "tts_voice"
        } or k.endswith("_api_key")}
        if safe_data:
            await self.update_profile(user_id, safe_data)

    async def adjust_llm_credits(self, user_id: str, delta: int) -> int:
        """Atomically-ish adjust credits. Returns new balance (best effort)."""
        current = await self.get_user_llm_config(user_id)
        new_balance = max(0, int(current.get("llm_credits") or 0) + delta)
        await self.update_profile(user_id, {"llm_credits": new_balance})
        return new_balance

    async def has_sufficient_credits(self, user_id: str, required: int = 1) -> bool:
        cfg = await self.get_user_llm_config(user_id)
        return int(cfg.get("llm_credits") or 0) >= required

    # === Platform (our) LLM provider management ===

    async def list_active_platform_providers(self) -> list[dict[str, Any]]:
        return await self._rest_get(
            "llm_providers",
            {"is_active": "eq.true", "select": "*", "order": "priority.asc"},
        )

    async def get_platform_provider(self, name: str) -> dict[str, Any] | None:
        rows = await self._rest_get(
            "llm_providers",
            {"name": f"eq.{name}", "select": "*", "limit": "1"},
        )
        return rows[0] if rows else None

    async def pick_best_platform_provider(self, preferred_name: str | None = None) -> dict[str, Any] | None:
        if preferred_name:
            p = await self.get_platform_provider(preferred_name)
            if p and p.get("is_active"):
                return p
        providers = await self.list_active_platform_providers()
        return providers[0] if providers else None

    async def log_llm_usage(self, data: dict[str, Any]) -> None:
        """Insert detailed usage + cost log."""
        await self._rest_post("llm_usages", data)

    async def upsert_subscription(self, data: dict[str, Any]) -> None:
        await self._rest_post("subscriptions", data, upsert=True, on_conflict="lemon_subscription_id")

    async def upsert_profile(self, data: dict[str, Any]) -> None:
        """Idempotent insert/update of a minimal profile row (used as backfill)."""
        await self._rest_post("profiles", data, upsert=True, on_conflict="id")

    async def update_subscription_by_lemon_id(
        self, lemon_subscription_id: str, data: dict[str, Any]
    ) -> None:
        await self._rest_patch(
            "subscriptions",
            {"lemon_subscription_id": f"eq.{lemon_subscription_id}"},
            data,
        )

    # --- Usage tracking (simple counters on profile for production dashboard) ---
    async def get_ai_calls_count(self, user_id: str) -> int:
        rows = await self._rest_get(
            "profiles",
            {"id": f"eq.{user_id}", "select": "ai_calls_count"},
        )
        if not rows:
            return 0
        return int(rows[0].get("ai_calls_count") or 0)

    async def increment_ai_calls(self, user_id: str, amount: int = 1) -> int:
        # Read-modify-write is acceptable for low volume. For higher contention use DB RPC.
        current = await self.get_ai_calls_count(user_id)
        new_count = current + amount
        await self._rest_patch(
            "profiles",
            {"id": f"eq.{user_id}"},
            {"ai_calls_count": new_count, "usage_updated_at": "now()"},
        )
        return new_count

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
            # Raise to surface DB issues instead of silent empty results (prod observability)
            raise RuntimeError(f"Supabase REST GET {table} failed: {response.status_code} {response.text}")
        return response.json()

    async def _rest_patch(
        self, table: str, match: dict[str, str], data: dict[str, Any]
    ) -> None:
        if not self._db_configured():
            return

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(
                f"{self._base}/rest/v1/{table}",
                params=match,
                json=data,
                headers={**self._service_headers(), "Prefer": "return=minimal"},
            )
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase REST PATCH {table} failed: {response.status_code} {response.text}")

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
            response = await client.post(
                f"{self._base}/rest/v1/{table}",
                json=data,
                headers=headers,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase REST POST {table} failed: {response.status_code} {response.text}")

    def _service_headers(self) -> dict[str, str]:
        return {
            "apikey": self._service,
            "Authorization": f"Bearer {self._service}",
            "Content-Type": "application/json",
        }

    # === Thin Gallery / Publishing (Phase 8) ===

    async def create_animation(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new animation metadata record. Returns the created row."""
        # Use post with return=representation to get the row
        headers = {**self._service_headers(), "Prefer": "return=representation"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self._base}/rest/v1/animations",
                json=data,
                headers=headers,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase create animation failed: {response.status_code} {response.text}")
        rows = response.json()
        return rows[0] if rows else {}

    async def list_animations(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str | None = "published",
        featured: bool | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {
            "select": "*",
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset),
        }
        if status:
            params["status"] = f"eq.{status}"
        if featured is not None:
            params["featured"] = f"eq.{str(featured).lower()}"
        if search:
            # Simple ilike on title/desc (Supabase supports)
            params["or"] = f"(title.ilike.*{search}*,description.ilike.*{search}*)"
        return await self._rest_get("animations", params)

    async def get_animation(self, animation_id: str) -> dict[str, Any] | None:
        rows = await self._rest_get("animations", {"id": f"eq.{animation_id}", "select": "*", "limit": "1"})
        return rows[0] if rows else None

    async def update_animation(self, animation_id: str, data: dict[str, Any]) -> None:
        await self._rest_patch("animations", {"id": f"eq.{animation_id}"}, data)


@lru_cache
def get_supabase_service() -> SupabaseService:
    return SupabaseService()