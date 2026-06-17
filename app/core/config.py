"""Application configuration.

Everything the app needs from the environment lives here as a single typed object.
This replaces scattered `os.environ[...]` / `process.env` lookups: you get validation,
defaults, and autocomplete. `Settings` is read once at startup and reused everywhere.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # pydantic-settings reads these from environment variables or a local .env file.
    # `case_sensitive=False` means MONGODB_URI in .env maps to `mongodb_uri` below.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # --- Server ---
    app_name: str = "Analysis AI"
    port: int = 3000
    environment: str = "development"

    # --- MongoDB (used from Phase 1) ---
    mongodb_uri: str = "mongodb://localhost:27017"
    db_name: str = "analysisai"

    # --- Sanitizer service (used from Phase 7) ---
    sanitizer_url: str = "http://localhost:8000/ner"

    # --- OpenAI (used from Phase 2) ---
    openai_api_key: str = ""

    # --- Per-stage model selection ---
    brd_agent_model: str = "gpt-4.1"
    prompt_agent_model: str = "gpt-4.1"
    planning_agent_model: str = "gpt-4.1"
    notebook_agent_model: str = "gpt-4.1"
    summary_agent_model: str = "gpt-4.1"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    `@lru_cache` ensures the .env file is parsed only once for the whole process.
    FastAPI routes/services call `get_settings()` (or use it as a dependency) to read config.
    """
    return Settings()
