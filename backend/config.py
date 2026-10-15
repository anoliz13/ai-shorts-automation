"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API keys
    muapi_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # LLM provider
    llm_provider: str = "openai"
    openai_model: str = "gpt-4o-mini"

    # Local Whisper settings
    local_whisper_model: str = "base"
    local_whisper_device: str = "auto"

    # Output
    local_output_dir: str = "output"
    db_path: str = "data/shorts_automation.db"

    # Scheduler
    check_hour: int = 20
    check_minute: int = 0

    # Anti-spam limits
    max_shorts_per_video: int = 5
    max_uploads_per_day_tiktok: int = 5
    max_uploads_per_day_youtube: int = 5
    min_gap_minutes: int = 30

    # Shorts generation mode
    shorts_mode: str = "api"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
