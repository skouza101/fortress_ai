from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str = "Fortress AI"
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Local AI Models (SSH Tunnel) ──────────────────────────
    LLM_PROVIDER: str = "rocm"  # rocm | nim | modelscope

    QWEN_API_BASE: str = "http://localhost:8001/v1"
    QWEN_MODEL: str = "Qwen/Qwen3.6-27B"

    # Optional NVIDIA NIM endpoint/model. These are only used when LLM_PROVIDER=nim.
    NIM_API_BASE: str = "http://localhost:8002/v1"
    NIM_MODEL: str = "Qwen/Qwen3.6-27B"
    NIM_API_KEY: str = ""

    # Optional ModelScope API-Inference endpoint/model.
    # These are only used when LLM_PROVIDER=modelscope.
    MODELSCOPE_API_BASE: str = "https://api-inference.modelscope.ai/v1"
    MODELSCOPE_MODEL: str = "Qwen/Qwen2.5-VL-72B-Instruct"
    MODELSCOPE_API_KEY: str = ""

    LOCAL_API_KEY: str = "dummy-key"
    TAVILY_API_KEY: str = "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"
    HUGGING_FACE_HUB_TOKEN: str = ""

    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3
    LLM_MAX_OUTPUT_TOKENS: int = 4096

    # ── Qdrant (future RAG) ──────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "legal_documents"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # ── Redis & Celery ────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── File uploads ──────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
    USE_PYMUPDF: bool = True

    # ── Clerk Authentication ──────────────────────────────────
    CLERK_JWKS_URL: str = "https://your-app.clerk.accounts.dev/.well-known/jwks.json"
    CLERK_ISSUER: str = "https://your-app.clerk.accounts.dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def llm_api_base(self) -> str:
        if self.LLM_PROVIDER.lower() == "modelscope":
            return self.MODELSCOPE_API_BASE
        if self.LLM_PROVIDER.lower() == "nim":
            return self.NIM_API_BASE
        return self.QWEN_API_BASE

    @property
    def llm_model(self) -> str:
        if self.LLM_PROVIDER.lower() == "modelscope":
            return self.MODELSCOPE_MODEL
        if self.LLM_PROVIDER.lower() == "nim":
            return self.NIM_MODEL
        return self.QWEN_MODEL

    @property
    def llm_api_key(self) -> str:
        if self.LLM_PROVIDER.lower() == "modelscope":
            return self.MODELSCOPE_API_KEY or self.LOCAL_API_KEY
        if self.LLM_PROVIDER.lower() == "nim":
            return self.NIM_API_KEY or self.LOCAL_API_KEY
        return self.LOCAL_API_KEY


settings = Settings()
