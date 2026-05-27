from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str = "Fortress AI"
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Local AI Models (SSH Tunnel) ──────────────────────────
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_API_KEY: str = ""

    TAVILY_API_KEY: str = "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"
    HUGGING_FACE_HUB_TOKEN: str = ""

    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3

    # ── Redis & Celery ────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Authentication ───────────────────────────────────────
    NEXTAUTH_SECRET: str = ""
    SECRET_KEY: str = ""

    # ── File uploads ──────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
    USE_PYMUPDF: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("NEXTAUTH_SECRET", "SECRET_KEY")
    @classmethod
    def validate_required_secrets(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Authentication secrets must be configured via environment variables")
        return value

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def llm_api_base(self) -> str:
        return self.GEMINI_API_BASE

    @property
    def llm_model(self) -> str:
        return self.GEMINI_MODEL

    @property
    def llm_api_key(self) -> str:
        return self.GEMINI_API_KEY


settings = Settings()
