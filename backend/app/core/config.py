from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GEO Platform"
    env: str = "dev"
    debug: bool = True
    api_prefix: str = "/api"

    # Postgres (async DSN)
    database_url: str = "postgresql+asyncpg://geo:geo@localhost:5432/geo"

    # Redis (queue + cache)
    redis_url: str = "redis://localhost:6379/0"

    # MinIO / S3 object storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "geo-assets"
    minio_secure: bool = False

    # Auth skeleton (P0): single shared API token; real multi-tenant auth lands in P5.
    api_token: str | None = None
    default_tenant_id: str = "00000000-0000-0000-0000-000000000000"

    # Observability
    sentry_dsn: str | None = None

    # Provider config file
    providers_config_path: str = str(BACKEND_DIR / "app" / "providers" / "providers.yaml")

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
