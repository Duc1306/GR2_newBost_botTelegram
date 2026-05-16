"""
FastAPI application entry point.

Route modules live in src/api/routes/. This file only handles:
- App / lifespan setup
- Middleware registration
- Router inclusion
"""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.middleware import setup_rate_limiting, setup_logging, log_requests_middleware
from src.config import get_allowed_origins
from src.api.channels import router as channels_router
from src.api.telegram_auth import router as telegram_auth_router
from src.api.routes.auth_routes import router as auth_router
from src.api.routes.post_routes import router as post_router
from src.api.routes.analytics_routes import router as analytics_router
from src.api.routes.notification_routes import router as notification_router
from src.api.routes.settings_routes import router as settings_router
from src.api.routes.public_routes import router as public_router
from src.api.routes.tts_routes import router as tts_router
from src.api.routes.hotnews_routes import router as hotnews_router, _hotnews_precompute_worker
from src.api.routes.admin_routes import router as admin_router

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background workers when the API boots; cancel them on shutdown."""
    from scripts.create_indexes import create_indexes
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, create_indexes)
    from src.ingestion.channel_queue_worker import run_worker, run_refresh_loop
    pending_task = asyncio.create_task(run_worker())
    refresh_task = asyncio.create_task(run_refresh_loop())
    precompute_task = asyncio.create_task(_hotnews_precompute_worker())
    logger.info("Background workers started.")
    try:
        yield
    finally:
        pending_task.cancel()
        refresh_task.cancel()
        precompute_task.cancel()
        logger.info("Background workers stopped.")


app = FastAPI(
    title="MXH Aggregator API",
    version="2.0.0",
    lifespan=lifespan,
)

setup_rate_limiting(app)
app.middleware("http")(log_requests_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(channels_router)
app.include_router(telegram_auth_router)
app.include_router(auth_router)
app.include_router(post_router)
app.include_router(analytics_router)
app.include_router(notification_router)
app.include_router(settings_router)
app.include_router(public_router)
app.include_router(tts_router)
app.include_router(hotnews_router)
app.include_router(admin_router)
