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

    site_url: str = "http://localhost:5173"

    # LLM proxy
    llm_api_base: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openai/gpt-4o-mini"
    llm_stub: bool = True

    # CORS — comma-separated origins (website + Tauri dev)
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173,"
        "tauri://localhost,http://localhost,http://127.0.0.1,"
        "https://p01--math--zjvwyx4fjqbn.code.run,https://*.code.run"
    )

    # Rate limiting (requests per minute). Applied primarily to chat endpoints.
    rate_limit_free_rpm: int = 60
    rate_limit_pro_rpm: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_email_list(self) -> list[str]:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]

    def validate_for_production(self) -> None:
        """Fail fast in production if critical configuration is missing or unsafe."""
        if self.env != "production":
            return
        problems: list[str] = []
        if self.auth_stub:
            problems.append("MATEMIUM_AUTH_STUB must be false in production")
        if not self.supabase_url or not self.supabase_service_role_key:
            problems.append("Supabase URL and service role key are required in production")
        if problems:
            raise RuntimeError("Production configuration errors: " + "; ".join(problems))


settings = Settings()
settings.validate_for_production()
