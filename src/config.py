"""
Configuration management using Pydantic Settings.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI API
    openai_api_key: str
    openai_api_timeout: int = 30
    max_retries: int = 3

    # Google Sheets
    google_sheets_id: str
    google_credentials_path: str = "./credentials.json"

    # Chroma Vector Database
    chroma_persist_dir: str = "./data/chroma_db"

    # OpenAI Models
    embedding_model: str = "text-embedding-3-small"
    tag_generation_model: str = "gpt-4o-mini"
    recommendation_model: str = "gpt-4o"
    clarification_model: str = "gpt-4o-mini"

    # Optional: Webhook Server
    webhook_port: int = 8000
    webhook_host: str = "localhost"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()


