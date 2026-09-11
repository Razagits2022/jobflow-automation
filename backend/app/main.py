"""FastAPI application factory.

Mounts all routers, configures CORS for the Next.js frontend,
and provides the /health liveness endpoint.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.routes import candidates, health, jobs, runs, stats
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.redis import close_arq_pool

log = structlog.get_logger(__name__)


class SubscribeResponse(BaseModel):
    subscribed: bool = True


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    configure_logging()

    if settings.storage_driver == "supabase":
        missing: list[str] = []
        if not settings.supabase_url or not settings.supabase_url.strip():
            missing.append("SUPABASE_URL")
        if not settings.supabase_service_role_key or not settings.supabase_service_role_key.strip():
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if not settings.supabase_storage_bucket or not settings.supabase_storage_bucket.strip():
            missing.append("SUPABASE_STORAGE_BUCKET")

        if missing:
            log.error("storage.supabase_misconfigured", missing=", ".join(missing))
        else:
            parsed = urlparse(settings.supabase_url)
            host = parsed.hostname or settings.supabase_url
            log.info("storage.supabase_ready", url=host, bucket=settings.supabase_storage_bucket)

    yield
    await close_arq_pool()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="JobFlow API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ---- CORS ----
    cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if settings.app_env == "development":
        cors_origins.append("*")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_env == "development" else cors_origins,
        allow_origin_regex=r"https://.*" if settings.app_env != "development" else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Routers ----
    application.include_router(health.router, tags=["health"])
    application.include_router(candidates.router, prefix="/api/candidate", tags=["candidate"])
    application.include_router(candidates.router, prefix="/api/candidates", tags=["candidates"])
    application.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    application.include_router(runs.router, prefix="/api/runs", tags=["runs"])
    application.include_router(stats.router, prefix="/api/stats", tags=["stats"])

    @application.post("/api/subscribe", response_model=SubscribeResponse, tags=["subscribe"])
    async def subscribe() -> SubscribeResponse:
        """Stub subscription activation endpoint."""
        return SubscribeResponse(subscribed=True)

    return application


app = create_app()
