# src/action_machine/integrations/fastapi/adapter.py
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

    from action_machine.intents.auth import NoAuthCoordinator

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
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
HEALTH CHECK
═══════════════════════════════════════════════════════════════════════════════

Endpoint ``GET /health`` is added automatically during ``build()``.
Returns ``{"status": "ok"}``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.auth import NoAuthCoordinator
    from action_machine.integrations.fastapi import FastApiAdapter

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
        title="Orders API",
        version="0.1.0",
    )

    app = adapter \\
        .post("/api/v1/orders", CreateOrderAction, tags=["orders"]) \\
        .get("/api/v1/orders/{order_id}", GetOrderAction, tags=["orders"]) \\
        .get("/api/v1/ping", PingAction, tags=["system"]) \\
        .build()
"""

# Ruff/isort lists first-party ``action_machine`` before FastAPI (known-first-party).
# pylint: disable=wrong-import-order
from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from typing import Any, Self

from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from action_machine.adapters.base_adapter import BaseAdapter
from action_machine.adapters.base_route_record import (
    ensure_machine_params,
    ensure_protocol_response,
)
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.integrations.fastapi.route_record import FastApiRouteRecord
from action_machine.intents.context.context import Context
from action_machine.model.base_action import BaseAction
from action_machine.model.exceptions import AuthorizationError, ValidationFieldError
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ═════════════════════════════════════════════════════════════════════════════
# Module-level helper functions
# ═════════════════════════════════════════════════════════════════════════════

_PATH_PARAM_PATTERN: re.Pattern[str] = re.compile(r"\{(\w+)\}")


def _fastapi_route_label(record: FastApiRouteRecord) -> str:
    return f"{record.method} {record.path}"


def _get_meta_description(action_class: type) -> str:
    """
    Extract description from action ``@meta`` declaration.

    Used to auto-fill endpoint summary when summary is not provided explicitly
    during route registration.

    Args:
        action_class: action class.

    Returns:
        Description string from ``@meta`` or empty string.
    """
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
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Create endpoint for methods with JSON body (POST, PUT, PATCH).

    ``body`` parameter is annotated with concrete Pydantic model.
    FastAPI validates request body and generates OpenAPI schema automatically.

    Args:
        record: route configuration.
        machine: action execution machine.
        auth_coordinator: authentication coordinator (required).
        connections_factory: connections factory, or ``None``.

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
            context = Context()

        connections = None
        if connections_factory is not None:
            connections = connections_factory()

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
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
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
        connections_factory: connections factory, or ``None``.

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
            context = Context()

        connections = None
        if connections_factory is not None:
            connections = connections_factory()

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
        annotation = field_info.annotation if field_info.annotation is not None else str

        if field_name in path_params:
            if field_info.default is not None and not field_info.is_required():
                sig_params.append(inspect.Parameter(
                    field_name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotation, default=field_info.default,
                ))
            else:
                sig_params.append(inspect.Parameter(
                    field_name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotation,
                ))
        else:
            default = field_info.default if not field_info.is_required() else inspect.Parameter.empty
            sig_params.append(inspect.Parameter(
                field_name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=annotation, default=default,
            ))

    endpoint.__signature__ = inspect.Signature(sig_params)  # type: ignore[attr-defined]

    return endpoint


def _make_endpoint_no_params(
    record: FastApiRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Create endpoint for actions with empty Params (no fields).

    Endpoint accepts no body/query parameters. Empty Params instance is created
    inside handler.

    Args:
        record: route configuration.
        machine: action execution machine.
        auth_coordinator: authentication coordinator (required).
        connections_factory: connections factory, or ``None``.

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
            context = Context()

        connections = None
        if connections_factory is not None:
            connections = connections_factory()

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
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
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
        connections_factory: connections factory, or ``None``.

    Returns:
        Async function suitable for ``app.add_api_route()``.
    """
    model_fields = _get_model_fields(record.effective_request_model)

    if not model_fields:
        return _make_endpoint_no_params(record, machine, auth_coordinator, connections_factory)

    if _has_body_method(record.method):
        return _make_endpoint_with_body(record, machine, auth_coordinator, connections_factory)

    return _make_endpoint_with_query(record, machine, auth_coordinator, connections_factory)


