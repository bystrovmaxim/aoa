# packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py
"""
FastApiAdapter — HTTP adapter for ActionMachine using FastAPI.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

FastApiAdapter converts Actions into FastAPI HTTP endpoints. One call to a
protocol method (post/get/put/delete/patch) registers one endpoint.
All protocol methods return ``self`` for fluent chaining:

    app = adapter \\
        .get("/api/v1/ping", PingAction, tags=["system"]) \\
        .post("/api/v1/orders", CreateOrderAction, tags=["orders"]) \\
        .build()

OpenAPI documentation is generated automatically from metadata already declared
in code: field descriptions from ``Field(description=...)``, constraints from
``Field(gt=0, min_length=3, pattern=...)``, summary from ``@meta``, and tags
from route registration arguments.

═══════════════════════════════════════════════════════════════════════════════
REQUIRED AUTHENTICATION
═══════════════════════════════════════════════════════════════════════════════

The ``auth_coordinator`` argument is required (inherited from ``BaseAdapter``).
This prevents accidental auth omission: ``auth_coordinator=None`` fails fast
with ``TypeError`` instead of becoming a silent production bug. For open APIs,
use ``NoAuthCoordinator`` explicitly:

    from aoa.action_machine.intents.check_roles import NoAuthCoordinator

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(context=Context()),
    )

═══════════════════════════════════════════════════════════════════════════════
MAPPER NAMING CONVENTION
═══════════════════════════════════════════════════════════════════════════════

Each mapper is named by what it RETURNS:

    params_mapper   -> returns params   (transforms request -> params)
    response_mapper -> returns response (transforms result  -> response)

═══════════════════════════════════════════════════════════════════════════════
ENDPOINT GENERATION STRATEGIES
═══════════════════════════════════════════════════════════════════════════════

The adapter uses three endpoint generation strategies depending on HTTP method
and whether the params model has fields:

1. POST/PUT/PATCH with non-empty Params -> parameters are passed in JSON body.
   FastAPI validates the body using the Pydantic model.

2. GET/DELETE with non-empty Params -> parameters are passed via query/path.
   If URL has path params (e.g. ``{order_id}``), FastAPI extracts those from
   path and the rest from query string.

3. Any method with empty Params (no fields) -> endpoint takes no body/query.
   Empty Params instance is created inside the handler.

═══════════════════════════════════════════════════════════════════════════════
ERROR HANDLING
═══════════════════════════════════════════════════════════════════════════════

Exception handlers are registered at application level:

    AuthorizationError   -> HTTP 403 {"detail": "..."}
    ValidationFieldError -> HTTP 422 {"detail": "..."}

Unhandled exceptions are caught by middleware wrapping each request in
try/except and returning HTTP 500 for any error not handled above.

═══════════════════════════════════════════════════════════════════════════════
TESTING NOTE (HTTP routes)
═══════════════════════════════════════════════════════════════════════════════

Route and handler tests should use a real ``ActionProductMachine`` so
OpenAPI-related wiring and graph metadata match production.

To control results or speed, stub ``machine.run`` only — not the whole stack.

::

    Request body / query / path
              |
              v
    FastAPI validation / mappers  --->  auth_coordinator  --->  machine.run  ~~~~ stub
         ^___________________________ production ___________________________^
                                                                           ~~~~
                                                                optional AsyncMock

    response mapping / JSON response  <---  (after run)
         ^
         production

See ``BaseAdapter`` module docstring (ADAPTER TESTING CONTRACT) for the full
adapter-level picture.

═══════════════════════════════════════════════════════════════════════════════
HEALTH CHECK
═══════════════════════════════════════════════════════════════════════════════

Endpoint ``GET /health`` is added automatically during ``build()``.
Returns ``{"status": "ok"}``.

"""

# Ruff/isort lists first-party ``action_machine`` before FastAPI (known-first-party).
# pylint: disable=wrong-import-order
from __future__ import annotations

import inspect
import re
from collections.abc import Callable, Mapping
from typing import Annotated, Any, Self, get_origin

from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from aoa.action_machine.adapters.base_adapter import BaseAdapter
from aoa.action_machine.adapters.base_route_record import ensure_machine_params, ensure_protocol_response
from aoa.action_machine.auth.auth_coordinator_protocol import AuthCoordinatorProtocol
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.exceptions.check_access_decide_batch_size_exceeded_error import (
    CheckAccessDecideBatchSizeExceededError,
)
from aoa.action_machine.exceptions.validation_field_error import ValidationFieldError
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.resources.per_call_connection import ConnectionValue, resolve_connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.fastapi.manifest import Manifest, build_manifest
from aoa.fastapi.permissions import build_action_index, resolve_verdicts
from aoa.fastapi.permissions_schema import ResolveRequest, ResolveResponse
from aoa.fastapi.reserved_route_path_error import ReservedRoutePathError
from aoa.fastapi.route_record import FastApiRouteRecord
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

