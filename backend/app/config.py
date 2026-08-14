from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Merit AI"
    app_version: str = "0.1.0"
    environment: str = "development"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""

    merit_storage_mode: Literal["supabase", "memory"] = "supabase"
    merit_max_questions: int = Field(default=7, ge=3, le=12)
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
