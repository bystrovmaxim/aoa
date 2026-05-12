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
Each generated route declares the ``connections`` required by its action; the live
interchange graph uses one :class:`~aoa.maxitor.model.core.resources.service_graph_resource.ServiceGraphResource`
instance for the whole application, built when ASGI ``lifespan`` creates the API session.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aoa.action_machine.auth import NoAuthCoordinator
from aoa.action_machine.graph_model.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.integrations.fastapi import FastApiAdapter
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.api.routes.sidebar import router as sidebar_router
from aoa.maxitor.api.session import build_maxitor_api_session
from aoa.maxitor.model.core.resources.networkx_graph_resource import NetworkXGraphResource
from aoa.maxitor.model.core.resources.service_graph_resource import (
    SERVICE_GRAPH_CONNECTION_KEY,
    ServiceGraphResource,
)
from aoa.maxitor.model.diagrams.actions.get_interchange_graph_payload_action import (
    GetInterchangeGraphPayloadAction,
)
from aoa.maxitor.model.diagrams.actions.list_domains_action import ListDomainsAction
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction


def create_app() -> FastAPI:
    """
    Create the Maxitor FastAPI application.

    AI-CORE-BEGIN
    ROLE: Build the ASGI app consumed by uvicorn, tests, and production hosting.
    CONTRACT: React assets are hosted separately; diagram JSON uses FastApiAdapter + shared machine.
    AI-CORE-END
    """
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    auth = NoAuthCoordinator()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Build Maxitor runtime state once per ASGI application lifecycle."""
        session = await build_maxitor_api_session(machine=machine)
        application.state.maxitor_session = session
        networkx_graph = NetworkXGraphResource()
        diagram_service_graph = ServiceGraphResource(session.nx_graph)

        action_subapp = (
            FastApiAdapter(
                machine=machine,
                auth_coordinator=auth,
                title="Maxitor ActionMachine API",
                version="1.0.0",
                description=(
                    "JSON endpoints generated from diagrams actions. "
                    "Each route declares its ``connections``; diagram routes share one "
                    "``ServiceGraphResource`` for the application lifetime."
                ),
            )
            .get(
                "/erd/domain-qualnames",
                ListDomainsAction,
                connections={SERVICE_GRAPH_CONNECTION_KEY: diagram_service_graph},
                tags=["erd"],
            )
            .get(
                "/erd/domains/{domain_qualname:path}",
                ListEntitiesAction,
                connections={SERVICE_GRAPH_CONNECTION_KEY: diagram_service_graph},
                tags=["erd"],
            )
            .get(
                "/graph/interchange",
                GetInterchangeGraphPayloadAction,
                connections={SERVICE_GRAPH_CONNECTION_KEY: diagram_service_graph},
                tags=["graph"],
            )
            .build()
        )
        application.mount("/api/v1", action_subapp)
        yield

    fastapi_app = FastAPI(title="Maxitor API", lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    fastapi_app.include_router(sidebar_router)

    @fastapi_app.get("/api/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return fastapi_app


app = create_app()
