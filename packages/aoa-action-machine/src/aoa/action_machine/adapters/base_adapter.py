# packages/aoa-action-machine/src/aoa/action_machine/adapters/base_adapter.py
"""
BaseAdapter[R] — abstract foundation for protocol adapters.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the shared contract for adapters that translate external protocols
(HTTP, MCP, gRPC, CLI) into
``machine.run(context, action, params, connections)`` calls.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Concrete adapters (FastApiAdapter, McpAdapter, etc.) inherit ``BaseAdapter``,
implement protocol-specific registration methods (``post``, ``get``, ``tool``),
and implement ``build()`` to produce a protocol application object.

The adapter stores a machine reference, an authentication coordinator, and the
machine's ``NodeGraphCoordinator``. Per-route connection wiring lives on each
``BaseRouteRecord`` (``connections`` + :func:`~aoa.action_machine.resources.per_call_connection.resolve_connections`).
Registered routes are accumulated in
``_routes`` as concrete ``BaseRouteRecord`` subclasses.

A route may also override the adapter's default ``auth_coordinator`` via
``BaseRouteRecord.auth_coordinator``. Concrete adapters resolve the coordinator
to use for one request through :meth:`effective_auth_coordinator`, which returns
the per-route override when set, else the adapter-wide default. This lets a
public route (e.g. a login endpoint) sit next to routes protected by a strict
default coordinator, without weakening the default for every other route.

::

    ┌──────────────────────────────────────┐
    │  BaseAdapter[R]                      │
    │                                      │
    │  machine: ActionProductMachine       │
    │  auth_coordinator: Any (required)    │
    │  graph_coordinator: NodeGraphCoordinator │
    │  _routes: list[R]                    │
    │                                      │
    │  _add_route(record: R) → Self        │
    │  effective_auth_coordinator(record: R) → Any │
    │  build() → Any                       │
    └──────────────────────────────────────┘
               ▲
    ┌──────────┴──────────────────────────┐
    │  FastApiAdapter                      │
    │  McpAdapter                          │
    └──────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
ADAPTER TESTING CONTRACT
═══════════════════════════════════════════════════════════════════════════════

Integration-style adapter tests use production types: a real
``ActionProductMachine`` and its ``NodeGraphCoordinator``. The adapter, route records,
validation, and transport mapping run as shipped.

When a test must fix outcomes or skip the full action pipeline, only
``machine.run(...)`` is stubbed (e.g. ``AsyncMock``). That is a seam on the
execution boundary, not a hand-written fake machine or duplicate adapter logic.

::

    Agent / protocol host
             |
             v
    +-----------------------------+
    | Adapter (production)        |
    | NodeGraphCoordinator (real)  |
    | ActionProductMachine (real) |
    +-----------------------------+
             |
             |  machine.run(context, action, params, connections)
             v
    +-----------------------------+
    | Action pipeline             |  <- optional test seam (stub ``run`` only)
    | (aspects, checkers, ...)    |
    +-----------------------------+

Prefer the real machine class plus a ``run`` stub for handler-level scenarios;
replace ``ActionProductMachine`` only when testing constructor wiring itself.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Self

from aoa.action_machine.adapters.base_route_record import BaseRouteRecord
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class BaseAdapter[R: BaseRouteRecord](ABC):
    """
    AI-CORE-BEGIN
        ROLE: Transport bridge — exposes Actions via an external protocol.
        CONTRACT: Translation only, no business logic.
        INVARIANTS: One adapter — one protocol.
        AI-CORE-END
    """

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: Any,
    ) -> None:
        """
        Initialize the adapter.

        Raises:
            TypeError: if machine is not ActionProductMachine.
            TypeError: if auth_coordinator is None.
        """
        if not isinstance(machine, ActionProductMachine):
            raise TypeError(f"BaseAdapter expects ActionProductMachine, " f"got {type(machine).__name__}: {machine!r}.")

        if auth_coordinator is None:
            raise TypeError(
                "auth_coordinator is required. Pass AuthCoordinator "
                "for authenticated APIs or NoAuthCoordinator(context=Context()) for open APIs."
            )

        self._machine: ActionProductMachine = machine
        self._auth_coordinator: Any = auth_coordinator
        self._graph_coordinator: NodeGraphCoordinator = machine.graph_coordinator
        self._routes: list[R] = []

    @property
    def machine(self) -> ActionProductMachine:
        """Returns the action execution machine."""
        return self._machine

    @property
    def auth_coordinator(self) -> Any:
        """Returns the authentication coordinator."""
        return self._auth_coordinator

    @property
    def graph_coordinator(self) -> NodeGraphCoordinator:
        """Returns the machine node graph coordinator."""
        return self._graph_coordinator

    @property
    def routes(self) -> list[R]:
        """Returns the list of registered routes."""
        return self._routes

    def _add_route(self, record: R) -> Self:
        """Add a RouteRecord to the route list and return self (fluent API)."""
        self._routes.append(record)
        return self

    def effective_auth_coordinator(self, record: R) -> Any:
        """Return ``record.auth_coordinator`` when set, else the adapter's default coordinator."""
        return record.auth_coordinator if record.auth_coordinator is not None else self._auth_coordinator

    @abstractmethod
    def build(self) -> Any:
        """
        Create the protocol application from registered routes.

        Returns:
            Protocol-specific application (FastAPI, MCP, etc.).
        """
