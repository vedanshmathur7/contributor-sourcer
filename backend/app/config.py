import os
import tempfile
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        extra="ignore",
    )

    github_token: str = ""
    github_api_url: str = "https://api.github.com"

    llm_provider: str = "anthropic"  # anthropic | openai | none
    llm_api_key: str = ""
    llm_model: str = "claude-opus-5-5"

    database_url: str = ""
    cors_origins: str = "http://localhost:3000"
    git_sha: str = Field(default="", validation_alias="GIT_SHA")
    render_git_commit: str = Field(default="", validation_alias="RENDER_GIT_COMMIT")

    # Agent limits
    search_rate_per_min: int = 28  # GitHub search API allows 30/min when authenticated
    max_search_pages: int = 3
    http_timeout_s: float = 20.0
    # Fixture mode simulates GitHub latency so the live trace is watchable in demos (0 in tests).
    fixture_latency_ms: int = 140
    # Serverless hosts (Vercel) kill background tasks once a response returns, so the agent runs inside the
    # SSE request instead. Auto-enabled on Vercel; can be forced with RUN_INLINE=1.
    run_inline: bool = bool(os.environ.get("VERCEL"))

    @property
    def live_available(self) -> bool:
        return bool(self.github_token)

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider in ("anthropic", "openai") and bool(self.llm_api_key)

    @property
    def commit_sha(self) -> str:
        return (self.git_sha or self.render_git_commit or "local")[:12]

    @property
    def async_database_url(self) -> str:
        url = self.database_url.strip()
        if not url:
            data_dir = Path(tempfile.gettempdir()) if os.environ.get("VERCEL") else BACKEND_DIR / "data"
            data_dir.mkdir(exist_ok=True)
            return f"sqlite+aiosqlite:///{data_dir / 'sourcer.db'}"
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
