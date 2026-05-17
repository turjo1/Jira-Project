from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field(default="local")
    log_level: str = Field(default="INFO")

    database_url: str = Field(
        default="mysql+aiomysql://app:app@mysql:3306/jira_analytics"
    )
    db_pool_size: int = Field(default=20)
    db_max_overflow: int = Field(default=10)

    redis_url: str = Field(default="redis://redis:6379/0")

    jwt_signing_key: str = Field(default="dev-insecure-change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_ttl_seconds: int = Field(default=24 * 60 * 60)
    jwt_refresh_ttl_seconds: int = Field(default=14 * 24 * 60 * 60)

    aes_encryption_key: str = Field(
        default="dev-insecure-32byte-key-change!!"
    )

    jira_client_id: str = Field(default="")
    jira_client_secret: str = Field(default="")
    jira_redirect_uri: str = Field(
        default="http://localhost:8000/auth/callback"
    )
    jira_oauth_authorize_url: str = Field(
        default="https://auth.atlassian.com/authorize"
    )
    jira_oauth_token_url: str = Field(
        default="https://auth.atlassian.com/oauth/token"
    )
    jira_accessible_resources_url: str = Field(
        default="https://api.atlassian.com/oauth/token/accessible-resources"
    )

    rate_limit_per_minute: int = Field(default=1000)

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Celery configuration
    celery_broker_url: str = Field(default="redis://redis:6379/0")
    celery_result_backend: str = Field(default="redis://redis:6379/0")


@lru_cache
def get_settings() -> Settings:
    return Settings()
