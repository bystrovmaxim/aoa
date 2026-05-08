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

The adapter stores a machine reference, an authentication coordinator, the
machine's ``NodeGraphCoordinator``, and an optional connections factory.
Registered routes are accumulated in
``_routes`` as concrete ``BaseRouteRecord`` subclasses.

::

    ┌──────────────────────────────────────┐
    │  BaseAdapter[R]                      │
    │                                      │
    │  machine: ActionProductMachine       │
    │  auth_coordinator: Any (required)    │
    │  graph_coordinator: NodeGraphCoordinator │
    │  connections_factory: Fn | None      │
    │  _routes: list[R]                    │
    │                                      │
    │  _add_route(record: R) → Self        │
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
from collections.abc import Callable
from typing import Any, Self

from aoa.action_machine.adapters.base_route_record import BaseRouteRecord
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator


class BaseAdapter[R: BaseRouteRecord](ABC):
    """
AI-CORE-BEGIN
    ROLE: Protocol-agnostic adapter contract and shared state holder.
    CONTRACT: Validates constructor dependencies, stores route records, and exposes abstract ``build()``.
    INVARIANTS: machine type is strict; auth coordinator is mandatory; route registration preserves order.
    AI-CORE-END
"""

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: Any,
        connections_factory: Callable[..., dict[str, BaseResource]] | None = None,
    ) -> None:
        """
        Initialize the adapter.

        Raises:
            TypeError: if machine is not ActionProductMachine.
            TypeError: if auth_coordinator is None.
        """
        if not isinstance(machine, ActionProductMachine):
            raise TypeError(
                f"BaseAdapter expects ActionProductMachine, "
                f"got {type(machine).__name__}: {machine!r}."
            )

        if auth_coordinator is None:
            raise TypeError(
                "auth_coordinator is required. Pass AuthCoordinator "
                "for authenticated APIs or NoAuthCoordinator() for open APIs."
            )

        self._machine: ActionProductMachine = machine
        self._auth_coordinator: Any = auth_coordinator
        self._graph_coordinator: NodeGraphCoordinator = machine.graph_coordinator
        self._connections_factory: Callable[..., dict[str, BaseResource]] | None = connections_factory
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
    def connections_factory(self) -> Callable[..., dict[str, BaseResource]] | None:
        """Returns the connections factory (or None)."""
        return self._connections_factory

    @property
    def routes(self) -> list[R]:
        """Returns the list of registered routes."""
        return self._routes

    def _add_route(self, record: R) -> Self:
        """Add a RouteRecord to the route list and return self (fluent API)."""
        self._routes.append(record)
        return self

    @abstractmethod
    def build(self) -> Any:
        """
        Create the protocol application from registered routes.

        Returns:
            Protocol-specific application (FastAPI, MCP, etc.).
        """
