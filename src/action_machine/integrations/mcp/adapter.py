# src/action_machine/integrations/mcp/adapter.py
"""
McpAdapter — MCP adapter for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

McpAdapter maps actions to MCP tools for AI agents. One protocol ``tool()``
call registers one MCP tool. Protocol methods return ``self`` for fluent chains:

    server = adapter \\
        .tool("system.ping", PingAction) \\
        .tool("orders.create", CreateOrderAction) \\
        .build()

``inputSchema`` is generated from the Pydantic Params model via
``model_json_schema()``. Field descriptions, constraints, and examples from
``Field(...)`` propagate to MCP schema without duplicate declarations.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

``auth_coordinator`` is mandatory (enforced by ``BaseAdapter`` contract).
Each ``tool()`` call creates one ``McpRouteRecord`` entry.
``build()`` always registers resource ``system://graph``.
Tool I/O contracts are validated via ``ensure_machine_params`` and
``ensure_protocol_response``. Tool call results are always one JSON object per
``TextContent`` (success or error envelope); see ERROR HANDLING.

For open APIs, use ``NoAuthCoordinator`` explicitly:

    adapter = McpAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    tool(...) registration
            |
            v
    McpRouteRecord list
            |
            v
    build()
      |               \
      v                v
  MCP Tool(s)     system://graph
      |                |
      +-------> machine.run() <------+

Mapper naming convention:
    params_mapper   -> returns params   (request -> params)
    response_mapper -> returns response (result  -> response)

═══════════════════════════════════════════════════════════════════════════════
TOOL HANDLER GENERATION STRATEGY
═══════════════════════════════════════════════════════════════════════════════

For each registered ``McpRouteRecord``, the adapter builds an async handler that:

1. Receives tool call args as kwargs from MCP host.
2. Deserializes them via ``_validate_tool_request_kwargs`` (wraps
   ``model_validate``); Pydantic failures become ``ValidationFieldError`` with
   ``details["errors"]``.
3. Applies ``params_mapper`` when configured.
4. Builds ``Context`` via ``auth_coordinator``.
5. Resolves connections via ``connections_factory`` (or ``None``).
6. Creates action instance and calls ``machine.run()``.
7. Applies ``response_mapper`` when configured.
8. Returns ``CallToolResult``: success -> JSON ``TextContent`` envelope
   ``{"ok":true,"code":"OK","data":...}`` with ``isError=False``; failures ->
   JSON envelope ``{"ok":false,"code":...,"message":...,"details":{}}`` with
   ``isError=True``.

On failures, the handler returns ``CallToolResult(isError=True)`` instead of
raising, so MCP clients can distinguish tool-call errors at protocol level.

═══════════════════════════════════════════════════════════════════════════════
RESOURCE system://graph
═══════════════════════════════════════════════════════════════════════════════

During ``build()``, the adapter registers MCP resource ``system://graph``.
The resource returns coordinator graph JSON with nodes and edges:

    {
      "nodes": [
        {"id": "...", "type": "action", "description": "...", "domain": "..."},
        {"id": "...", "type": "domain", "name": "..."}
      ],
      "edges": [
        {"from": "...", "to": "...", "type": "belongs_to"}
      ]
    }

This lets AI agents inspect runtime architecture: available actions, domains,
and dependency relations.

═══════════════════════════════════════════════════════════════════════════════
REGISTER_ALL METHOD
═══════════════════════════════════════════════════════════════════════════════

Automatically registers all coordinator actions as MCP tools.
Tool names are derived from class names in snake_case without ``Action`` suffix
(for example, ``CreateOrderAction -> create_order``). Action classes are
discovered via ``get_nodes_by_type("aspect")``; descriptions are read from
``get_snapshot(cls, "meta")`` with fallback to scratch ``_meta_info``.

═══════════════════════════════════════════════════════════════════════════════
ERROR HANDLING
═══════════════════════════════════════════════════════════════════════════════

Exceptions are converted to JSON error envelopes with ``isError=True``:

    AuthorizationError      → ``{"ok":false,"code":"PERMISSION_DENIED","message":...,"details":{}}``
    ValidationFieldError    → ``code`` ``INVALID_PARAMS``, ``message`` from ``exc.message``,
                              ``details`` from ``exc.details`` (tool input: ``errors`` from Pydantic)
    Exception               → ``code`` ``INTERNAL_ERROR``, fixed ``message`` ``"Unexpected failure"``;
                              original exception is logged with ``logger.exception`` (not echoed to client)

Success: ``{"ok":true,"code":"OK","data":<payload>}`` where ``<payload>`` is the
JSON-serializable object produced by ``_serialize_result`` (one outer
``json.dumps`` in ``_envelope_ok``). ``isError`` is for MCP protocol clients only.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.auth import NoAuthCoordinator
    from action_machine.integrations.mcp import McpAdapter

    adapter = McpAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
        server_name="Orders MCP",
        server_version="0.1.0",
    )

    server = adapter \\
        .tool("orders.create", CreateOrderAction) \\
        .tool("orders.get", GetOrderAction) \\
        .tool("system.ping", PingAction) \\
        .build()

    server.run(transport="stdio")

AI-CORE-BEGIN
ROLE: Transport adapter that exposes ActionMachine through MCP tools/resources.
CONTRACT: kwargs -> validated params -> machine.run() -> JSON envelope text payload.
INVARIANTS: required auth coordinator; uniform JSON text envelopes; typed errors;
    internal failures do not leak exception strings to clients.
AI-CORE-END
"""

