"""
TRACE-X Configuration
All settings sourced from environment variables.
"""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "TRACE-X"
    app_version: str = "1.0.0"
    environment: Literal["development", "production", "testing"] = "development"
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./tracex.db"

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_url: str = "redis://:redispass@localhost:6379/0"
    cache_ttl_seconds: int = 300

    # ── Auth / JWT ───────────────────────────────────────────────────────────
    secret_key: str = "change-me-to-a-random-secret-key-min-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # ── Rate limiting ────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── Blockchain ───────────────────────────────────────────────────────────
    blockchain_provider: Literal["mock", "evm"] = "mock"
    eth_rpc_url: str = ""

    # ── Demo ─────────────────────────────────────────────────────────────────
    seed_demo_data: bool = True

    # ── Reports ──────────────────────────────────────────────────────────────
    report_output_dir: str = "/app/reports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