# ═════════════════════════════════════════════════════════════════════════════
# Module-level helper functions
# ═════════════════════════════════════════════════════════════════════════════

_PATH_PARAM_PATTERN: re.Pattern[str] = re.compile(r"\{(\w+)\}")


def _fastapi_query_param_annotation(field_name: str, field_info: Any, path_params: set[str]) -> Any:
    """
    Build the FastAPI endpoint parameter annotation for one query field.

    FastAPI treats bare ``list[...]`` on GET handlers as a JSON body field; wrap with
    :class:`fastapi.Query` so list values bind from repeated query keys (or a single
    value, depending on client) instead.
    """
    if field_name in path_params:
        return field_info.annotation if field_info.annotation is not None else str
    ann = field_info.annotation
    if ann is None:
        return str
    if get_origin(ann) is list:
        if field_info.is_required():
            return Annotated[ann, Query()]
        return Annotated[ann, Query(default_factory=list)]
    return ann


def _fastapi_route_label(record: FastApiRouteRecord) -> str:
    return f"{record.method} {record.path}"


def _get_action_class_description(
    action_class: type,
    *,
    coordinator: NodeGraphCoordinator | None = None,
) -> str:
    """
    Extract description from action ``@meta`` declaration.

    Used to auto-fill endpoint summary when summary is not provided explicitly
    during route registration.

    Args:
        action_class: action class.

    Returns:
        Description string from the node graph, ``@meta`` scratch, or empty string.
    """
    if coordinator is not None:
        try:
            node = coordinator.get_node_by_id(
                TypeIntrospection.full_qualname(action_class),
                ActionGraphNode.NODE_TYPE,
            )
        except (LookupError, RuntimeError):
            node = None
        if node is not None:
            return str(node.properties.get("description", "") or "")

    meta_info = getattr(action_class, "_meta_info", None)
    if meta_info and isinstance(meta_info, dict):
        return str(meta_info.get("description", ""))
    return ""


def _get_model_fields(model: type) -> dict[str, Any]:
    """
    Return Pydantic model fields as a dictionary.

    For Pydantic ``BaseModel`` uses ``model_fields``.
    For other types returns an empty dict.

    Args:
        model: model class (Pydantic ``BaseModel`` or another type).

    Returns:
        Dict of ``{field_name: FieldInfo}`` or empty dict.
    """
    if isinstance(model, type) and issubclass(model, BaseModel):
        return model.model_fields
    return {}


def _extract_path_params(path: str) -> set[str]:
    """
    Extract path-parameter names from URL template.

    Args:
        path: URL path with placeholders like ``{param_name}``.

    Returns:
        Set of path-parameter names.
    """
    return set(_PATH_PARAM_PATTERN.findall(path))


def _has_body_method(method: str) -> bool:
    """
    Return whether HTTP method supports request body.

    POST/PUT/PATCH support body.
    GET/DELETE do not use body in this adapter.

    Args:
        method: uppercase HTTP method.

    Returns:
        True if method supports body.
    """
    return method in ("POST", "PUT", "PATCH")


# ═════════════════════════════════════════════════════════════════════════════
# Endpoint function factories
# ═════════════════════════════════════════════════════════════════════════════


def _make_endpoint_with_body(
    record: FastApiRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: AuthCoordinatorProtocol,
) -> Callable[..., Any]:
    """
    Create endpoint for methods with JSON body (POST, PUT, PATCH).

    ``body`` parameter is annotated with concrete Pydantic model.
    FastAPI validates request body and generates OpenAPI schema automatically.

    Args:
        record: route configuration.
        machine: action execution machine.
        auth_coordinator: authentication coordinator (required).

    Returns:
        Async endpoint function for ``app.add_api_route()``.
    """
    req_model = record.effective_request_model
    has_params_mapper = record.params_mapper is not None
    has_response_mapper = record.response_mapper is not None

    async def endpoint(request: Request, body: Any) -> Any:
        if has_params_mapper:
            params = record.params_mapper(body)  # type: ignore[misc]
        else:
            params = body

        ensure_machine_params(
            params,
            record.params_type,
            adapter="FastAPI",
            route_label=_fastapi_route_label(record),
        )

        context = await auth_coordinator.process(request)
        if context is None:
            raise AuthorizationError("Authentication required")

        connections = resolve_connections(record.connections)

        action = record.action_class()
        result = await machine.run(context, action, params, connections)

        if has_response_mapper:
            mapped = record.response_mapper(result)  # type: ignore[misc]
            ensure_protocol_response(
                mapped,
                record.effective_response_model,
                adapter="FastAPI",
                route_label=_fastapi_route_label(record),
            )
            return mapped
        return result

    sig_params = [
        inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
        inspect.Parameter("body", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=req_model),
    ]
    endpoint.__signature__ = inspect.Signature(sig_params)  # type: ignore[attr-defined]

    return endpoint


