# packages/aoa-action-machine/src/aoa/action_machine/integrations/mcp/adapter.py
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
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    tool(...) registration
            |
            v
    McpRouteRecord list
            |
            v
    build()  --->  MCP Tool(s)  --->  machine.run()

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
8. Builds success ``data`` via ``_serialize_result`` (``model_dump(mode="json")`` for
   Pydantic models); only ``_envelope_ok`` runs the outer ``json.dumps``.
9. Returns ``CallToolResult``: success -> JSON ``TextContent`` envelope
   ``{"ok":true,"code":"OK","data":...}`` with ``isError=False``; failures ->
   JSON envelope ``{"ok":false,"code":...,"message":...,"details":{}}`` with
   ``isError=True`` (tool-input Pydantic issues use ``details.errors``).

On failures, the handler returns ``CallToolResult(isError=True)`` instead of
raising, so MCP clients can distinguish tool-call errors at protocol level.

═══════════════════════════════════════════════════════════════════════════════
TESTING NOTE (MCP tools)
═══════════════════════════════════════════════════════════════════════════════

Handler tests should use a real ``ActionProductMachine`` so schemas, node graph
metadata, and handler code match production.

To control results or speed, stub ``machine.run`` only — not the whole stack.

::

    MCP kwargs
         |
         v
    validate / map params  --->  auth_coordinator  --->  machine.run  ~~~~ stub
         ^______________________ production ________________________^
                                                                    ~~~~
                                                         optional AsyncMock

    serialize / envelope  <---  (after run)
         ^
         production

See ``BaseAdapter`` module docstring (ADAPTER TESTING CONTRACT) for the full
adapter-level picture.

═══════════════════════════════════════════════════════════════════════════════
REGISTER_ALL METHOD
═══════════════════════════════════════════════════════════════════════════════

Automatically registers all coordinator actions as MCP tools.
Tool names are derived from class names in snake_case without ``Action`` suffix
(for example, ``CreateOrderAction -> create_order``). Action classes are
discovered from ``ActionGraphNode`` rows with regular or summary aspects;
descriptions are read from node properties with fallback to scratch ``_meta_info``.

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

from aoa.action_machine.adapters.base_adapter import BaseAdapter
from aoa.action_machine.adapters.base_route_record import (
    ensure_machine_params,
    ensure_protocol_response,
)
from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.exceptions.validation_field_error import ValidationFieldError
from aoa.action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
from aoa.action_machine.integrations.mcp.route_record import McpRouteRecord
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools.base import Tool
from mcp.server.fastmcp.utilities.func_metadata import ArgModelBase, FuncMetadata
from mcp.types import CallToolResult, TextContent

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# Module-level helper functions
# ═════════════════════════════════════════════════════════════════════════════


def _envelope_ok(data: Any) -> str:
    """JSON success body: ``ok``, ``code`` ``OK``, ``data`` (``default=str`` fallback)."""
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
    """JSON error body: ``ok`` false, ``code``, ``message``, ``details``."""
    return json.dumps(
        {"ok": False, "code": code, "message": message, "details": details or {}},
        ensure_ascii=False,
        default=str,
    )


def _validate_tool_request_kwargs(kwargs: dict[str, Any], req_model: type) -> Any:
    """Validate ``kwargs`` with ``req_model``; ``ValidationFieldError`` on failure."""
    try:
        return req_model.model_validate(kwargs)  # type: ignore[attr-defined]
    except PydanticValidationError as exc:
        raise ValidationFieldError(
            "Tool input validation failed",
            details={"errors": exc.errors()},
        ) from exc


def _get_action_class_description(
    action_class: type,
    *,
    coordinator: NodeGraphCoordinator | None = None,
) -> str:
    """``@meta`` description: action graph node property, else ``_meta_info``."""
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


def _class_name_to_snake_case(name: str) -> str:
    """CamelCase → snake_case after stripping trailing ``Action`` (e.g. ``CreateOrderAction`` → ``create_order``)."""
    if name.endswith("Action") and len(name) > len("Action"):
        name = name[: -len("Action")]

    result = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", result)
    return result.lower()


def _mcp_edge_type_from_payload(edge_data: Any) -> str:
    """Normalize rustworkx edge payload to a string edge type for JSON."""
    if isinstance(edge_data, dict):
        return str(edge_data.get("edge_type", ""))
    edge_name = getattr(edge_data, "edge_name", None)
    if edge_name is not None:
        return str(edge_name)
    if isinstance(edge_data, str):
        return edge_data
    return str(edge_data)


def _mcp_optional_string_property(properties: dict[str, Any], key: str) -> str:
    """Return a non-empty string property, ignoring non-string metadata."""
    value = properties.get(key, "")
    if isinstance(value, str) and value:
        return value
    return ""


