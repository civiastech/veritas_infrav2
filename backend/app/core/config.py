from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Veritas Infra API"
    environment: str = "development"
    api_v1_str: str = "/api/v1"

    jwt_secret_key: str = "change-me"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 60 * 24 * 7

    database_url: str = "sqlite:///./veritas_infra_v2.db"

    cors_origins: str = (
        "http://localhost:8080,"
        "http://127.0.0.1:8080,"
        "http://localhost,"
        "http://127.0.0.1"
    )
    trusted_hosts: str = "localhost,127.0.0.1"

    first_superuser_email: str = "admin@visc.org"
    first_superuser_password: str = "AdminPass123!"

    auto_create_tables: bool = False
    uploads_dir: str = str(BASE_DIR / "uploads")
    max_upload_size_mb: int = 50

    redis_url: str = "redis://redis:6379/0"
    redis_enabled: bool = True
    login_rate_limit: int = 10
    rate_limit_window_seconds: int = 60
    account_lock_threshold: int = 5
    account_lock_minutes: int = 15

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_evidence: str = "veritas-evidence"
    minio_enabled: bool = True

    metrics_enabled: bool = True
    mfa_issuer: str = "Veritas Infra"

    uvicorn_host: str = "0.0.0.0"
    uvicorn_port: int = 8000
    uvicorn_workers: int = 1

    celery_concurrency: int = 2
    celery_loglevel: str = "info"
    celery_queues: str = "celery"

    run_migrations: bool = True
    run_seed_on_boot: bool = False

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def validate_jwt_secret_key(cls, value: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("JWT_SECRET_KEY cannot be empty")
        return value

    @field_validator("first_superuser_email", mode="before")
    @classmethod
    def normalize_superuser_email(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("uploads_dir", mode="before")
    @classmethod
    def normalize_uploads_dir(cls, value: str) -> str:
        return str(Path(value).expanduser().resolve())

    @field_validator("uvicorn_workers", "celery_concurrency", mode="before")
    @classmethod
    def ensure_positive_int(cls, value: int) -> int:
        value = int(value)
        if value < 1:
            raise ValueError("Value must be at least 1")
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> List[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return origins

    @property
    def trusted_host_list(self) -> List[str]:
        hosts = [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]
        if not hosts:
            return ["localhost", "127.0.0.1"]
        return hosts

    @property
    def uploads_path(self) -> Path:
        path = Path(self.uploads_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()