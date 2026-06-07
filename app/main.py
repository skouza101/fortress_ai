"""
Fortress AI — Private Multi-Agent Legal Audit System.

FastAPI backend serving the Next.js frontend.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes import health, conversations, chat, datasets, documents, ws

# ── Logging ──────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


from app.db.store import store

# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🏰 Fortress AI backend starting...")
    logger.info(
        f"   LLM endpoint:   {settings.llm_api_base} ({settings.llm_model}) provider={settings.LLM_PROVIDER}"
    )
    logger.info(f"   CORS origin:    {settings.FRONTEND_URL}")

    # Ensure upload directory exists
    settings.upload_path  # triggers mkdir

    # Connect to database
    await store.connect()
    logger.info("🔌 Connected to PostgreSQL database")

    yield

    # Disconnect from database
    await store.disconnect()
    logger.info("🔌 Disconnected from PostgreSQL database")
    logger.info("🏰 Fortress AI backend shutting down.")


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Private Multi-Agent Legal Contract Risk Assessment System",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow Next.js frontend) ────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(datasets.router)
app.include_router(documents.router)
app.include_router(ws.router)


# ── Root ─────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }
