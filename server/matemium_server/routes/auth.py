from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..deps import AuthUser, get_optional_user
from ..services.supabase import SupabaseService, get_supabase_service

router = APIRouter(tags=["auth"])


class TokenRequest(BaseModel):
    email: str = Field(..., examples=["user@example.com"])
    password: str = Field(..., min_length=1)


class SessionRequest(BaseModel):
    """Exchange a Supabase access token (website Google sign-in or desktop OAuth)."""

    access_token: str = Field(..., min_length=10)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    email: str | None = None
    plan: str | None = None


@router.post("/auth/token", response_model=TokenResponse)
def issue_token(body: TokenRequest) -> TokenResponse:
    """Dev stub for desktop — returns a bearer token when MATEMIUM_AUTH_STUB=true."""
    if not settings.auth_stub:
        raise HTTPException(
            status_code=400,
            detail="Email/password auth disabled. Use Supabase sign-in via /v1/auth/session.",
        )
    stub_token = f"dev.{body.email.split('@')[0]}.token"
    return TokenResponse(access_token=stub_token, expires_in=604800, email=body.email, plan="free")


@router.post("/auth/session", response_model=TokenResponse)
async def exchange_session(
    body: SessionRequest,
    supabase: SupabaseService = Depends(get_supabase_service),
) -> TokenResponse:
    """Validate Supabase JWT and return it for the desktop client to store."""
    user = await supabase.verify_access_token(body.access_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Supabase session")

    profile = await supabase.get_profile(user["id"])
    email = (profile or {}).get("email") or user.get("email")
    plan = (profile or {}).get("plan", "free")

    return TokenResponse(
        access_token=body.access_token,
        expires_in=3600,
        email=email,
        plan=plan,
    )


@router.get("/auth/verify", response_model=TokenResponse)
async def verify_token(
    user: Annotated[AuthUser | None, Depends(get_optional_user)],
) -> TokenResponse:
    """Check that the current bearer token is valid (website + desktop)."""
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return TokenResponse(
        access_token="verified",
        expires_in=3600,
        email=user.email,
        plan=user.plan,
    )