# ═════════════════════════════════════════════════════════════════════════════
# Middleware
# ═════════════════════════════════════════════════════════════════════════════


class _CatchAllErrorsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches unhandled exceptions.

    Wraps each request in try/except and guarantees HTTP 500 for uncaught errors.
    """

    async def dispatch(
        self, request: StarletteRequest, call_next: Callable[..., Any],
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
    APIs, use ``NoAuthCoordinator()`` explicitly.

    Attributes:
        _title : str
            API title for OpenAPI/Swagger UI.

        _version : str
            API version for OpenAPI.

        _description : str
            API description for OpenAPI (Markdown supported).
    """

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: Any,
        connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = None,
        *,
        gate_coordinator: GateCoordinator | None = None,
        title: str = "ActionMachine API",
        version: str = "0.1.0",
        description: str = "",
    ) -> None:
        """
        Initialize FastAPI adapter.

        Args:
            machine: action execution machine (required).
            auth_coordinator: authentication coordinator (required).
                For open APIs use ``NoAuthCoordinator()``. ``None`` is invalid.
            connections_factory: connections factory; if ``None``, connections
                are not passed.
            gate_coordinator: explicit ``GateCoordinator``; defaults to
                ``machine.gate_coordinator``.
            title: API title for OpenAPI/Swagger UI.
            version: API version for OpenAPI.
            description: API description for OpenAPI (Markdown supported).
        """
        super().__init__(
            machine=machine,
            auth_coordinator=auth_coordinator,
            connections_factory=connections_factory,
            gate_coordinator=gate_coordinator,
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
    ) -> Self:
        """
        Create ``FastApiRouteRecord``, append to ``_routes``, and return ``self``.

        If ``summary`` is empty, fill it from action ``@meta`` description.
        """
        effective_summary = summary or _get_meta_description(action_class)

        record = FastApiRouteRecord(
            action_class=action_class,
            request_model=request_model,
            response_model=response_model,
            params_mapper=params_mapper,
            response_mapper=response_mapper,
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
    ) -> Self:
        """Register POST endpoint. Returns self for fluent chain."""
        return self._register(
            "POST", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated,
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
    ) -> Self:
        """Register GET endpoint. Returns self for fluent chain."""
        return self._register(
            "GET", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated,
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
    ) -> Self:
        """Register PUT endpoint. Returns self for fluent chain."""
        return self._register(
            "PUT", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated,
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
    ) -> Self:
        """Register DELETE endpoint. Returns self for fluent chain."""
        return self._register(
            "DELETE", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated,
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
    ) -> Self:
        """Register PATCH endpoint. Returns self for fluent chain."""
        return self._register(
            "PATCH", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated,
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
        5. Generate/register endpoint for each route.

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
            auth_coordinator=self._auth_coordinator,
            connections_factory=self._connections_factory,
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
            request: Request, exc: AuthorizationError,
        ) -> JSONResponse:
            return JSONResponse(
                status_code=403,
                content={"detail": str(exc)},
            )

        @app.exception_handler(ValidationFieldError)
        async def handle_validation_error(
            request: Request, exc: ValidationFieldError,
        ) -> JSONResponse:
            return JSONResponse(
                status_code=422,
                content={"detail": str(exc)},
            )

    # ─────────────────────────────────────────────────────────────────────
    # Health check
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _register_health_check(app: FastAPI) -> None:
        """Add ``GET /health -> {"status": "ok"}`` endpoint."""

        @app.get("/health", tags=["system"])
        async def health_check() -> dict[str, str]:
            return {"status": "ok"}
