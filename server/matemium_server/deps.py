"""FastAPI dependencies — Supabase JWT auth shared by website and desktop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .services.supabase import SupabaseService, get_supabase_service

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    id: str
    email: str
    role: str
    plan: str
    full_name: str | None = None
    lemon_customer_id: str | None = None


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    supabase: SupabaseService = Depends(get_supabase_service),
) -> AuthUser | None:
    if not credentials:
        return None

    token = credentials.credentials.strip()
    if not token:
        return None

    if settings.auth_stub and token.startswith("dev."):
        parts = token.split(".")
        email = f"{parts[1]}@dev.local" if len(parts) > 1 else "dev@local"
        return AuthUser(id="dev-user", email=email, role="user", plan="free")

    user = await supabase.verify_access_token(token)
    if not user:
        return None

    profile = await supabase.get_profile(user["id"])

    # Backfill profile row if the DB trigger didn't create one (e.g. migration timing,
    # early signups, or Google OAuth edge cases). This makes admin lists etc. work.
    if not profile:
        meta = user.get("user_metadata") or {}
        email_for_profile = user.get("email") or meta.get("email") or ""
        await supabase.upsert_profile({
            "id": user["id"],
            "email": email_for_profile,
            "full_name": meta.get("full_name") or meta.get("name"),
            "avatar_url": meta.get("avatar_url") or meta.get("picture"),
        })
        profile = await supabase.get_profile(user["id"])

        # If this email is in the admin bootstrap list, persist the role so the
        # users list in admin console reflects it.
        if email_for_profile.lower() in settings.admin_email_list:
            await supabase.update_profile(user["id"], {"role": "admin"})
            profile = await supabase.get_profile(user["id"])

    role = (profile or {}).get("role", "user")
    plan = (profile or {}).get("plan", "free")
    email = (profile or {}).get("email") or user.get("email") or ""

    if role != "admin" and email.lower() in settings.admin_email_list:
        role = "admin"

    return AuthUser(
        id=user["id"],
        email=email,
        role=role,
        plan=plan,
        full_name=(profile or {}).get("full_name"),
        lemon_customer_id=(profile or {}).get("lemon_customer_id"),
    )


async def require_user(
    user: Annotated[AuthUser | None, Depends(get_optional_user)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> AuthUser:
    if user:
        return user

    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server auth not configured — set MATEMIUM_SUPABASE_URL and MATEMIUM_SUPABASE_ANON_KEY in server/.env",
        )

    if credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Supabase token",
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")


async def require_admin(
    user: Annotated[AuthUser, Depends(require_user)],
) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user