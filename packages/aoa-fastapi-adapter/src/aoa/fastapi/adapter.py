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
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Annotated, Any, Self, get_origin

from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from aoa.action_machine.adapters.base_adapter import BaseAdapter
from aoa.action_machine.adapters.base_route_record import ensure_machine_params, ensure_protocol_response
from aoa.action_machine.auth.auth_coordinator_protocol import AuthCoordinatorProtocol
from aoa.action_machine.auth.permission_namespace import compute_cache_partition
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.exceptions.check_access_decide_batch_size_exceeded_error import (
    CheckAccessDecideBatchSizeExceededError,
)
from aoa.action_machine.exceptions.validation_field_error import ValidationFieldError
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.resources.per_call_connection import ConnectionValue
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.fastapi.execution_plan import EndpointExecutionPlan, PreparedEndpointContext, build_execution_plan_index
from aoa.fastapi.manifest import Manifest, build_manifest
from aoa.fastapi.permissions import build_route_index, resolve_verdicts
from aoa.fastapi.permissions_schema import (
    SUPPORTED_VERSION,
    ErrorDetail,
    ErrorEnvelope,
    PermissionNamespace,
    ResolveRequest,
    ResolveResponse,
)
from aoa.fastapi.reserved_route_path_error import ReservedRoutePathError
from aoa.fastapi.route_record import FastApiRouteRecord
from aoa.fastapi.route_shadow_error import RouteShadowError
from aoa.fastapi.unsupported_version_error import UnsupportedVersionError
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


# ═════════════════════════════════════════════════════════════════════════════
# Route shadowing detection
# ═════════════════════════════════════════════════════════════════════════════
#
# Two *different* path templates, same method, can still match the same real
# URL — "/users/me" alongside "/users/{id}", or "/users/{id}" alongside
# "/users/{name}". Starlette would silently route every matching request to
# whichever was registered first; build() fails the build instead (RouteShadowError).
# This is deliberately conservative — "when in doubt, flag it" — since a false
# positive costs a developer one rename, but a missed collision costs a client a
# button that lies. See RouteShadowError's own module docstring for the full argument.

_TEMPLATE_SEGMENT_PATTERN: re.Pattern[str] = re.compile(r"\{(?P<name>\w+)(?::(?P<converter>\w+))?\}")
_INT_LITERAL_PATTERN: re.Pattern[str] = re.compile(r"^-?\d+$")
_FLOAT_LITERAL_PATTERN: re.Pattern[str] = re.compile(r"^-?\d+(\.\d+)?$")
_UUID_LITERAL_PATTERN: re.Pattern[str] = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@dataclass(frozen=True)
class _PathSegment:
    """One ``/``-delimited piece of a path template: a literal, or a ``{name[:converter]}`` param."""

    is_param: bool
    value: str  # literal text, or the param name
    converter: str = "str"  # only meaningful when is_param — Starlette's default converter is "str"


def _parse_path_segments(path: str) -> list[_PathSegment]:
    """Split a path template into ``_PathSegment``s, recognizing Starlette's ``{name:converter}`` syntax."""
    segments: list[_PathSegment] = []
    for raw in path.split("/"):
        if not raw:
            continue
        match = _TEMPLATE_SEGMENT_PATTERN.fullmatch(raw)
        if match is None:
            segments.append(_PathSegment(is_param=False, value=raw))
        else:
            converter = match.group("converter") or "str"
            segments.append(_PathSegment(is_param=True, value=match.group("name"), converter=converter))
    return segments


def _literal_matches_converter(literal: str, converter: str) -> bool:
    """Whether a literal segment's text is a value the given converter could actually accept.

    ``str``/``path`` (and any converter this module does not specifically know
    about) accept any non-empty text — conservative by construction, since an
    unrecognized converter might accept anything.
    """
    if converter == "int":
        return bool(_INT_LITERAL_PATTERN.fullmatch(literal))
    if converter == "float":
        return bool(_FLOAT_LITERAL_PATTERN.fullmatch(literal))
    if converter == "uuid":
        return bool(_UUID_LITERAL_PATTERN.fullmatch(literal))
    return True


