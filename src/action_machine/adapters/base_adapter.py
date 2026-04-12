# src/action_machine/adapters/base_adapter.py
"""
BaseAdapter[R] — abstract base class for all protocol adapters.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the unified contract for adapters that translate external protocols
(HTTP, MCP, gRPC, CLI) into calls to ``machine.run(context, action, params, connections)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Concrete adapters (FastApiAdapter, McpAdapter, etc.) inherit ``BaseAdapter``,
implement protocol-specific registration methods (``post``, ``get``, ``tool``),
and implement ``build()`` to return a protocol application.

The adapter holds a reference to the machine, an authentication coordinator,
an optional explicit ``GateCoordinator`` (defaults to ``machine.gate_coordinator``),
and an optional connections factory. Registered routes are stored in ``_routes``
as concrete ``BaseRouteRecord`` subclasses.

::

    ┌──────────────────────────────────────┐
    │  BaseAdapter[R]                      │
    │                                      │
    │  machine: ActionProductMachine       │
    │  auth_coordinator: Any (required)    │
    │  gate_coordinator: GateCoordinator   │
    │    (optional; defaults to machine)     │
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
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``auth_coordinator`` is required; passing ``None`` raises ``TypeError``.
- ``machine`` must be an instance of ``ActionProductMachine``.
- ``gate_coordinator`` defaults to ``machine.gate_coordinator`` when omitted.
- Route records are stored in ``_routes`` and remain immutable after registration.
- The fluent API returns ``self``, enabling method chaining.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # With authentication
    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=AuthCoordinator(extractor, authenticator, assembler),
    )

    # Without authentication (explicit declaration)
    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``TypeError`` if ``machine`` is not ``ActionProductMachine``.
- ``TypeError`` if ``auth_coordinator`` is ``None``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Abstract base for all protocol adapters.
CONTRACT: Subclasses must implement protocol methods and ``build()``; auth is required.
INVARIANTS: ``_routes`` holds route records; ``gate_coordinator`` resolved at init;
  fluent API returns ``self``.
FLOW: route registration -> ``_add_route`` -> ``build()`` produces protocol app.
FAILURES: Constructor raises ``TypeError`` on invalid machine or missing auth.
EXTENSION POINTS: New adapters subclass ``BaseAdapter`` and define concrete ``RouteRecord``.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Self

from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .base_route_record import BaseRouteRecord


class BaseAdapter[R: BaseRouteRecord](ABC):
    """
    Abstract base class for all ActionMachine protocol adapters.

    The auth_coordinator parameter is required. For open APIs, use
    NoAuthCoordinator as an explicit declaration of no authentication.
    """

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: Any,
        connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = None,
        *,
        gate_coordinator: GateCoordinator | None = None,
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
        self._gate_coordinator: GateCoordinator = (
            gate_coordinator
            if gate_coordinator is not None
            else machine.gate_coordinator
        )
        self._connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = connections_factory
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
    def gate_coordinator(self) -> GateCoordinator:
        """Returns the gate graph coordinator (explicit or from ``machine``)."""
        return self._gate_coordinator

    @property
    def connections_factory(self) -> Callable[..., dict[str, BaseResourceManager]] | None:
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
