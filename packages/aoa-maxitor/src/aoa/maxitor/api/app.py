# packages/aoa-maxitor/src/aoa/maxitor/api/app.py
"""
FastAPI ASGI application for Maxitor.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose API endpoints for a separately hosted Vite React SPA. This module does
not serve React assets or Python-rendered shell HTML.

ERD data and the interchange graph payload are exposed as JSON via :class:`aoa.action_machine.adapters.fastapi.FastApiAdapter`
routes mounted under ``/api/v1``. The React SPA renders both viewers in the browser.
Each diagram route reads the same in-process DuckDB snapshot built from the coordinator
JSON produced alongside the sidebar (avoids desync with a separate HTTP graph-json service).

Set ``AOA_SERVICE_URL`` env var to override the default AOA examples service URL.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aoa.action_machine.auth import NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.model import ParamsStub
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter
from aoa.maxitor.api.routes.sidebar import router as sidebar_router
from aoa.maxitor.model.core.actions.left_sidebar_action import GetLeftMenuSidebarDataAction
from aoa.maxitor.model.core.actions.load_aoa_service_action import LoadAOAServiceAction, LoadAOAServiceParams
from aoa.maxitor.model.diagrams.actions.domain_use_case_diagram_action import GetDomainUseCaseDiagramAction
from aoa.maxitor.model.diagrams.actions.full_graph_action import FullGraphAction
from aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action import GetLifecycleFiniteAutomatonAction
from aoa.maxitor.model.diagrams.actions.list_domains_action import ListDomainsAction
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.actions.list_node_types_action import ListNodeTypesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY

_DEFAULT_SERVICE_URL = "http://127.0.0.1:8001"


def create_app() -> FastAPI:
    """
    Create the Maxitor FastAPI application.

    AI-CORE-BEGIN
    ROLE: Build the ASGI app consumed by uvicorn, tests, and production hosting.
    CONTRACT: React assets are hosted separately; diagram JSON uses FastApiAdapter + shared machine.
    AI-CORE-END
    """
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    auth = NoAuthCoordinator(context=Context())

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Load AOA service graph into DuckDB, then build sidebar — single source of truth."""
        service_url = os.environ.get("AOA_SERVICE_URL", _DEFAULT_SERVICE_URL)
        load_result = await machine.run(
            Context(),
            LoadAOAServiceAction(),
            LoadAOAServiceParams(service_url=service_url),
        )
        sidebar_result = await machine.run(
            Context(),
            GetLeftMenuSidebarDataAction(),
            ParamsStub(),
            connections={DUCKDB_GRAPH_CONNECTION_KEY: load_result.graph_resource},
        )
        application.state.duckdb_graph = load_result.graph_resource
        application.state.sidebar_data = sidebar_result
        yield

    fastapi_app = FastAPI(title="Maxitor API", lifespan=lifespan)

    duckdb_per_request = PerCallConnection(factory=lambda: fastapi_app.state.duckdb_graph)

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
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_per_request},
        )
        .get(
            "/list-entities",
            ListEntitiesAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_per_request},
        )
        .get(
            "/list-node-types",
            ListNodeTypesAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_per_request},
        )
        .get(
            "/full-graph",
            FullGraphAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_per_request},
        )
        .get(
            "/lifecycle-finite-automaton",
            GetLifecycleFiniteAutomatonAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_per_request},
        )
        .get(
            "/domain-use-case-diagram",
            GetDomainUseCaseDiagramAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_per_request},
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
    """Lazily build ``app``; graph JSON is loaded in the ASGI lifespan, not at import time."""
    if name != "app":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    cached = _lazy_fastapi_app["app"]
    if cached is None:
        cached = create_app()
        _lazy_fastapi_app["app"] = cached
    return cached
