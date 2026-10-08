"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import APP_NAME, APP_VERSION


class Settings(BaseSettings):
    """Validated application settings.

    Values are loaded from environment variables and the .env file.
    """

    # Application
    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    debug: bool = False

    # External Services (configured in future phases)
    openai_api_key: str = ""
    github_token: str = ""
    database_url: str = ""
    redis_url: str = ""

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Workspace & Repository Ingestion
    workspace_dir: str = "workspace"
    max_repo_size_mb: int = 100
    clone_timeout_seconds: int = 60
    max_file_tree_depth: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
