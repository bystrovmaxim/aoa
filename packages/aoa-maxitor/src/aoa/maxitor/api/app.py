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
Each generated route declares the ``connections`` required by its action; diagram routes use a
shared :class:`~aoa.maxitor.model.core.resources.networkx_graph_resource.NetworkXGraphResource`
(list domains and interchange graph payload) and :class:`~aoa.maxitor.model.core.resources.duckdb_graph_resource.DuckDBGraphResource`
(ERD ``/erd/domains``),
constructed once with :func:`create_app` (interchange JSON from the examples ``graph-json`` HTTP endpoint). Sidebar rows are loaded once in the ASGI lifespan
(``application.state.sidebar_data``).
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
from aoa.maxitor.model.core.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)
from aoa.maxitor.model.core.resources.networkx_graph_resource import (
    NETWORKX_GRAPH_CONNECTION_KEY,
    NetworkXGraphResource,
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
    networkx_graph = NetworkXGraphResource()
    duckdb_graph = DuckDBGraphResource()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Load sidebar once; runs inside uvicorn's event loop (no ``asyncio.run``)."""
        session = await build_maxitor_api_session(machine=machine)
        application.state.sidebar_data = session.sidebar_data
        yield

    fastapi_app = FastAPI(title="Maxitor API", lifespan=lifespan)

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    fastapi_app.include_router(sidebar_router)

    action_subapp = (
        FastApiAdapter(
            machine=machine,
            auth_coordinator=auth,
            title="Maxitor ActionMachine API",
            version="1.0.0",
            description=(
                "JSON endpoints generated from diagrams actions. "
                "Each route declares its ``connections``; ``ListDomainsAction`` / interchange graph use "
                "``NetworkXGraphResource``; ``ListEntitiesAction`` uses ``DuckDBGraphResource``."
            ),
        )
        .get(
            "/erd/domain-qualnames",
            ListDomainsAction,
            connections={NETWORKX_GRAPH_CONNECTION_KEY: networkx_graph},
            tags=["erd"],
        )
        .get(
            "/erd/domains",
            ListEntitiesAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_graph},
            tags=["erd"],
        )
        .get(
            "/graph/interchange",
            GetInterchangeGraphPayloadAction,
            connections={NETWORKX_GRAPH_CONNECTION_KEY: networkx_graph},
            tags=["graph"],
        )
        .build()
    )
    fastapi_app.mount("/api/v1", action_subapp)

    @fastapi_app.get("/api/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return fastapi_app


_lazy_fastapi_app: dict[str, FastAPI | None] = {"app": None}


def __getattr__(name: str) -> FastAPI:
    """Lazily build ``app`` so imports of this module do not hit the examples graph-json URL."""
    if name != "app":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    cached = _lazy_fastapi_app["app"]
    if cached is None:
        cached = create_app()
        _lazy_fastapi_app["app"] = cached
    return cached
