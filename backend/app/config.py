from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str = "sqlite+pysqlite:///:memory:"
    redis_url: str | None = None
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_hours: int = 72
    field_encrypt_key: str | None = None
    minio_endpoint: str | None = None
    minio_root_user: str | None = None
    minio_root_password: str | None = None
    minio_bucket: str = "campus-assistant"
    minio_secure: bool = False
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "deepseek-chat"
    demo_reset_enabled: bool = True
    app_env: str = "demo"
    app_name: str = "Campus Assistant API"
    tz: str = "Asia/Shanghai"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
