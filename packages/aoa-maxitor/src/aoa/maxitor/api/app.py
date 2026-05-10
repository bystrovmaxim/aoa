# packages/aoa-maxitor/src/aoa/maxitor/api/app.py
"""
FastAPI ASGI application for Maxitor.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose API endpoints for a separately hosted Vite React SPA. This module does
not serve React assets or Python-rendered shell HTML.

ERD data and the interchange graph payload are exposed as JSON via :class:`aoa.action_machine.integrations.fastapi.FastApiAdapter`
routes mounted under ``/api/v1``. The React SPA renders both viewers in the browser.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aoa.action_machine.auth import NoAuthCoordinator
from aoa.action_machine.integrations.fastapi import FastApiAdapter
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.api.maxitor_connection_holder import MaxitorConnectionHolder
from aoa.maxitor.api.routes.sidebar import router as sidebar_router
from aoa.maxitor.api.session import build_maxitor_api_session
from aoa.maxitor.model.app_view.actions.get_erd_domain_payload_action import GetErdDomainPayloadAction
from aoa.maxitor.model.app_view.actions.get_interchange_graph_payload_action import (
    GetInterchangeGraphPayloadAction,
)
from aoa.maxitor.model.app_view.actions.list_erd_domain_qualnames_action import ListErdDomainQualnamesAction


def create_app() -> FastAPI:
    """
    Create the Maxitor FastAPI application.

    AI-CORE-BEGIN
    ROLE: Build the ASGI app consumed by uvicorn, tests, and production hosting.
    CONTRACT: React assets are hosted separately; diagram JSON uses FastApiAdapter + shared machine.
    AI-CORE-END
    """
    machine = ActionProductMachine()
    connections_holder = MaxitorConnectionHolder()
    auth = NoAuthCoordinator()

    action_subapp = (
        FastApiAdapter(
            machine=machine,
            auth_coordinator=auth,
            connections_factory=connections_holder,
            title="Maxitor ActionMachine API",
            version="1.0.0",
            description=(
                "JSON endpoints generated from app-view actions. "
                "The interchange nx graph is injected per request via ``connections_factory``."
            ),
        )
        .get("/erd/domain-qualnames", ListErdDomainQualnamesAction, tags=["erd"])
        .get("/erd/domains/{domain_qualname:path}", GetErdDomainPayloadAction, tags=["erd"])
        .get("/graph/interchange", GetInterchangeGraphPayloadAction, tags=["graph"])
        .build()
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Build Maxitor runtime state once per ASGI application lifecycle."""
        session = await build_maxitor_api_session(machine=machine)
        application.state.maxitor_session = session
        connections_holder.set_session(session)
        yield

    fastapi_app = FastAPI(title="Maxitor API", lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    fastapi_app.include_router(sidebar_router)
    fastapi_app.mount("/api/v1", action_subapp)

    @fastapi_app.get("/api/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return fastapi_app


app = create_app()