def _segments_could_overlap(a: _PathSegment, b: _PathSegment) -> bool:
    """Whether some single URL segment could satisfy both ``a`` and ``b`` at once."""
    if not a.is_param and not b.is_param:
        return a.value == b.value
    if a.is_param and b.is_param:
        # Conservative: two params (whatever their converters) can always agree on some value.
        return True
    literal, param = (a, b) if not a.is_param else (b, a)
    return _literal_matches_converter(literal.value, param.converter)


def _is_greedy_tail(segments: list[_PathSegment]) -> bool:
    """Whether ``segments`` ends in a ``{name:path}`` param — Starlette's only multi-segment converter."""
    return bool(segments) and segments[-1].is_param and segments[-1].converter == "path"


def _paths_could_overlap(path_a: str, path_b: str) -> bool:
    """
    Whether two *different* path templates could match a common real URL.

    Neither template greedy (no trailing ``{name:path}``): they can only overlap
    with the same segment count, each pair of corresponding segments compatible.
    Either one greedy: its trailing ``{name:path}`` can absorb any number of the
    other template's remaining segments (including zero), so only the fixed
    (non-greedy) prefixes need to line up — and the shorter fixed prefix must be
    a compatible match against the longer one's first segments.
    """
    segments_a = _parse_path_segments(path_a)
    segments_b = _parse_path_segments(path_b)
    fixed_a = segments_a[:-1] if _is_greedy_tail(segments_a) else segments_a
    fixed_b = segments_b[:-1] if _is_greedy_tail(segments_b) else segments_b

    if not _is_greedy_tail(segments_a) and not _is_greedy_tail(segments_b):
        if len(fixed_a) != len(fixed_b):
            return False
        return all(_segments_could_overlap(x, y) for x, y in zip(fixed_a, fixed_b, strict=True))

    shorter, longer = (fixed_a, fixed_b) if len(fixed_a) <= len(fixed_b) else (fixed_b, fixed_a)
    prefix_of_longer = longer[: len(shorter)]
    return all(_segments_could_overlap(x, y) for x, y in zip(shorter, prefix_of_longer, strict=True))


def _check_for_route_shadowing(routes: list[tuple[str, str]]) -> None:
    """
    Raise ``RouteShadowError`` if any two *different* templates, same method, could overlap.

    Takes plain ``(method, path)`` pairs, not ``FastApiRouteRecord``\\ s — the only two
    fields this check ever reads — so the caller can feed it the adapter's own bespoke
    routes (``/health``, ``/permissions/resolve``, ...) alongside ``self._routes``
    without fabricating a fake ``FastApiRouteRecord`` (which would need a real
    ``action_class``) for each one. Audit finding 5: those four used to be invisible
    to this check entirely, registered a different way and never added to the list
    it was called with — an app-registered route could structurally shadow the
    framework's own health check or resolver and ``build()`` would not notice.

    Exact ``(method, path)`` duplicates are a separate, non-fatal case (a dev-time
    ``UserWarning`` in ``_register``, first-wins in the manifest/resolver) — skipped
    here on purpose, since registering the identical template twice is never
    "ambiguous" about which URLs it matches.
    """
    paths_by_method: dict[str, list[str]] = {}
    for method, path in routes:
        paths_by_method.setdefault(method, []).append(path)

    for method, paths in paths_by_method.items():
        confirmed: list[str] = []
        for path in paths:
            for other in confirmed:
                if path != other and _paths_could_overlap(path, other):
                    raise RouteShadowError(method, other, path)
            confirmed.append(path)


