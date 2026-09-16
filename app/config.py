"""
Configuration management via pydantic-settings.
Reads API keys and service URLs from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings — loaded from environment variables or .env file."""

    # --- LLM Provider Keys (at least one required) ---
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")

    # --- Database (Stage 3+) ---
    database_url: Optional[str] = Field(
        default=None,
        alias="DATABASE_URL",
    )

    # --- Qdrant (Stage 4+) ---
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")

    # --- Redis (Stage 7) ---
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    # --- App ---
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @staticmethod
    def _is_real_key(key: str | None) -> bool:
        """Check if a key is real (not a placeholder)."""
        if not key:
            return False
        placeholders = ("your_", "_here", "sk-your", "gsk_your", "CHANGE_ME")
        return not any(p in key for p in placeholders)

    @property
    def available_providers(self) -> list[str]:
        """Return list of providers that have real (non-placeholder) API keys configured."""
        providers = []
        if self._is_real_key(self.groq_api_key):
            providers.append("groq")
        if self._is_real_key(self.openai_api_key):
            providers.append("openai")
        if self._is_real_key(self.gemini_api_key):
            providers.append("gemini")
        return providers


settings = Settings()
