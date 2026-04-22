from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Veritas Infra API'
    environment: str = 'development'
    api_v1_str: str = '/api/v1'
    jwt_secret_key: str = 'change-me'
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = 'sqlite:///./veritas_infra_v2.db'
    cors_origins: str = 'http://localhost:8080,http://127.0.0.1:8080,http://localhost,http://127.0.0.1'
    first_superuser_email: str = 'admin@visc.org'
    first_superuser_password: str = 'AdminPass123!'
    auto_create_tables: bool = True
    uploads_dir: str = str(BASE_DIR / 'uploads')
    max_upload_size_mb: int = 50
    trusted_hosts: str = 'localhost,127.0.0.1,backend,nginx,*'

    redis_url: str = 'redis://redis:6379/0'
    redis_enabled: bool = True
    login_rate_limit: int = 10
    rate_limit_window_seconds: int = 60
    account_lock_threshold: int = 5
    account_lock_minutes: int = 15

    minio_endpoint: str = 'minio:9000'
    minio_access_key: str = 'minioadmin'
    minio_secret_key: str = 'minioadmin'
    minio_secure: bool = False
    minio_bucket_evidence: str = 'veritas-evidence'
    minio_enabled: bool = True

    metrics_enabled: bool = True
    mfa_issuer: str = 'Veritas Infra'

    @property
    def cors_origin_list(self) -> List[str]:
        return [x.strip() for x in self.cors_origins.split(',') if x.strip()]

    @property
    def trusted_host_list(self) -> List[str]:
        return [x.strip() for x in self.trusted_hosts.split(',') if x.strip()]

settings = Settings()