def _make_endpoint_with_query(
    record: FastApiRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: AuthCoordinatorProtocol,
) -> Callable[..., Any]:
    """
    Create endpoint for GET/DELETE with query/path parameters.

    Each Params model field becomes a function argument. FastAPI resolves which
    parameters come from path and which from query string using annotations and
    route path placeholders.

    Args:
        record: route configuration.
        machine: action execution machine.
        auth_coordinator: authentication coordinator (required).

    Returns:
        Async endpoint function for ``app.add_api_route()``.
    """
    req_model = record.effective_request_model
    has_params_mapper = record.params_mapper is not None
    has_response_mapper = record.response_mapper is not None
    model_fields = _get_model_fields(req_model)
    path_params = _extract_path_params(record.path)

    async def endpoint(request: Request, **kwargs: Any) -> Any:
        body = req_model(**kwargs)

        if has_params_mapper:
            params = record.params_mapper(body)  # type: ignore[misc]
        else:
            params = body

        ensure_machine_params(
            params,
            record.params_type,
            adapter="FastAPI",
            route_label=_fastapi_route_label(record),
        )

        context = await auth_coordinator.process(request)
        if context is None:
            raise AuthorizationError("Authentication required")

        connections = resolve_connections(record.connections)

        action = record.action_class()
        result = await machine.run(context, action, params, connections)

        if has_response_mapper:
            mapped = record.response_mapper(result)  # type: ignore[misc]
            ensure_protocol_response(
                mapped,
                record.effective_response_model,
                adapter="FastAPI",
                route_label=_fastapi_route_label(record),
            )
            return mapped
        return result

    sig_params = [
        inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
    ]

    for field_name, field_info in model_fields.items():
        annotation = _fastapi_query_param_annotation(field_name, field_info, path_params)

        if field_name in path_params:
            if field_info.default is not None and not field_info.is_required():
                sig_params.append(
                    inspect.Parameter(
                        field_name,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=annotation,
                        default=field_info.default,
                    )
                )
            else:
                sig_params.append(
                    inspect.Parameter(
                        field_name,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=annotation,
                    )
                )
        else:
            default = field_info.default if not field_info.is_required() else inspect.Parameter.empty
            sig_params.append(
                inspect.Parameter(
                    field_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotation,
                    default=default,
                )
            )

    endpoint.__signature__ = inspect.Signature(sig_params)  # type: ignore[attr-defined]

    return endpoint


def _make_endpoint_no_params(
    record: FastApiRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: AuthCoordinatorProtocol,
) -> Callable[..., Any]:
    """
    Create endpoint for actions with empty Params (no fields).

    Endpoint accepts no body/query parameters. Empty Params instance is created
    inside handler.

    Args:
        record: route configuration.
        machine: action execution machine.
        auth_coordinator: authentication coordinator (required).

    Returns:
        Async endpoint function for ``app.add_api_route()``.
    """
    req_model = record.effective_request_model
    has_params_mapper = record.params_mapper is not None
    has_response_mapper = record.response_mapper is not None

    async def endpoint(request: Request) -> Any:
        body = req_model()

        if has_params_mapper:
            params = record.params_mapper(body)  # type: ignore[misc]
        else:
            params = body

        ensure_machine_params(
            params,
            record.params_type,
            adapter="FastAPI",
            route_label=_fastapi_route_label(record),
        )

        context = await auth_coordinator.process(request)
        if context is None:
            raise AuthorizationError("Authentication required")

        connections = resolve_connections(record.connections)

        action = record.action_class()
        result = await machine.run(context, action, params, connections)

        if has_response_mapper:
            mapped = record.response_mapper(result)  # type: ignore[misc]
            ensure_protocol_response(
                mapped,
                record.effective_response_model,
                adapter="FastAPI",
                route_label=_fastapi_route_label(record),
            )
            return mapped
        return result

    return endpoint


