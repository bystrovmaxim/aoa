# packages/aoa-maxitor/src/aoa/maxitor/api/app.py
"""
FastAPI ASGI application for Maxitor.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose API endpoints and serve the bundled Vite React SPA.

The compiled frontend lives in ``src/aoa/maxitor/static/`` and is bundled into
the wheel so that ``pip install aoa-maxitor`` is the only server-side step.
Nginx proxies ``/maxitor/`` to this process; the SPA is built with ``--base=/maxitor/``.

ERD data and the interchange graph payload are exposed as JSON via :class:`aoa.action_machine.adapters.fastapi.FastApiAdapter`
routes mounted under ``/api/v1``. The React SPA renders both viewers in the browser.
Each diagram route reads the in-process DuckDB graph of the source it names in
``?source=<graph-json URL>``: ``GraphSourceMiddleware`` takes that source's entry from the
process-wide :class:`~aoa.maxitor.api.graph_store.GraphStore`, building it on the first read.
One process therefore holds one graph per source, not one graph for every user (#214).

Set ``AOA_SERVICE_URL`` env var to override the default AOA examples service URL.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from aoa.action_machine.auth import NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter
from aoa.maxitor.api.duckdb_graph_holder import DuckDBGraphHolder
from aoa.maxitor.api.graph_source_middleware import GraphSourceMiddleware
from aoa.maxitor.api.graph_store import GraphStore, build_graph_entry
from aoa.maxitor.api.routes.load import router as load_router
from aoa.maxitor.api.routes.sidebar import router as sidebar_router
from aoa.maxitor.model.diagrams.actions.domain_use_case_diagram_action import GetDomainUseCaseDiagramAction
from aoa.maxitor.model.diagrams.actions.full_graph_action import FullGraphAction
from aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action import GetLifecycleFiniteAutomatonAction
from aoa.maxitor.model.diagrams.actions.list_domains_action import ListDomainsAction
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.actions.list_node_types_action import ListNodeTypesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY

_STATIC_DIR = Path(__file__).parent.parent / "static"


def _positive_int_env(name: str, default: int) -> int:
    """Read a positive integer setting, refusing to start on anything else but naming it."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a positive integer, got {raw!r}") from None
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {raw!r}")
    return value


def _positive_seconds_env(name: str, default: float) -> float:
    """Read a positive number of seconds, refusing to start on anything else but naming it."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a positive number, got {raw!r}") from None
    if value <= 0:
        raise ValueError(f"{name} must be a positive number, got {raw!r}")
    return value


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
        application.state.machine = machine
        application.state.graph_store = store
        yield

    fastapi_app = FastAPI(title="Maxitor API", lifespan=lifespan)

    store = GraphStore(
        partial(build_graph_entry, machine),
        max_graphs=_positive_int_env("MAXITOR_MAX_GRAPHS", 50),
        idle_seconds=_positive_seconds_env("MAXITOR_GRAPH_IDLE_SECONDS", 3600.0),
        max_concurrent_builds=_positive_int_env("MAXITOR_MAX_CONCURRENT_BUILDS", 4),
    )
    fastapi_app.state.graph_store = store

    duckdb_graph = DuckDBGraphHolder()

    # Installed first, so CORS is added outside it afterwards (the last added is the outermost):
    # the middleware's 400, 422 and 503 then carry the CORS headers, including the exposed
    # Retry-After a client on another origin reads to time its retry.
    fastapi_app.add_middleware(GraphSourceMiddleware)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["Retry-After"],
    )
    fastapi_app.include_router(sidebar_router)
    fastapi_app.include_router(load_router)

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
        .get(
            "/lifecycle-finite-automaton",
            GetLifecycleFiniteAutomatonAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_graph},
        )
        .get(
            "/domain-use-case-diagram",
            GetDomainUseCaseDiagramAction,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: duckdb_graph},
        )
        .build()
    )
    fastapi_app.mount("/api/v1", action_subapp)

    @fastapi_app.get("/api/health", tags=["health"])
    async def health(request: Request) -> dict[str, Any]:
        """Report the store's load, so an operator can see it without a debugger."""
        graph_store = request.app.state.graph_store
        return {
            "status": "ok",
            "graphs_held": graph_store.held,
            "builds_running": graph_store.running,
            "builds_queued": graph_store.queued,
        }

    if _STATIC_DIR.exists():
        fastapi_app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")

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
