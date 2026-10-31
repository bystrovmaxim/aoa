# packages/maxitor/front/src/maxitor/front/api/app.py
"""
FastAPI ASGI application for Maxitor.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose API endpoints and serve the bundled Vite React SPA.

The compiled frontend lives in ``src/maxitor/front/static/`` and is bundled into
the wheel so that ``pip install maxitor`` is the only server-side step.
Nginx proxies ``/maxitor/`` to this process; the SPA is built with ``--base=/maxitor/``.

ERD data and the interchange graph payload are exposed as JSON via :class:`aoa.action_machine.adapters.fastapi.FastApiAdapter`
routes mounted under ``/api/v1``. The React SPA renders both viewers in the browser.

Static answers are cached by name — a content-hashed asset for a year, ``index.html`` revalidated
on every open — and every answer above 500 bytes is gzipped when the client accepts gzip.

Each diagram route reads the in-process DuckDB graph of the source it names in
``?source=<graph-json URL>``: ``GraphSourceMiddleware`` takes that source's entry from the
process-wide :class:`~maxitor.front.api.graph_store.GraphStore`, building it on the first read.
One process therefore holds one graph per source, not one graph for every user (#214).

Rooms (#271) run over one WebSocket route of the same adapter,
``/api/v1/rooms/{room_id}/live``: every message is an action over the process-wide
``RoomRegistry``. ``/api/meta/app-info`` answers the running version and client build
from a second adapter app, outside the paths ``GraphSourceMiddleware`` guards.
``MAXITOR_ROOM_ORIGINS`` lists extra browser origins allowed to join a room (comma
separated), for a client served from another address, such as the Vite dev server.

Held graphs are kept current (#271): ``GET /api/v1/graph-fingerprint`` answers from memory
and marks the source watched, and a clock started in the lifespan runs
``CheckDueSourcesAction`` every ten seconds, which asks each watched, due source whether it
changed and rebuilds it when it did. The clock decides nothing; the actions do.

Histories (spec 037) are opened from a third adapter app, ``/api/history``, outside the
paths ``GraphSourceMiddleware`` guards: a history's read key arrives only in the header
``X-Maxitor-History-Key``, which ``HistoryKeyAuthCoordinator`` puts in the request's context.
A version of a history is then read like any graph, its source being the port's version URL.
``MAXITOR_PUBLIC_PORT`` names Maxitor's own port, through which public GitHub links are read;
without it they are refused. uvicorn's request lines are written without their query.

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
from fastapi.responses import JSONResponse
from maxitor.front.api.access_log import install as install_access_log
from maxitor.front.api.cached_static_files import CachedStaticFiles
from maxitor.front.api.duckdb_graph_holder import DuckDBGraphHolder
from maxitor.front.api.graph_source_middleware import GraphSourceMiddleware, current_mapped, current_pair
from maxitor.front.api.graph_store import GraphStore, build_graph_entry
from maxitor.front.api.history_key_auth_coordinator import HistoryKeyAuthCoordinator
from maxitor.front.api.routes.load import router as load_router
from maxitor.front.api.routes.sidebar import router as sidebar_router
from maxitor.front.model.core.actions.app_info_action import AppInfoAction
from maxitor.front.model.core.actions.check_due_sources_action import CheckDueSourcesAction
from maxitor.front.model.core.actions.check_history_action import CheckHistoryAction
from maxitor.front.model.core.actions.check_source_action import CheckSourceAction
from maxitor.front.model.core.actions.get_own_graph_json_action import GetOwnGraphJsonAction
from maxitor.front.model.core.actions.graph_fingerprint_action import GraphFingerprintAction
from maxitor.front.model.core.actions.history_versions_action import HistoryVersionsAction
from maxitor.front.model.core.actions.open_history_action import OpenHistoryAction
from maxitor.front.model.core.history_address import (
    HistoryAddressError,
    PublicHistoriesNotSetUpError,
    parse_version_source,
)
from maxitor.front.model.core.history_errors import HistoryNotFoundError, HistoryUnreachableError, TooManyWrongKeysError
from maxitor.front.model.core.resources.graph_source_gateway import GRAPH_SOURCE_CONNECTION_KEY, GraphSourceGateway
from maxitor.front.model.core.resources.graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from maxitor.front.model.core.resources.history_access import HISTORY_ACCESS_CONNECTION_KEY, HistoryAccess
from maxitor.front.model.core.resources.history_store import HISTORY_STORE_CONNECTION_KEY, HistoryStore
from maxitor.front.model.core.resources.open_tabs_registry import OPEN_TABS_CONNECTION_KEY, OpenTabsRegistry
from maxitor.front.model.core.resources.own_model_graph_resource import (
    OWN_MODEL_GRAPH_CONNECTION_KEY,
    OwnModelGraphResource,
)
from maxitor.front.model.core.resources.repo_graph_port_gateway import (
    REPO_GRAPH_PORT_CONNECTION_KEY,
    RepoGraphPortGateway,
)
from maxitor.front.model.core.resources.source_checks import SOURCE_CHECKS_CONNECTION_KEY, SourceChecks
from maxitor.front.model.core.resources.static_bundle_resource import (
    STATIC_BUNDLE_CONNECTION_KEY,
    StaticBundleResource,
)
from maxitor.front.model.diagrams.actions.compare_element_action import CompareElementAction, ElementNotComparedError
from maxitor.front.model.diagrams.actions.compare_versions_action import CompareVersionsAction
from maxitor.front.model.diagrams.actions.domain_use_case_diagram_action import GetDomainUseCaseDiagramAction
from maxitor.front.model.diagrams.actions.full_graph_action import FullGraphAction
from maxitor.front.model.diagrams.actions.get_lifecycle_finite_automaton_action import (
    GetLifecycleFiniteAutomatonAction,
)
from maxitor.front.model.diagrams.actions.list_domains_action import _LIST_DOMAINS_DISTINCT_COLORS, ListDomainsAction
from maxitor.front.model.diagrams.actions.list_entities_action import ListEntitiesAction
from maxitor.front.model.diagrams.actions.list_entity_kinds_action import ListEntityKindsAction
from maxitor.front.model.diagrams.actions.list_node_types_action import ListNodeTypesAction
from maxitor.front.model.diagrams.actions.map_area_action import MapAreaAction, MapAreaNotFoundError
from maxitor.front.model.diagrams.actions.map_changes_action import MapChangesAction
from maxitor.front.model.diagrams.actions.map_overview_action import MapOverviewAction
from maxitor.front.model.diagrams.resources.comparison_store import (
    COMPARISON_STORE_CONNECTION_KEY,
    ComparisonRefusedError,
    ComparisonStore,
    NotComparingError,
)
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY
from maxitor.front.model.diagrams.resources.map_store import (
    MAP_STORE_CONNECTION_KEY,
    MapRefusedError,
    MapStore,
    NoGraphError,
)
from maxitor.front.model.rooms.actions import (
    DisconnectTabAction,
    FollowAction,
    JoinRoomAction,
    LeaveRoomAction,
    ReloadSourceForRoomAction,
    RenameParticipantAction,
    ReportPageAction,
    SeedPageSettingsAction,
    SetPageSettingAction,
    SetRoomVersionAction,
    StopFollowingAction,
)
from maxitor.front.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry
from starlette.middleware.gzip import GZipMiddleware

from aoa.action_machine.auth import NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.model import ParamsStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter

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


def _origins_env(name: str) -> tuple[str, ...]:
    """Read a comma-separated list of origins, ignoring blanks."""
    return tuple(origin.strip() for origin in os.environ.get(name, "").split(",") if origin.strip())


def _map_scope(source: str) -> str:
    """What the places on a map are kept for: a version's history, or the source itself."""
    version = parse_version_source(source)
    return version[0] if version else source