# Ruff/isort lists first-party ``action_machine`` before MCP SDK imports (known-first-party).
# pylint: disable=wrong-import-order
from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any, Self

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from action_machine.adapters.base_adapter import BaseAdapter
from action_machine.adapters.base_route_record import (
    ensure_machine_params,
    ensure_protocol_response,
)
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.integrations.mcp.route_record import McpRouteRecord
from action_machine.intents.context.context import Context
from action_machine.model.base_action import BaseAction
from action_machine.model.exceptions import AuthorizationError, ValidationFieldError
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools.base import Tool
from mcp.server.fastmcp.utilities.func_metadata import ArgModelBase, FuncMetadata
from mcp.types import CallToolResult, TextContent

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# Module-level helper functions
# ═════════════════════════════════════════════════════════════════════════════


def _envelope_ok(data: Any) -> str:
    """
    Serialize MCP tool success body as a single JSON object.

    Shape: ``ok`` (true), ``code`` (``OK``), ``data`` (arbitrary JSON-compatible
    value; non-encodable values use ``default=str``).
    """
    return json.dumps(
        {"ok": True, "code": "OK", "data": data},
        ensure_ascii=False,
        default=str,
    )


def _envelope_error(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> str:
    """
    Serialize MCP tool error body as a single JSON object.

    Shape: ``ok`` (false), ``code`` (machine-readable), ``message`` (human text),
    ``details`` (object, often empty). Uses ``default=str`` for odd values in
    ``details``.
    """
    return json.dumps(
        {"ok": False, "code": code, "message": message, "details": details or {}},
        ensure_ascii=False,
        default=str,
    )


def _validate_tool_request_kwargs(kwargs: dict[str, Any], req_model: type) -> Any:
    """
    Validate MCP tool kwargs against the effective request model.

    Centralizes Pydantic ``model_validate`` and maps failures to
    ``ValidationFieldError`` so ``_execute_tool_call`` and tests can share one
    contract without going through the full tool handler.

    Args:
        kwargs: arguments from the MCP host.
        req_model: Pydantic model type (typically ``effective_request_model``).

    Returns:
        Validated model instance.

    Raises:
        ValidationFieldError: always with message ``Tool input validation failed``
            and ``details`` containing Pydantic ``errors()`` (any validation path:
            types, constraints, ``field_validator``, etc.).
    """
    try:
        return req_model.model_validate(kwargs)  # type: ignore[attr-defined]
    except PydanticValidationError as exc:
        raise ValidationFieldError(
            "Tool input validation failed",
            details={"errors": exc.errors()},
        ) from exc


def _get_meta_description(
    action_class: type,
    *,
    coordinator: GateCoordinator | None = None,
) -> str:
    """
    Extract MCP tool description from action metadata.

    Prefers coordinator ``meta`` facet snapshot
    (``get_snapshot(action_class, "meta")``); falls back to class scratch
    ``_meta_info`` if snapshot is unavailable.

    Args:
        action_class: action class.
        coordinator: optional built coordinator.

    Returns:
        Description string or empty string.
    """
    if coordinator is not None and coordinator.is_built:
        meta_snap = coordinator.get_snapshot(action_class, "meta")
        if meta_snap is not None:
            return str(getattr(meta_snap, "description", "") or "")
    meta_info = getattr(action_class, "_meta_info", None)
    if meta_info and isinstance(meta_info, dict):
        return str(meta_info.get("description", ""))
    return ""


def _class_name_to_snake_case(name: str) -> str:
    """
    Convert a CamelCase class name to snake_case.

    Removes ``Action`` suffix before conversion.
    Example: ``CreateOrderAction -> create_order``.

    Args:
        name: class name in CamelCase.

    Returns:
        Name in snake_case without ``Action`` suffix.
    """
    if name.endswith("Action") and len(name) > len("Action"):
        name = name[: -len("Action")]

    result = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", result)
    return result.lower()


def _build_graph_json(coordinator: GateCoordinator) -> str:
    """
    Build JSON representation of system graph from coordinator.

    Extracts nodes and edges from coordinator graph and returns compact JSON
    with ``nodes`` and ``edges`` arrays.

    Args:
        coordinator: built ``GateCoordinator``.

    Returns:
        JSON string with graph structure.
    """
    graph = coordinator.get_graph()

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for idx in graph.node_indices():
        payload = graph[idx]
        hydrated = coordinator.hydrate_graph_node(dict(payload))
        node_type = hydrated.get("node_type", "unknown")
        name = hydrated.get("name", "")
        meta = hydrated.get("meta", {})

        node: dict[str, Any] = {
            "id": name,
            "type": node_type,
        }

        description = meta.get("description", "")
        if description:
            node["description"] = description

        # In node payload ``meta``, ``domain`` is usually a BaseDomain class.
        # ``json.dumps`` cannot serialize ``type`` values directly.
        # For MCP resource we emit stable ``module.QualName``; for non-standard
        # values we fallback to ``str(domain)`` so agents still receive text.
        domain = meta.get("domain")
        if domain:
            if isinstance(domain, type):
                node["domain"] = f"{domain.__module__}.{domain.__qualname__}"
            else:
                node["domain"] = str(domain)

        if node_type == "domain":
            domain_name = meta.get("name", "")
            if domain_name:
                node["name"] = domain_name

        nodes.append(node)

    for source, target, edge_data in graph.weighted_edge_list():
        source_payload = graph[source]
        target_payload = graph[target]

        if isinstance(edge_data, dict):
            edge_type = edge_data.get("edge_type", "")
        elif isinstance(edge_data, str):
            edge_type = edge_data
        else:
            edge_type = str(edge_data)

        nt_s = source_payload.get("node_type", "")
        nm_s = source_payload.get("name", "")
        nt_t = target_payload.get("node_type", "")
        nm_t = target_payload.get("name", "")

        edges.append({
            "from": nm_s,
            "to": nm_t,
            "source_key": f"{nt_s}:{nm_s}",
            "target_key": f"{nt_t}:{nm_t}",
            "type": edge_type,
        })

    result = {
        "nodes": nodes,
        "edges": edges,
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


# ═════════════════════════════════════════════════════════════════════════════
# MCP tool handler factory
# ═════════════════════════════════════════════════════════════════════════════


def _make_tool_handler(
    record: McpRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
    gate_coordinator: GateCoordinator,
) -> Callable[..., Any]:
    """
    Create async handler for one MCP tool.

    Handler accepts kwargs from MCP host, deserializes into request model,
    executes action via ``machine.run()``, and returns ``CallToolResult`` whose
    ``TextContent`` is always one JSON object (success or error envelope). On
    failure, returns ``CallToolResult(isError=True)`` with ``_envelope_error`` JSON.

    Args:
        record: route configuration with action class and mappers.
        machine: action execution machine.
        auth_coordinator: authentication coordinator.
        connections_factory: optional connections factory.
        gate_coordinator: coordinator used for tool metadata.

    Returns:
        Async function suitable for MCP tool registration.
    """
    req_model = record.effective_request_model
    has_params_mapper = record.params_mapper is not None
    has_response_mapper = record.response_mapper is not None

    async def handler(**kwargs: Any) -> CallToolResult:
        """
        Execute one MCP tool call and return protocol-level result.

        Returns:
            ``CallToolResult`` with JSON envelope text and ``isError`` set from
            outcome (see module ERROR HANDLING).
        """
        try:
            payload = await _execute_tool_call(
                kwargs, req_model, record, machine,
                auth_coordinator, connections_factory,
                has_params_mapper, has_response_mapper,
            )
            return CallToolResult(
                content=[TextContent(type="text", text=_envelope_ok(payload))],
                isError=False,
            )
        except AuthorizationError as exc:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=_envelope_error("PERMISSION_DENIED", str(exc)),
                )],
                isError=True,
            )
        except ValidationFieldError as exc:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=_envelope_error(
                        "INVALID_PARAMS",
                        exc.message,
                        exc.details,
                    ),
                )],
                isError=True,
            )
        except Exception:
            logger.exception("MCP tool call failed: %s", record.tool_name)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=_envelope_error(
                        "INTERNAL_ERROR",
                        "Unexpected failure",
                    ),
                )],
                isError=True,
            )

    handler.__name__ = record.tool_name.replace(".", "_").replace("-", "_")
    handler.__doc__ = record.description or _get_meta_description(
        record.action_class,
        coordinator=gate_coordinator,
    )

    return handler


