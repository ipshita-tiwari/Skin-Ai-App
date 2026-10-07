"""
Application configuration.
Centralizes settings for file limits, allowed types, and API behavior.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Load from environment or .env; defaults for local dev."""

    # File upload limits (bytes)
    max_skin_image_size: int = 5 * 1024 * 1024   # 5 MB
    max_blood_report_size: int = 10 * 1024 * 1024  # 10 MB

    # Allowed MIME types
    allowed_image_types: list = ["image/jpeg", "image/png", "image/webp"]
    allowed_pdf_type: str = "application/pdf"

    # API
    api_prefix: str = "/api"
    app_title: str = "Skin AI Assistant API"
    app_version: str = "1.0.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