def _map_store(fastapi_app: FastAPI) -> MapStore:
    """The maps of versions, laid out once and kept on disk (spec 040)."""
    maps = MapStore(
        Path(os.environ.get("MAXITOR_MAP_CACHE") or Path.home() / ".cache" / "maxitor" / "map"),
        graph=current_mapped,
        scope=_map_scope,
        colours=_LIST_DOMAINS_DISTINCT_COLORS,
        immutable=lambda source: parse_version_source(source) is not None,
        pair=current_pair,
    )
    fastapi_app.state.maps = maps
    return maps


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
    graph_source = GraphSourceGateway()
    rooms = RoomRegistry(allowed_origins=_origins_env("MAXITOR_ROOM_ORIGINS"))
    rooms.bind(machine)
    bundle = StaticBundleResource(_STATIC_DIR)
    open_tabs = OpenTabsRegistry()
    source_checks = SourceChecks()
    # Maxitor's own port, for public GitHub links only (spec 037, FR-003b); read here, never in an action.
    port_gateway = RepoGraphPortGateway(os.environ.get("MAXITOR_PUBLIC_PORT", "").strip() or None)
    histories = HistoryStore(max_histories=_positive_int_env("MAXITOR_MAX_HISTORIES", 50))
    history_access = HistoryAccess()
    install_access_log()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.machine = machine
        application.state.graph_store = store
        # The clock only runs the action that decides which sources are due (spec 028, FR-071).
        source_checks.start(CheckDueSourcesAction, ParamsStub())
        yield
        await source_checks.close()
        await rooms.close()
        await graph_source.aclose()
        await port_gateway.aclose()

    fastapi_app = FastAPI(title="Maxitor API", lifespan=lifespan)

    store = GraphStore(
        partial(build_graph_entry, machine, graph_source),
        max_graphs=_positive_int_env("MAXITOR_MAX_GRAPHS", 50),
        max_concurrent_builds=_positive_int_env("MAXITOR_MAX_CONCURRENT_BUILDS", 4),
    )
    fastapi_app.state.graph_store = store
    fastapi_app.state.rooms = rooms
    graphs = GraphStoreController(store)
    check_connections = {GRAPH_STORE_CONNECTION_KEY: graphs, GRAPH_SOURCE_CONNECTION_KEY: graph_source, ROOM_REGISTRY_KEY: rooms}
    history_connections = {
        GRAPH_SOURCE_CONNECTION_KEY: graph_source,
        REPO_GRAPH_PORT_CONNECTION_KEY: port_gateway,
        HISTORY_STORE_CONNECTION_KEY: histories,
        HISTORY_ACCESS_CONNECTION_KEY: history_access,
    }
    source_checks.bind(
        machine,
        {
            CheckDueSourcesAction: {
                **check_connections,
                OPEN_TABS_CONNECTION_KEY: open_tabs,
                HISTORY_STORE_CONNECTION_KEY: histories,
                REPO_GRAPH_PORT_CONNECTION_KEY: port_gateway,
            },
            CheckSourceAction: check_connections,
            CheckHistoryAction: {REPO_GRAPH_PORT_CONNECTION_KEY: port_gateway, HISTORY_STORE_CONNECTION_KEY: histories, ROOM_REGISTRY_KEY: rooms},
        },
    )
    # GraphSourceMiddleware runs CheckVersionAccessAction before a history's version is handed over.
    fastapi_app.state.machine = machine
    fastapi_app.state.history_connections = {
        REPO_GRAPH_PORT_CONNECTION_KEY: port_gateway,
        HISTORY_STORE_CONNECTION_KEY: histories,
        HISTORY_ACCESS_CONNECTION_KEY: history_access,
    }

    duckdb_graph = DuckDBGraphHolder()
    maps = _map_store(fastapi_app)
    # Two versions compared once per pair, whoever reads them (spec 038, research R9).
    comparisons = ComparisonStore(pair=current_pair)
    fastapi_app.state.comparisons = comparisons

    _install_middleware(fastapi_app)

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
            "/list-entity-kinds",
            ListEntityKindsAction,
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
        .get(
            "/graph-fingerprint",
            GraphFingerprintAction,
            connections={
                GRAPH_STORE_CONNECTION_KEY: graphs,
                OPEN_TABS_CONNECTION_KEY: open_tabs,
                SOURCE_CHECKS_CONNECTION_KEY: source_checks,
            },
        )
        .get(
            "/compare",
            CompareVersionsAction,
            connections={COMPARISON_STORE_CONNECTION_KEY: comparisons},
        )
        .get(
            "/compare-element",
            CompareElementAction,
            connections={COMPARISON_STORE_CONNECTION_KEY: comparisons},
        )
        .get(
            "/map/overview",
            MapOverviewAction,
            connections={MAP_STORE_CONNECTION_KEY: maps},
        )
        .get(
            "/map/area",
            MapAreaAction,
            connections={MAP_STORE_CONNECTION_KEY: maps},
        )
        .get(
            "/map/changes",
            MapChangesAction,
            connections={MAP_STORE_CONNECTION_KEY: maps},
        )
        .websocket(
            "/rooms/{room_id}/live",
            on_open=JoinRoomAction,
            messages={
                "page": ReportPageAction,
                "activity": ReportPageAction,
                "setting": SetPageSettingAction,
                "seed": SeedPageSettingsAction,
                "rename": RenameParticipantAction,
                "follow": FollowAction,
                "stop_following": StopFollowingAction,
                "leave": LeaveRoomAction,
                "reload": ReloadSourceForRoomAction,
                "version": SetRoomVersionAction,
            },
            on_close=DisconnectTabAction,
            relay=frozenset({"pointer", "viewport", "focus", "click"}),
            relay_key=ROOM_REGISTRY_KEY,
            # Pointer 20 + screen 20 + focus 10 a second at most (spec 029, R3), with room to spare.
            max_messages_per_second=80,
            connections={
                ROOM_REGISTRY_KEY: rooms,
                GRAPH_STORE_CONNECTION_KEY: graphs,
                GRAPH_SOURCE_CONNECTION_KEY: graph_source,
                STATIC_BUNDLE_CONNECTION_KEY: bundle,
                HISTORY_STORE_CONNECTION_KEY: histories,
                HISTORY_ACCESS_CONNECTION_KEY: history_access,
            },
            description="A room: everyone looking at one service, or one version of its history, together",
        )
        .build()
    )
    _answer_comparison_refusals(action_subapp)
    fastapi_app.mount("/api/v1", action_subapp)

    meta_subapp = (
        FastApiAdapter(machine=machine, auth_coordinator=auth, title="Maxitor meta", version="1.0.0")
        .get("/app-info", AppInfoAction, connections={STATIC_BUNDLE_CONNECTION_KEY: bundle})
        .build()
    )
    fastapi_app.mount("/api/meta", meta_subapp)

    history_subapp = (
        FastApiAdapter(machine=machine, auth_coordinator=HistoryKeyAuthCoordinator(), title="Maxitor histories", version="1.0.0")
        .get("/open", OpenHistoryAction, connections={**history_connections, OPEN_TABS_CONNECTION_KEY: open_tabs})
        .get("/versions", HistoryVersionsAction, connections={**history_connections, OPEN_TABS_CONNECTION_KEY: open_tabs})
        .build()
    )
    _answer_history_refusals(history_subapp)
    fastapi_app.mount("/api/history", history_subapp)

    # Maxitor's own model, at the path Maxitor adds to a bare service address (spec 029, FR-060).
    own_model = OwnModelGraphResource(machine.graph_coordinator)
    own_model_subapp = (
        FastApiAdapter(machine=machine, auth_coordinator=auth, title="Maxitor model", version="1.0.0")
        .get("/graph-json", GetOwnGraphJsonAction, connections={OWN_MODEL_GRAPH_CONNECTION_KEY: own_model})
        .build()
    )
    fastapi_app.mount("/examples/model", own_model_subapp)

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
        fastapi_app.mount("/", CachedStaticFiles(directory=_STATIC_DIR, html=True), name="static")

    return fastapi_app