def _make_endpoint(
    record: FastApiRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: AuthCoordinatorProtocol,
) -> Callable[..., Any]:
    """
    Endpoint factory for FastAPI.

    Chooses generation strategy by HTTP method and Params model shape:

    1. Empty model (no fields) -> endpoint without parameters.
    2. POST/PUT/PATCH with fields -> endpoint with JSON body.
    3. GET/DELETE with fields -> endpoint with query/path parameters.

    Args:
        record: route configuration.
        machine: action execution machine.
        auth_coordinator: authentication coordinator (required).

    Returns:
        Async function suitable for ``app.add_api_route()``.
    """
    model_fields = _get_model_fields(record.effective_request_model)

    if not model_fields:
        return _make_endpoint_no_params(record, machine, auth_coordinator)

    if _has_body_method(record.method):
        return _make_endpoint_with_body(record, machine, auth_coordinator)

    return _make_endpoint_with_query(record, machine, auth_coordinator)


# ═════════════════════════════════════════════════════════════════════════════
# Middleware
# ═════════════════════════════════════════════════════════════════════════════


class _CatchAllErrorsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches unhandled exceptions.

    Wraps each request in try/except and guarantees HTTP 500 for uncaught errors.
    """

    async def dispatch(
        self,
        request: StarletteRequest,
        call_next: Callable[..., Any],
    ) -> StarletteResponse:
        try:
            response: StarletteResponse = await call_next(request)
            return response
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )


# ═════════════════════════════════════════════════════════════════════════════
# Adapter class
# ═════════════════════════════════════════════════════════════════════════════


class FastApiAdapter(BaseAdapter[FastApiRouteRecord]):
    """
    FastAPI-based HTTP adapter for ActionMachine.

    Inherits ``BaseAdapter[FastApiRouteRecord]`` and exposes protocol methods
    ``post/get/put/delete/patch`` for endpoint registration. All protocol
    methods return ``self`` for fluent chaining. ``build()`` finalizes the
    chain and creates FastAPI application.

    ``auth_coordinator`` is required (inherited from ``BaseAdapter``). For open
    APIs, use ``NoAuthCoordinator(context=Context())`` explicitly.

    Attributes:
        _title : str
            API title for OpenAPI/Swagger UI.

        _version : str
            API version for OpenAPI.

        _description : str
            API description for OpenAPI (Markdown supported).
    """

    #: Paths owned by the adapter's own bespoke routes (``build()`` registers these before looping
    #: over ``self._routes``, so an app-registered route on the same path would be silently
    #: shadowed by Starlette's first-match-wins routing — see ``ReservedRoutePathError``).
    _RESERVED_PATHS: frozenset[str] = frozenset({"/health", "/permissions/resolve"})

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: AuthCoordinatorProtocol,
        *,
        title: str = "ActionMachine API",
        version: str = "0.1.0",
        description: str = "",
    ) -> None:
        """
        Initialize FastAPI adapter.

        Args:
            machine: action execution machine (required).
            auth_coordinator: authentication coordinator (required).
                For open APIs use ``NoAuthCoordinator(context=Context())``. ``None`` is invalid.
            title: API title for OpenAPI/Swagger UI.
            version: API version for OpenAPI.
            description: API description for OpenAPI (Markdown supported).
        """
        super().__init__(
            machine=machine,
            auth_coordinator=auth_coordinator,
        )
        self._title: str = title
        self._version: str = version
        self._description: str = description

    # ─────────────────────────────────────────────────────────────────────
    # Properties
    # ─────────────────────────────────────────────────────────────────────

    @property
    def title(self) -> str:
        """API title for OpenAPI."""
        return self._title

    @property
    def version(self) -> str:
        """API version for OpenAPI."""
        return self._version

    @property
    def api_description(self) -> str:
        """API description for OpenAPI."""
        return self._description

    # ─────────────────────────────────────────────────────────────────────
    # Internal registration method (fluent)
    # ─────────────────────────────────────────────────────────────────────

    def _register(
        self,
        method: str,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
        *,
        connections: Mapping[str, ConnectionValue] | None = None,
        auth_coordinator: AuthCoordinatorProtocol | None = None,
    ) -> Self:
        """
        Create ``FastApiRouteRecord``, append to ``_routes``, and return ``self``.

        If ``summary`` is empty, fill it from action ``@meta`` description.
        ``auth_coordinator``, when given, overrides the adapter's default coordinator
        for this route only (see :meth:`~aoa.action_machine.adapters.base_adapter.BaseAdapter.effective_auth_coordinator`).

        Raises:
            ReservedRoutePathError: ``path`` collides with one of the adapter's own bespoke
                routes (``_RESERVED_PATHS``) — registering it here would be silently
                shadowed at ``build()`` time rather than actually reachable.
        """
        if path in self._RESERVED_PATHS:
            raise ReservedRoutePathError(path, method)

        effective_summary = summary or _get_action_class_description(
            action_class,
            coordinator=self.graph_coordinator,
        )

        record = FastApiRouteRecord(
            action_class=action_class,
            request_model=request_model,
            response_model=response_model,
            params_mapper=params_mapper,
            response_mapper=response_mapper,
            connections=connections,
            auth_coordinator=auth_coordinator,
            method=method,
            path=path,
            tags=tuple(tags or ()),
            summary=effective_summary,
            description=description,
            operation_id=operation_id,
            deprecated=deprecated,
        )
        return self._add_route(record)

    # ─────────────────────────────────────────────────────────────────────
    # Protocol methods (fluent — return Self)
    # ─────────────────────────────────────────────────────────────────────

    def post(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
        *,
        connections: Mapping[str, ConnectionValue] | None = None,
        auth_coordinator: AuthCoordinatorProtocol | None = None,
    ) -> Self:
        """Register POST endpoint. Returns self for fluent chain."""
        return self._register(
            "POST", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated, connections=connections, auth_coordinator=auth_coordinator,
        )

    def get(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
        *,
        connections: Mapping[str, ConnectionValue] | None = None,
        auth_coordinator: AuthCoordinatorProtocol | None = None,
    ) -> Self:
        """Register GET endpoint. Returns self for fluent chain."""
        return self._register(
            "GET", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated, connections=connections, auth_coordinator=auth_coordinator,
        )

    def put(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
        *,
        connections: Mapping[str, ConnectionValue] | None = None,
        auth_coordinator: AuthCoordinatorProtocol | None = None,
    ) -> Self:
        """Register PUT endpoint. Returns self for fluent chain."""
        return self._register(
            "PUT", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated, connections=connections, auth_coordinator=auth_coordinator,
        )

    def delete(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
        *,
        connections: Mapping[str, ConnectionValue] | None = None,
        auth_coordinator: AuthCoordinatorProtocol | None = None,
    ) -> Self:
        """Register DELETE endpoint. Returns self for fluent chain."""
        return self._register(
            "DELETE", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated, connections=connections, auth_coordinator=auth_coordinator,
        )

    def patch(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
        *,
        connections: Mapping[str, ConnectionValue] | None = None,
        auth_coordinator: AuthCoordinatorProtocol | None = None,
    ) -> Self:
        """Register PATCH endpoint. Returns self for fluent chain."""
        return self._register(
            "PATCH", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated, connections=connections, auth_coordinator=auth_coordinator,
        )

    # ─────────────────────────────────────────────────────────────────────
    # FastAPI application build
    # ─────────────────────────────────────────────────────────────────────

    def build(self) -> FastAPI:
        """
        Create FastAPI application from registered routes.

        Initialization order:
        1. Create FastAPI app with OpenAPI metadata.
        2. Add middleware for uncaught exception handling.
        3. Register exception handlers.
        4. Register health check endpoint ``GET /health``.
        5. Register permissions endpoints (``POST /permissions/resolve``,
           ``GET /client-manifest.json``).
        6. Generate/register endpoint for each route.

        Returns:
            Ready-to-run FastAPI application.
        """
        app = FastAPI(
            title=self._title,
            version=self._version,
            description=self._description,
        )

        app.add_middleware(_CatchAllErrorsMiddleware)
        self._register_exception_handlers(app)
        self._register_health_check(app)
        self._register_permissions_endpoints(app)

        for record in self._routes:
            self._register_endpoint(app, record)

        return app

    # ─────────────────────────────────────────────────────────────────────
    # Endpoint generation
    # ─────────────────────────────────────────────────────────────────────

    def _register_endpoint(self, app: FastAPI, record: FastApiRouteRecord) -> None:
        """
        Generate and register one async endpoint from ``FastApiRouteRecord``.
        """
        endpoint = _make_endpoint(
            record=record,
            machine=self._machine,
            auth_coordinator=self.effective_auth_coordinator(record),
        )

        app.add_api_route(
            path=record.path,
            endpoint=endpoint,
            methods=[record.method],
            response_model=record.effective_response_model,
            tags=list(record.tags) if record.tags else None,
            summary=record.summary or None,
            description=record.description or None,
            operation_id=record.operation_id,
            deprecated=record.deprecated or None,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Exception handlers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _register_exception_handlers(app: FastAPI) -> None:
        """
        Register ActionMachine exception handlers at app level.

            AuthorizationError   -> HTTP 403 Forbidden
            ValidationFieldError -> HTTP 422 Unprocessable Entity
        """

        @app.exception_handler(AuthorizationError)
        async def handle_authorization_error(
            request: Request,
            exc: AuthorizationError,
        ) -> JSONResponse:
            return JSONResponse(
                status_code=403,
                content={"detail": str(exc)},
            )

        @app.exception_handler(ValidationFieldError)
        async def handle_validation_error(
            request: Request,
            exc: ValidationFieldError,
        ) -> JSONResponse:
            return JSONResponse(
                status_code=422,
                content={"detail": str(exc)},
            )

        @app.exception_handler(CheckAccessDecideBatchSizeExceededError)
        async def handle_batch_size_exceeded(
            request: Request,
            exc: CheckAccessDecideBatchSizeExceededError,
        ) -> JSONResponse:
            return JSONResponse(
                status_code=413,
                content={"detail": str(exc)},
            )

    # ─────────────────────────────────────────────────────────────────────
    # Permissions resolver + client manifest (issue #130)
    # ─────────────────────────────────────────────────────────────────────

    def _register_permissions_endpoints(self, app: FastAPI) -> None:
        """
        Add ``POST /permissions/resolve`` (list-shaped role-gate resolver, PR 1 + PR 2)
        and ``GET /client-manifest.json`` (endpoint catalog, chapter 3) — both issue #130.

        Registered as a bespoke route, not a ``BaseAction`` — it needs ``machine``
        and a full ``Context`` to call ``machine.check_access_decide`` on *other*
        actions, and ordinary aspects cannot reach either (see the module-level
        ``REQUIRED AUTHENTICATION`` note and the ADR for the full argument).

        Always calls ``auth_coordinator.process(request)``; a ``403`` (via the
        existing ``AuthorizationError`` handler) follows only
        when that returns ``None`` (e.g. invalid credentials on a strict
        coordinator) — a resolved anonymous ``Context`` (``NoAuthCoordinator``)
        proceeds normally, so ``@check_roles(GuestRole)`` actions resolve correctly
        for unauthenticated callers instead of being special-cased here.

        Deduplication and per-item error isolation (PR 2, chapter 2) live in
        :func:`~aoa.fastapi.permissions.resolve_verdicts`, not here — this endpoint
        only wires auth + the wire response around it.

        The catalog is a bespoke route for the same structural reason: it projects
        ``self._routes`` (see :func:`~aoa.fastapi.manifest.build_manifest`), a field
        an ordinary action cannot reach. It is built once here (``self._routes`` is
        already fixed by ``build()`` time) and is role-independent — the same manifest
        is returned to every authenticated caller, guest included.
        """
        machine = self._machine
        auth_coordinator = self._auth_coordinator
        action_index = build_action_index(self.graph_coordinator)
        # Projected once: self._routes is already fixed by the time build() runs
        # (every .post/.get/... has registered), so nothing is recomputed per request.
        manifest = build_manifest(self._routes)

        @app.post("/permissions/resolve", tags=["permissions"], response_model=ResolveResponse)
        async def resolve(request: Request, body: ResolveRequest) -> ResolveResponse:
            context = await auth_coordinator.process(request)
            if context is None:
                raise AuthorizationError("Authentication required")

            outcome = await resolve_verdicts(context, body.items, action_index, machine)
            return ResolveResponse(protocol=1, verdicts=outcome.verdicts)

        @app.get("/client-manifest.json", tags=["permissions"], response_model=Manifest)
        async def client_manifest(request: Request) -> Manifest:
            context = await auth_coordinator.process(request)
            if context is None:
                raise AuthorizationError("Authentication required")
            # Role-independent: the same manifest goes to every authenticated
            # caller, guest (NoAuthCoordinator) included.
            return manifest

    # ─────────────────────────────────────────────────────────────────────
    # Health check
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _register_health_check(app: FastAPI) -> None:
        """Add ``GET /health -> {"status": "ok"}`` endpoint."""

        @app.get("/health", tags=["system"])
        async def health_check() -> dict[str, str]:
            return {"status": "ok"}
