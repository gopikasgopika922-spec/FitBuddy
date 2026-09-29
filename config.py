from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FitBuddy"
    environment: str = "development"
    database_url: str = "sqlite:///./fitbuddy.db"

    gemini_api_key: str = ""
    workout_model: str = "gemini-3.1-pro-preview"
    nutrition_model: str = "gemini-3.8-flash"
    demo_mode: bool = False

    admin_username: str = "admin"
    admin_password: str = "change-me"

    max_feedback_length: int = 2000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