async def _execute_tool_call(
    kwargs: dict[str, Any],
    req_model: type,
    record: McpRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
    has_params_mapper: bool,
    has_response_mapper: bool,
) -> Any:
    """
    Execute one MCP tool call: deserialize, map, run, serialize.

    Request parsing uses ``_validate_tool_request_kwargs`` so Pydantic failures
    become ``ValidationFieldError`` and the handler maps them to
    ``INVALID_PARAMS`` instead of ``INTERNAL_ERROR``.

    Args:
        kwargs: tool call arguments from agent.
        req_model: request model for input validation.
        record: route configuration.
        machine: action machine.
        auth_coordinator: authentication coordinator.
        connections_factory: optional connections factory.
        has_params_mapper: whether params mapper is configured.
        has_response_mapper: whether response mapper is configured.

    Returns:
        Serializable payload for the success envelope ``data`` field (not yet
        wrapped in ``_envelope_ok``; the handler applies the envelope).

    Raises:
        ValidationFieldError: when tool kwargs fail Pydantic validation (via
            ``_validate_tool_request_kwargs``).

    Other exceptions from ``machine.run`` (for example ``AuthorizationError``)
    propagate to the tool handler, which maps them to envelopes.
    """
    body = _validate_tool_request_kwargs(kwargs, req_model)

    params = record.params_mapper(body) if has_params_mapper else body  # type: ignore[misc]

    ensure_machine_params(
        params,
        record.params_type,
        adapter="MCP",
        route_label=record.tool_name,
    )

    context = await auth_coordinator.process(None)
    if context is None:
        context = Context()

    connections = connections_factory() if connections_factory is not None else None

    action = record.action_class()
    result = await machine.run(context, action, params, connections)

    return _serialize_result(result, record, has_response_mapper)


