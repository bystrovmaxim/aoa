# packages/aoa-maxitor/src/aoa/maxitor/api/app.py
"""
FastAPI ASGI application for Maxitor.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose API endpoints for a separately hosted Vite React SPA. This module does
not serve React assets or Python-rendered shell HTML.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aoa.maxitor.api.routes.diagrams import router as diagrams_router
from aoa.maxitor.api.routes.sidebar import router as sidebar_router
from aoa.maxitor.api.session import build_maxitor_api_session


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build Maxitor runtime state once per ASGI application lifecycle."""
    app.state.maxitor_session = await build_maxitor_api_session()
    yield


def create_app() -> FastAPI:
    """
    Create the Maxitor FastAPI application.

    AI-CORE-BEGIN
    ROLE: Build the ASGI app consumed by uvicorn, tests, and production hosting.
    CONTRACT: React assets are hosted separately; this app only exposes API and diagram HTML endpoints.
    AI-CORE-END
    """
    fastapi_app = FastAPI(title="Maxitor API", lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    fastapi_app.include_router(sidebar_router)
    fastapi_app.include_router(diagrams_router)

    @fastapi_app.get("/api/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return fastapi_app


app = create_app()