def _answer_history_refusals(app: FastAPI) -> None:
    """Give each refusal of a history request its status and its fixed words (the history routes' contract in specs/037)."""
    answers: dict[type[Exception], tuple[int, dict[str, str]]] = {
        HistoryAddressError: (400, {}),
        PublicHistoriesNotSetUpError: (400, {}),
        HistoryNotFoundError: (404, {}),
        TooManyWrongKeysError: (429, {}),
        HistoryUnreachableError: (503, {"Retry-After": "5"}),
    }
    for error, (status, headers) in answers.items():

        async def answer(_request: Request, exc: Exception, status: int = status, headers: dict[str, str] = headers) -> JSONResponse:
            return JSONResponse(status_code=status, content={"detail": str(exc)}, headers=headers)

        app.add_exception_handler(error, answer)


def _install_middleware(fastapi_app: FastAPI) -> None:
    """The middleware every read passes through, in order, and the two hand-written routers."""
    # Installed first, so CORS is added outside it afterwards (the last added is the outermost):
    # the middleware's 400, 422 and 503 then carry the CORS headers, including the exposed
    # Retry-After a client on another origin reads to time its retry.
    fastapi_app.add_middleware(GraphSourceMiddleware)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["Retry-After", "ETag"],
    )
    # Added last, so gzip is the outermost middleware and sees every answer, the refusals
    # of GraphSourceMiddleware included (research R1). Level 6 rather than 9: the bundle is
    # compressed once per new visitor and then cached, so a few per cent of bytes is not
    # worth the extra CPU per first open.
    fastapi_app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=6)
    fastapi_app.include_router(sidebar_router)
    fastapi_app.include_router(load_router)


def _answer_comparison_refusals(app: FastAPI) -> None:
    """Give each refusal of a comparison read its status (the comparison reads' contract in specs/038)."""
    answers: dict[type[Exception], int] = {
        NotComparingError: 400,
        ElementNotComparedError: 404,
        MapAreaNotFoundError: 404,
        MapRefusedError: 422,
        NoGraphError: 400,
        ComparisonRefusedError: 422,
    }
    for error, status in answers.items():

        async def answer(_request: Request, exc: Exception, status: int = status) -> JSONResponse:
            return JSONResponse(status_code=status, content={"detail": str(exc)})

        app.add_exception_handler(error, answer)


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