def _if_none_match_hits(header_value: str | None, etag: str) -> bool:
    """
    Whether a quoted ``etag`` (e.g. ``'"sha256:abc..."'``) satisfies an ``If-None-Match``
    request header — a comma-separated list of quoted ETags, or the wildcard ``*``.
    """
    if header_value is None:
        return False
    candidates = [token.strip() for token in header_value.split(",")]
    return etag in candidates or "*" in candidates


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
    plan: EndpointExecutionPlan,
) -> Callable[..., Any]:
    """
    Create endpoint for methods with JSON body (POST, PUT, PATCH).

    ``body`` parameter is annotated with concrete Pydantic model.
    FastAPI validates request body and generates OpenAPI schema automatically.

    Args:
        record: route configuration.
        machine: action execution machine.
        plan: this route's execution plan (auth coordinator + connections recipe) —
            the same recipe the permissions resolver runs for this route's ``operation``.

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

        prepared = await plan.prepare(request)

        action = record.action_class()
        result = await machine.run(prepared.context, action, params, prepared.connections)

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
    plan: EndpointExecutionPlan,
) -> Callable[..., Any]:
    """
    Create endpoint for GET/DELETE with query/path parameters.

    Each Params model field becomes a function argument. FastAPI resolves which
    parameters come from path and which from query string using annotations and
    route path placeholders.

    Args:
        record: route configuration.
        machine: action execution machine.
        plan: this route's execution plan (auth coordinator + connections recipe) —
            the same recipe the permissions resolver runs for this route's ``operation``.

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

        prepared = await plan.prepare(request)

        action = record.action_class()
        result = await machine.run(prepared.context, action, params, prepared.connections)

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
    plan: EndpointExecutionPlan,
) -> Callable[..., Any]:
    """
    Create endpoint for actions with empty Params (no fields).

    Endpoint accepts no body/query parameters. Empty Params instance is created
    inside handler.

    Args:
        record: route configuration.
        machine: action execution machine.
        plan: this route's execution plan (auth coordinator + connections recipe) —
            the same recipe the permissions resolver runs for this route's ``operation``.

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

        prepared = await plan.prepare(request)

        action = record.action_class()
        result = await machine.run(prepared.context, action, params, prepared.connections)

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
    plan: EndpointExecutionPlan,
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
        plan: this route's execution plan (auth coordinator + connections recipe) —
            the same recipe the permissions resolver runs for this route's ``operation``.

    Returns:
        Async function suitable for ``app.add_api_route()``.
    """
    model_fields = _get_model_fields(record.effective_request_model)

    if not model_fields:
        return _make_endpoint_no_params(record, machine, plan)

    if _has_body_method(record.method):
        return _make_endpoint_with_body(record, machine, plan)

    return _make_endpoint_with_query(record, machine, plan)


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

    #: (method, path) for every bespoke route the adapter registers itself, outside
    #: self._routes (``build()`` registers these before looping over ``self._routes``,
    #: so an app-registered route on the same path would be silently shadowed by
    #: Starlette's first-match-wins routing — see ``ReservedRoutePathError``). Single
    #: source of truth for both ``_RESERVED_PATHS`` (exact-path collisions) and the
    #: route-shadowing check in ``build()`` (template overlaps) — audit finding 5: the
    #: two used to be checked separately, and only one of them knew these paths existed.
    _RESERVED_ROUTES: tuple[tuple[str, str], ...] = (
        ("GET", "/health"),
        ("POST", "/permissions/resolve"),
        ("GET", "/client-manifest.json"),
        ("GET", "/permissions/namespace"),
    )

    #: Paths owned by the adapter's own bespoke routes — derived from ``_RESERVED_ROUTES``
    #: so the two can never drift apart.
    _RESERVED_PATHS: frozenset[str] = frozenset(path for _, path in _RESERVED_ROUTES)

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

        An exact ``(method, path)`` duplicate is not an error — Starlette's real
        router would resolve it the same way, "first registration wins", so this
        only warns (``UserWarning``, once per call site) rather than raising;
        :func:`~aoa.fastapi.manifest.build_manifest` and
        :func:`~aoa.fastapi.permissions.build_route_index` both already build
        from the first registration to match. A *different* template that could
        match the same URL as an existing one (e.g. ``/users/me`` alongside
        ``/users/{id}``) is not caught here — that needs every route to be known
        first, so it is checked once, at :meth:`build`, and raises
        ``RouteShadowError`` instead of warning.

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
        if any(r.method == record.method and r.path == record.path for r in self._routes):
            warnings.warn(
                f"{record.method} {record.path!r} is already registered. Starlette will route every "
                "matching request to the first registration; this one is unreachable and will not "
                "appear in the client manifest.",
                UserWarning,
                stacklevel=3,
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
        1. Fail fast if any two different path templates could shadow each
           other (``RouteShadowError``) — before anything else is built. Covers
           the adapter's own bespoke routes (``_RESERVED_ROUTES``) too, not only
           ``self._routes`` — an app-registered template can shadow ``/health``
           or the resolver exactly as easily as it can shadow another app route.
        2. Create FastAPI app with OpenAPI metadata.
        3. Add middleware for uncaught exception handling.
        4. Register exception handlers.
        5. Register health check endpoint ``GET /health``.
        6. Register permissions endpoints (``POST /permissions/resolve``,
           ``GET /client-manifest.json``, ``GET /permissions/namespace``).
        7. Generate/register endpoint for each route.

        One :class:`~aoa.fastapi.execution_plan.EndpointExecutionPlan` per route,
        built once here (``plan_index``) and shared by both step 6 and step 7 — a
        real call and the resolver's own prediction for the same route always read
        the identical plan object, not two independently-built ones that merely
        happen to agree today (chapter 3.5 rule 1; audit finding 9).

        Raises:
            RouteShadowError: two registered routes, same method, have path
                templates that could match the same real URL (e.g. ``/users/me``
                alongside ``/users/{id}``) — see its own module docstring.

        Returns:
            Ready-to-run FastAPI application.
        """
        _check_for_route_shadowing(
            [*self._RESERVED_ROUTES, *((record.method, record.path) for record in self._routes)]
        )

        app = FastAPI(
            title=self._title,
            version=self._version,
            description=self._description,
        )

        route_index = build_route_index(self._routes)
        plan_index = build_execution_plan_index(route_index, self.effective_auth_coordinator)

        app.add_middleware(_CatchAllErrorsMiddleware)
        self._register_exception_handlers(app)
        self._register_health_check(app)
        self._register_permissions_endpoints(app, plan_index)

        for record in self._routes:
            self._register_endpoint(app, record, plan_index)

        return app

    # ─────────────────────────────────────────────────────────────────────
    # Endpoint generation
    # ─────────────────────────────────────────────────────────────────────

    def _register_endpoint(
        self, app: FastAPI, record: FastApiRouteRecord, plan_index: dict[str, EndpointExecutionPlan]
    ) -> None:
        """
        Generate and register one async endpoint from ``FastApiRouteRecord``.

        Reads this route's plan from ``plan_index`` (built once in ``build()``) rather
        than constructing its own -- the resolver reads the exact same plan object for
        the exact same route, per chapter 3.5 rule 1 (audit finding 9). An exact
        ``(method, path)`` duplicate (allowed, first-wins, a non-fatal ``UserWarning``
        elsewhere) resolves to the *first* registration's plan here too; the second
        registration is already unreachable via Starlette's own first-match routing,
        so this cannot change any real request's behavior.
        """
        plan = plan_index[_fastapi_route_label(record)]
        endpoint = _make_endpoint(
            record=record,
            machine=self._machine,
            plan=plan,
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

        ``AuthorizationError`` -> 403 body carries ``reason``/``level`` alongside the
        existing ``detail`` -- additively, ``detail`` is unchanged -- so the
        developer-declared ``reason=`` a ``grant(when=...)``/``check_roles(guard=...)``
        was rejected with (or the framework-fixed ``"FORBIDDEN_ROLE"``) actually reaches
        the caller on a real ``.call()`` denial, not only on a resolver ``.can()``
        prediction. Both are ``None`` for an entry-gate failure ("Authentication
        required", raised with neither) and, today, for a level-3 ``access_decide``
        denial (``reason`` is ``None`` there until that gate gets its own reason
        mechanism -- a separate, not-yet-done change).
        """

        @app.exception_handler(AuthorizationError)
        async def handle_authorization_error(
            request: Request,
            exc: AuthorizationError,
        ) -> JSONResponse:
            return JSONResponse(
                status_code=403,
                content={"detail": str(exc), "reason": exc.reason, "level": exc.level},
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

        @app.exception_handler(UnsupportedVersionError)
        async def handle_unsupported_version(
            request: Request,
            exc: UnsupportedVersionError,
        ) -> JSONResponse:
            return JSONResponse(
                status_code=400,
                content=ErrorEnvelope(error=ErrorDetail(code="unsupported_version")).model_dump(mode="json"),
            )

    # ─────────────────────────────────────────────────────────────────────
    # Permissions resolver + client manifest (issue #130)
    # ─────────────────────────────────────────────────────────────────────

    def _register_permissions_endpoints(self, app: FastAPI, plan_index: dict[str, EndpointExecutionPlan]) -> None:
        """
        Add ``POST /permissions/resolve`` (list-shaped role-gate resolver, PR 1 + PR 2),
        ``GET /client-manifest.json`` (endpoint catalog, chapter 3), and
        ``GET /permissions/namespace`` (``PermissionNamespace``/``cache_partition``,
        chapter 3.5) — all issue #130.

        Registered as a bespoke route, not a ``BaseAction`` — it needs ``machine``
        and a full ``Context`` to call ``machine.check_access_decide`` on *other*
        actions, and ordinary aspects cannot reach either (see the module-level
        ``REQUIRED AUTHENTICATION`` note and the ADR for the full argument).

        ``POST /permissions/resolve`` checks the whole request before touching any
        item, in order: ``body.version`` first (``400`` via ``UnsupportedVersionError``
        -> ``ErrorEnvelope``, before authentication even runs), then
        ``auth_coordinator.process(request)`` (``403``) — see chapter 3.5 rules 7/8.
        Neither failure produces a ``results`` array at all; a per-item problem
        (unknown ``operation``, a failed check) never does either — it becomes a
        ``CHECK_ERROR`` element inside an otherwise-normal ``200``.

        Always calls ``auth_coordinator.process(request)``; a ``403`` (via the
        existing ``AuthorizationError`` handler) follows only
        when that returns ``None`` (e.g. invalid credentials on a strict
        coordinator) — a resolved anonymous ``Context`` (``NoAuthCoordinator``)
        proceeds normally, so ``@check_roles(GuestRole)`` actions resolve correctly
        for unauthenticated callers instead of being special-cased here. This is the
        resolver's own entry gate — "can this caller ask the resolver anything at
        all" — separate from and prior to each item's own route-level auth below.

        Per-item auth/connections go through the same
        :class:`~aoa.fastapi.execution_plan.EndpointExecutionPlan` a real call to
        that route would use, not a single context/connections pair shared across
        the whole batch: for every *distinct* ``operation`` named in the batch (not
        per item — auth and connections do not depend on ``params``), the matching
        plan's :meth:`~aoa.fastapi.execution_plan.EndpointExecutionPlan.prepare` runs
        against this same ``request``, reusing the entry-gate ``context`` outright
        when that route does not override the adapter's default coordinator. When a
        route *does* override it and that coordinator rejects the caller, ``prepare``
        raises ``AuthorizationError`` -- caught here per operation (not left to
        propagate into the app-wide 403 handler) and passed to ``resolve_verdicts`` as
        ``unauthorized_operations``, so only that operation's own positions in
        ``results`` come back ``kind=SECURITY, reason="UNAUTHORIZED"``; every other
        question in the same batch still gets its real answer. The resolver's own
        entry gate above (``auth_coordinator.process(request)`` at the top of this
        handler) stays whole-request on purpose -- identity is not established at all
        yet at that point, so there is no per-item granularity to preserve.
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
        # plan_index is built once in build() and shared with _register_endpoint --
        # not rebuilt here (audit finding 9). Projected once: self._routes is already
        # fixed by the time build() runs (every .post/.get/... has registered), so
        # nothing is recomputed per request.
        manifest = build_manifest(self._routes)

        @app.post("/permissions/resolve", tags=["permissions"], response_model=ResolveResponse)
        async def resolve(request: Request, body: ResolveRequest) -> ResolveResponse:
            # Whole-request checks first, in order: an unsupported wire language
            # (400) never even gets to prove its identity (401/403) — see chapter
            # 3.5 rule 8. Both are all-or-nothing, unlike a per-item CHECK_ERROR.
            if body.version != SUPPORTED_VERSION:
                raise UnsupportedVersionError(body.version, supported_version=SUPPORTED_VERSION)

            context = await auth_coordinator.process(request)
            if context is None:
                raise AuthorizationError("Authentication required")

            prepared_by_operation: dict[str, PreparedEndpointContext] = {}
            unauthorized_operations: set[str] = set()
            for operation in {item.operation for item in body.items}:
                plan = plan_index.get(operation)
                if plan is None:
                    continue
                reuse_context = context if plan.record.auth_coordinator is None else None
                try:
                    prepared_by_operation[operation] = await plan.prepare(request, reuse_context=reuse_context)
                except AuthorizationError:
                    # This operation's own route-level auth_coordinator rejected the
                    # caller -- isolate it to this operation's positions (kind=SECURITY,
                    # reason="UNAUTHORIZED" via resolve_verdicts), not a blanket 403 for
                    # the whole batch. Distinct from the resolver's own entry gate above,
                    # which *is* whole-request by design (identity is not established at
                    # all yet at that point, so there is no per-item granularity to keep).
                    unauthorized_operations.add(operation)

            outcome = await resolve_verdicts(
                body.items,
                plan_index,
                prepared_by_operation,
                machine,
                unauthorized_operations=frozenset(unauthorized_operations),
            )
            return ResolveResponse(version=SUPPORTED_VERSION, results=outcome.results)

        manifest_etag = f'"{manifest.manifest_version}"'
        # Role-independent: the same manifest goes to every authenticated caller,
        # guest (NoAuthCoordinator) included — hence identity-neutral headers/body,
        # not per-caller ones. "private" in Cache-Control is about *where* the
        # response may be cached (this connection only, never a shared proxy), not
        # about its content varying by caller. Neither headers nor body depend on
        # anything request-scoped, and self._routes is already fixed by build()
        # time, so both are built exactly once here, not per request: audit finding
        # 8 — JSONResponse(...) itself re-runs model_dump() *and* json.dumps() on
        # every construction, so precomputing only the dict passed to it would still
        # re-serialize to JSON on every single request. Response objects hold no
        # per-request state (__call__ only replays the already-rendered bytes/
        # headers over ASGI), so the same instance is safe to return unmodified on
        # every cache-miss.
        manifest_headers = {"ETag": manifest_etag, "Cache-Control": "private, no-cache"}
        manifest_response = JSONResponse(content=manifest.model_dump(mode="json"), headers=manifest_headers)

        @app.get("/client-manifest.json", tags=["permissions"], response_model=Manifest)
        async def client_manifest(request: Request) -> StarletteResponse:
            context = await auth_coordinator.process(request)
            if context is None:
                raise AuthorizationError("Authentication required")
            if _if_none_match_hits(request.headers.get("if-none-match"), manifest_etag):
                return StarletteResponse(status_code=304, headers=manifest_headers)
            return manifest_response

        @app.get("/permissions/namespace", tags=["permissions"], response_model=PermissionNamespace)
        async def permission_namespace(request: Request) -> PermissionNamespace:
            context = await auth_coordinator.process(request)
            if context is None:
                raise AuthorizationError("Authentication required")
            # Freshly derived from this call's identity, never stored — see
            # compute_cache_partition's own docstring for why that is enough to
            # behave like a generation counter without needing one.
            return PermissionNamespace(cache_partition=compute_cache_partition(context))

    # ─────────────────────────────────────────────────────────────────────
    # Health check
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _register_health_check(app: FastAPI) -> None:
        """Add ``GET /health -> {"status": "ok"}`` endpoint."""

        @app.get("/health", tags=["system"])
        async def health_check() -> dict[str, str]:
            return {"status": "ok"}
