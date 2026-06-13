from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Craterra API"
    app_env: str = "local"
    openrouter_api_key: str | None = None
    openrouter_model: str = "deepseek/deepseek-v4-flash"
    openrouter_fallback_model: str = "qwen/qwen3-30b-a3b-instruct-2507"
    lastfm_api_key: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    apple_music_affiliate_token: str | None = None
    http_timeout_seconds: float = 10.0
    local_data_dir: str = "data"
    validate_rate_limit_per_minute: int = 60
    feedback_rate_limit_per_minute: int = 60
    dig_rate_limit_per_minute: int = 12
    outbound_click_rate_limit_per_minute: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
