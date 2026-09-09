"""Application settings loaded from environment variables via pydantic-settings.

All secrets live in .env (never committed). Defaults are safe for local development.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised, type-safe configuration for the entire backend.

    Load order: environment variables > .env file > field defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # ---- Database (Supabase) ----
    database_url: str = Field(
        default=(
            "postgresql+asyncpg://postgres.projectref:password@"
            "aws-0-region.pooler.supabase.com:5432/postgres"
        ),
        description=(
            "Supabase Session-mode pooler string (port 5432, "
            "IPv4-compatible, supports prepared statements)."
        ),
    )
    database_direct_url: str | None = Field(
        default=None,
        description=(
            "Supabase Direct connection string (host db.[ref].supabase.co:5432) "
            "for Alembic migrations; falls back to database_url when unset."
        ),
    )
    db_echo: bool = Field(
        default=False,
        description="Echo SQL queries in SQLAlchemy engine. Keep False for clean logs.",
    )

    # ---- Redis ----
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL used by both the cache and Arq queue.",
    )

    # ---- AI Provider ----
    ai_provider: Literal["deepseek", "openai"] = Field(
        default="deepseek",
        description="Which AI provider to use. Switching provider is a config change only.",
    )

    # DeepSeek (default provider)
    deepseek_api_key: str = Field(default="", description="DeepSeek API key.")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        description="Base URL for DeepSeek's OpenAI-compatible API.",
    )
    deepseek_model: str = Field(
        default="deepseek-v4-flash",
        description="DeepSeek model identifier. Override with your paid model.",
    )

    # OpenAI (fallback provider)
    openai_api_key: str = Field(default="", description="OpenAI API key (fallback).")
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model identifier (fallback).",
    )

    # ---- Zyte ----
    zyte_api_key: str = Field(default="", description="Zyte API key for page fetching.")

    # ---- CapSolver ----
    capsolver_api_key: str = Field(
        default="",
        description="CapSolver API key for automatic CAPTCHA solving.",
    )

    # ---- Browser & Network IP ----
    browser_headless: bool = Field(
        default=True,
        description="Run Chromium in headless mode. Set false for local debugging only.",
    )
    custom_ip: str = Field(
        default="",
        description=(
            "Custom IP / Proxy address (e.g. '1.2.3.4:8080' or 'http://user:pass@1.2.3.4:8080'). "
            "Leave empty to use host machine's own direct internet IP."
        ),
    )
    proxy_url: str = Field(
        default="",
        description="Alias for custom_ip.",
    )

    # ---- Worker ----
    worker_concurrency: int = Field(
        default=2,
        description="Max concurrent Arq jobs. Tune to ~1 browser per 2 GB RAM.",
        ge=1,
    )
    nav_timeout_ms: int = Field(
        default=30_000,
        description="Playwright navigation timeout in milliseconds.",
        ge=1000,
    )

    # ---- Inter-job Delay ----
    inter_job_delay_enabled: bool = Field(
        default=False,
        description="Space out job runs in production. Keep False in testing.",
    )
    inter_job_delay_min_minutes: float = Field(default=5.0)
    inter_job_delay_max_minutes: float = Field(default=20.0)

    # ---- Storage ----
    storage_driver: Literal["local", "s3"] = Field(
        default="local",
        description="Where to save screenshots, HTML, and resumes.",
    )
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_key: str = ""
    s3_secret: str = ""

    # ---- Computed helpers ----
    @property
    def active_ai_api_key(self) -> str:
        """Return the API key for the currently active provider."""
        return self.deepseek_api_key if self.ai_provider == "deepseek" else self.openai_api_key

    @property
    def active_ai_model(self) -> str:
        """Return the model identifier for the currently active provider."""
        return self.deepseek_model if self.ai_provider == "deepseek" else self.openai_model

    @property
    def active_ai_base_url(self) -> str | None:
        """Return the base URL override, or None for OpenAI (uses SDK default)."""
        return self.deepseek_base_url if self.ai_provider == "deepseek" else None

    @property
    def migration_database_url(self) -> str:
        """Return DATABASE_DIRECT_URL if configured, otherwise fallback to DATABASE_URL."""
        return self.database_direct_url or self.database_url

    @property
    def active_ip_or_proxy(self) -> str:
        """Return configured custom IP/proxy address, or empty string when using host's own IP."""
        return (self.custom_ip or self.proxy_url).strip()


# Module-level singleton — import this everywhere.
settings = Settings()