def _mcp_apply_node_properties_to_node(node: dict[str, Any], graph_node: Any) -> None:
    """Mutate ``node`` with selected public node graph properties."""
    description = _mcp_optional_string_property(graph_node.properties, "description")
    if description:
        node["description"] = description

    if graph_node.node_type == DomainGraphNode.NODE_TYPE:
        domain_name = _mcp_optional_string_property(graph_node.properties, "name")
        if domain_name:
            node["domain_label"] = domain_name


def _build_graph_json(coordinator: NodeGraphCoordinator) -> str:
    """Pretty-printed JSON with ``nodes`` / ``edges`` from the node graph."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for graph_node in coordinator.get_all_nodes():
        node: dict[str, Any] = {
            "id": graph_node.node_id,
            "type": graph_node.node_type,
        }
        _mcp_apply_node_properties_to_node(node, graph_node)

        for edge_data in graph_node.get_all_edges():
            target_node = edge_data.target_node
            if edge_data.edge_name == "domain" and target_node is not None:
                domain_obj = getattr(target_node, "node_obj", None)
                node["domain"] = (
                    f"{domain_obj.__module__}.{domain_obj.__qualname__}"
                    if isinstance(domain_obj, type)
                    else edge_data.target_node_id
                )

        nodes.append(node)

        for edge_data in graph_node.get_all_edges():
            target_node = edge_data.target_node
            target_node_type = getattr(target_node, "node_type", "unknown")
            edge_type = _mcp_edge_type_from_payload(edge_data)
            edges.append({
                "from": graph_node.node_id,
                "to": edge_data.target_node_id,
                "source_key": f"{graph_node.node_type}:{graph_node.node_id}",
                "target_key": f"{target_node_type}:{edge_data.target_node_id}",
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
    connections_factory: Callable[..., dict[str, BaseResource]] | None,
    graph_coordinator: NodeGraphCoordinator,
) -> Callable[..., Any]:
    """Async MCP handler: validate input, ``machine.run``, JSON envelope in ``CallToolResult``."""
    req_model = record.effective_request_model
    has_params_mapper = record.params_mapper is not None
    has_response_mapper = record.response_mapper is not None

    async def handler(**kwargs: Any) -> CallToolResult:
        """One tool invocation; JSON text + ``isError`` from outcome."""
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
        except Exception:  # no `as exc`: response text is fixed; traceback is in logs
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
    handler.__doc__ = record.description or _get_action_class_description(
        record.action_class,
        coordinator=graph_coordinator,
    )

    return handler


async def _execute_tool_call(
    kwargs: dict[str, Any],
    req_model: type,
    record: McpRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResource]] | None,
    has_params_mapper: bool,
    has_response_mapper: bool,
) -> Any:
    """Validate kwargs, map params, ``machine.run``, return data for ``_envelope_ok`` (not wrapped)."""
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
    """Map result if needed; ``model_dump(mode="json")`` for Pydantic models (else pass-through)."""
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
AI-CORE-BEGIN
    ROLE: Exposes ActionMachine actions as MCP tools/resources.
    CONTRACT: BaseAdapter[McpRouteRecord] with tool(), register_all(), build().
    INVARIANTS: auth coordinator required; tool text is JSON envelope.
    AI-CORE-END
"""

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: Any,
        connections_factory: Callable[..., dict[str, BaseResource]] | None = None,
        *,
        server_name: str = "ActionMachine MCP",
        server_version: str = "0.1.0",
    ) -> None:
        """Wire machine, auth, optional connections, and server metadata."""
        super().__init__(
            machine=machine,
            auth_coordinator=auth_coordinator,
            connections_factory=connections_factory,
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
        """Add one tool (``inputSchema`` from request model; ``@meta`` description if description empty)."""
        effective_description = description or _get_action_class_description(
            action_class,
            coordinator=self.graph_coordinator,
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
        """Register tools for action graph nodes that declare at least one aspect."""
        coordinator = self.graph_coordinator

        seen: set[type] = set()
        action_nodes = [
            node
            for node in coordinator.get_all_nodes()
            if isinstance(node, ActionGraphNode)
            and (node.regular_aspect or node.summary_aspect)
        ]
        for node in action_nodes:
            cls = node.node_obj
            if not isinstance(cls, type):
                continue
            if cls in seen or not issubclass(cls, BaseAction):
                continue
            seen.add(cls)

            tool_name = _class_name_to_snake_case(cls.__name__)
            description = str(node.properties.get("description", "") or "")

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
        """Create ``FastMCP`` with registered tools."""
        tools = [self._make_mcp_tool(record) for record in self._routes]
        return FastMCP(self._server_name, tools=tools)

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
            graph_coordinator=self.graph_coordinator,
        )
        arg_model = self._mcp_argument_model(record)
        fn_meta = FuncMetadata(arg_model=arg_model)
        parameters = arg_model.model_json_schema(by_alias=True)
        description = record.description or _get_action_class_description(
            record.action_class,
            coordinator=self.graph_coordinator,
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
