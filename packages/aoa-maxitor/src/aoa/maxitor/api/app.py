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
Each generated diagram route declares the shared
:class:`~aoa.maxitor.model.core.resources.duckdb_graph_resource.DuckDBGraphResource`
connection it reads. Sidebar rows are loaded once in the ASGI lifespan
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
from aoa.maxitor.model.diagrams.actions.full_graph_action import FullGraphAction
from aoa.maxitor.model.diagrams.actions.list_domains_action import ListDomainsAction
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.actions.list_node_types_action import ListNodeTypesAction


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
                "Each diagram route declares its shared ``DuckDBGraphResource`` connection."
            ),
        )
        .get(
            "/list-domains",
            ListDomainsAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_graph},
        )
        .get(
            "/list-entities",
            ListEntitiesAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_graph},
        )
        .get(
            "/list-node-types",
            ListNodeTypesAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_graph},
        )
        .get(
            "/full-graph",
            FullGraphAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_graph},
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
