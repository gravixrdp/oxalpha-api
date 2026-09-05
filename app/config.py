"""Application configuration and environment variable loading."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema."""

    # Authentication
    API_KEY: str = "change-this"

    # Upstream Provider Configuration
    UPSTREAM_URL: str = "https://oxalpha.com"
    UPSTREAM_MODEL: str = "z-ai/glm-5.3-flash"
    PUBLIC_MODEL_NAME: str = "glm-5.3-flash"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 30
    RATE_LIMIT_WINDOW: int = 60

    # Networking & Timeouts
    REQUEST_TIMEOUT: float = 120.0
    MAX_REQUEST_BODY_SIZE: int = 2 * 1024 * 1024  # 2MB

    # Security & CORS
    CORS_ORIGINS: str = "*"

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        if not self.CORS_ORIGINS:
            return []
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