def _serialize_result(
    result: Any,
    record: McpRouteRecord,
    has_response_mapper: bool,
) -> Any:
    """
    Build a JSON-serializable payload from the action result.

    Applies ``response_mapper`` before conversion when configured. The MCP
    handler wraps the return value in ``_envelope_ok`` (single ``json.dumps``).

    Args:
        result: action result object.
        record: route configuration.
        has_response_mapper: whether response mapper is configured.

    Returns:
        Object suitable for embedding in the success envelope ``data`` field.
    """
    if has_response_mapper:
        mapped = record.response_mapper(result)  # type: ignore[misc]
        ensure_protocol_response(
            mapped,
            record.effective_response_model,
            adapter="MCP",
            route_label=record.tool_name,
        )
        return mapped.model_dump(mode="json") if hasattr(mapped, "model_dump") else mapped
    return result.model_dump(mode="json") if hasattr(result, "model_dump") else result


# ═════════════════════════════════════════════════════════════════════════════
# Adapter class
# ═════════════════════════════════════════════════════════════════════════════


class McpAdapter(BaseAdapter[McpRouteRecord]):
    """
    MCP adapter for ActionMachine.

    Built tools return JSON envelope strings in ``CallToolResult`` text (see
    module docstring ERROR HANDLING).

    AI-CORE-BEGIN
    ROLE: Exposes ActionMachine actions as MCP tools/resources.
    CONTRACT: BaseAdapter[McpRouteRecord] with tool(), register_all(), build().
    INVARIANTS: auth coordinator required; graph resource on build; tool text is JSON envelope.
    AI-CORE-END
    """

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: Any,
        connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = None,
        *,
        gate_coordinator: GateCoordinator | None = None,
        server_name: str = "ActionMachine MCP",
        server_version: str = "0.1.0",
    ) -> None:
        """
        Initialize MCP adapter.

        Args:
            machine: action execution machine.
            auth_coordinator: authentication coordinator; required.
            connections_factory: optional connection factory per call.
            gate_coordinator: optional explicit coordinator.
            server_name: MCP server display name.
            server_version: MCP server version string.
        """
        super().__init__(
            machine=machine,
            auth_coordinator=auth_coordinator,
            connections_factory=connections_factory,
            gate_coordinator=gate_coordinator,
        )
        self._server_name: str = server_name
        self._server_version: str = server_version

    # ─────────────────────────────────────────────────────────────────────
    # Properties
    # ─────────────────────────────────────────────────────────────────────

    @property
    def server_name(self) -> str:
        """MCP server name."""
        return self._server_name

    @property
    def server_version(self) -> str:
        """MCP server version."""
        return self._server_version

    # ─────────────────────────────────────────────────────────────────────
    # Protocol registration method (returns Self)
    # ─────────────────────────────────────────────────────────────────────

    def tool(
        self,
        name: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        description: str = "",
    ) -> Self:
        """
        Register one MCP tool and return ``self`` for fluent chaining.

        ``inputSchema`` is derived from ``effective_request_model``.
        If ``description`` is empty, action ``@meta`` description is used.

        Args:
            name: MCP tool name visible to agents.
            action_class: action class (``BaseAction[P, R]`` subtype).
            request_model: optional protocol request model.
            response_model: optional protocol response model.
            params_mapper: optional request->params transformer.
            response_mapper: optional result->response transformer.
            description: optional tool description override.

        Returns:
            Current adapter instance.
        """
        effective_description = description or _get_meta_description(
            action_class,
            coordinator=self.gate_coordinator,
        )

        record = McpRouteRecord(
            action_class=action_class,
            request_model=request_model,
            response_model=response_model,
            params_mapper=params_mapper,
            response_mapper=response_mapper,
            tool_name=name,
            description=effective_description,
        )
        return self._add_route(record)

    # ─────────────────────────────────────────────────────────────────────
    # Automatic registration of all actions
    # ─────────────────────────────────────────────────────────────────────

    def register_all(self) -> Self:
        """
        Auto-register all coordinator actions as MCP tools.

        Iterates over ``aspect`` nodes and registers actions that have
        non-empty aspect snapshots.

        Returns:
            Current adapter instance.
        """
        coordinator = self.gate_coordinator

        action_nodes = coordinator.get_nodes_by_type("aspect")
        seen: set[type] = set()
        for node in action_nodes:
            cls = node.get("class_ref")
            if not isinstance(cls, type):
                continue
            if cls in seen or not issubclass(cls, BaseAction):
                continue
            seen.add(cls)

            aspect_snap = coordinator.get_snapshot(cls, "aspect")
            aspects = getattr(aspect_snap, "aspects", ()) if aspect_snap is not None else ()
            if not aspects:
                continue

            tool_name = _class_name_to_snake_case(cls.__name__)
            m = coordinator.get_snapshot(cls, "meta")
            description = m.description if m is not None and hasattr(m, "description") else ""

            self.tool(
                name=tool_name,
                action_class=cls,
                description=description,
            )

        return self

    # ─────────────────────────────────────────────────────────────────────
    # MCP server build
    # ─────────────────────────────────────────────────────────────────────

    def build(self) -> FastMCP:
        """
        Build MCP server from registered routes.

        Order:
        1. Build ``Tool`` objects for routes.
        2. Create MCP host with server name and tool list.
        3. Register ``system://graph`` resource.

        Returns:
            Ready MCP server with registered tools and graph resource.
        """
        tools = [self._make_mcp_tool(record) for record in self._routes]
        mcp = FastMCP(self._server_name, tools=tools)

        self._register_graph_resource(mcp)

        return mcp

    # ─────────────────────────────────────────────────────────────────────
    # MCP tool build (inputSchema + arg validation)
    # ─────────────────────────────────────────────────────────────────────

    def _mcp_argument_model(self, record: McpRouteRecord) -> type[ArgModelBase]:
        """
        Build MCP host argument model for one tool.

        Inherits from both ``effective_request_model`` and ``ArgModelBase`` so
        MCP arg validation can use expected model APIs.

        Raises:
            TypeError: if effective_request_model is not a BaseModel subclass.
        """
        req = record.effective_request_model
        if not isinstance(req, type) or not issubclass(req, BaseModel):
            raise TypeError(
                f"MCP tool {record.tool_name!r} requires effective_request_model "
                f"to be a Pydantic BaseModel subclass; got {req!r}."
            )
        safe_tool = "".join(ch if ch.isalnum() else "_" for ch in record.tool_name)
        return type(
            f"{req.__name__}_{safe_tool}McpArgs",
            (req, ArgModelBase),
            {},
        )

    def _make_mcp_tool(self, record: McpRouteRecord) -> Tool:
        """
        Build ``Tool`` with explicit JSON Schema parameters for MCP.

        Handler-only registration would infer schema from function signature;
        because handler accepts ``**kwargs``, schema is generated explicitly
        from action parameter model.
        """
        handler = _make_tool_handler(
            record=record,
            machine=self._machine,
            auth_coordinator=self._auth_coordinator,
            connections_factory=self._connections_factory,
            gate_coordinator=self.gate_coordinator,
        )
        arg_model = self._mcp_argument_model(record)
        fn_meta = FuncMetadata(arg_model=arg_model)
        parameters = arg_model.model_json_schema(by_alias=True)
        description = record.description or _get_meta_description(
            record.action_class,
            coordinator=self.gate_coordinator,
        )
        return Tool(
            fn=handler,
            name=record.tool_name,
            title=None,
            description=description,
            parameters=parameters,
            fn_metadata=fn_meta,
            is_async=True,
            context_kwarg=None,
            annotations=None,
            icons=None,
            meta=None,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Register system://graph resource
    # ─────────────────────────────────────────────────────────────────────

    def _register_graph_resource(self, mcp: FastMCP) -> None:
        """
        Register MCP resource ``system://graph`` on server.

        Agents can request it to inspect runtime structure: actions, domains,
        and dependency edges.

        Args:
            mcp: MCP host where resource is registered.
        """
        coordinator = self.gate_coordinator

        @mcp.resource("system://graph")
        def get_system_graph() -> str:
            """
            ActionMachine runtime graph structure.

            Returns JSON with coordinator graph nodes (actions, domains,
            dependencies, resource managers) and edges
            (depends, belongs_to, connection).
            """
            return _build_graph_json(coordinator)
