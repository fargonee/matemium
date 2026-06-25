"""Server configuration from environment."""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MATEMIUM_", extra="ignore")

    env: str = "development"
    # Support PORT (standard on PaaS like Northflank, Railway, Heroku) and MATEMIUM_PORT
    host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("host", "HOST", "MATEMIUM_HOST"),
    )
    port: int = Field(
        default=8080,
        validation_alias=AliasChoices("port", "PORT", "MATEMIUM_PORT"),
    )

    # Legacy dev stub (desktop email/password login)
    auth_stub: bool = True

    # Supabase — shared auth for website + desktop
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    admin_emails: str = ""

    # Lemon Squeezy billing
    lemon_squeezy_api_key: str = ""
    lemon_squeezy_webhook_secret: str = ""
    lemon_squeezy_store_id: str = ""
    lemon_squeezy_variant_pro_monthly: str = ""
    lemon_squeezy_test_mode: bool = True
    site_url: str = "http://localhost:5173"

    # LLM proxy
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_stub: bool = True

    # CORS — comma-separated origins (website + Tauri dev)
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173,"
        "tauri://localhost,http://localhost,http://127.0.0.1"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_email_list(self) -> list[str]:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]


settings = Settings()