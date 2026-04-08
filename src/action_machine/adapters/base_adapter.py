# src/action_machine/adapters/base_adapter.py
"""
BaseAdapter[R] — abstract base class for all protocol adapters.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

BaseAdapter is the unified contract for adapters that translate external
protocols (HTTP, MCP, gRPC, CLI) into calls to
``machine.run(context, action, params, connections)``.

═══════════════════════════════════════════════════════════════════════════════
REQUIRED AUTHENTICATION
═══════════════════════════════════════════════════════════════════════════════

The auth_coordinator parameter is required. The developer cannot "forget"
to configure authentication — this is a constructor error (TypeError), not a
silent production bug.

For open APIs, use NoAuthCoordinator — an explicit declaration of no
authentication:

    from action_machine.auth.no_auth_coordinator import NoAuthCoordinator

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

NoAuthCoordinator implements the same interface as AuthCoordinator:
async method process(request_data) → Context. It always returns an anonymous
Context with empty UserInfo (user_id=None, roles=[]).

═══════════════════════════════════════════════════════════════════════════════
MAPPER NAMING CONVENTION
═══════════════════════════════════════════════════════════════════════════════

    params_mapper   → returns params   (transforms request → params)
    response_mapper → returns response (transforms result  → response)

═══════════════════════════════════════════════════════════════════════════════
FLUENT API
═══════════════════════════════════════════════════════════════════════════════

The ``_add_route(record)`` method returns ``self``, allowing concrete adapters
to build chains using ``return self._add_route(record)`` in protocol methods
(post, get, tool, etc.).

The ``build()`` method terminates the chain and returns the protocol app.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────────────────────┐
    │  BaseAdapter[R]                      │
    │                                      │
    │  machine: ActionProductMachine       │
    │  auth_coordinator: Any (required)    │
    │  connections_factory: Fn | None      │
    │  _routes: list[R]                    │
    │                                      │
    │  _add_route(record: R) → Self        │
    │  build() → Any                       │
    └──────────────────────────────────────┘
               ▲
    ┌──────────┴──────────────────────────┐
    │  FastAPIAdapter                      │
    │  MCPAdapter                          │
    └──────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE USAGE
═══════════════════════════════════════════════════════════════════════════════

    # With authentication:
    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=AuthCoordinator(extractor, authenticator, assembler),
    )

    # Without authentication (explicit declaration):
    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

    # MCP adapter:
    adapter = McpAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Self

from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .base_route_record import BaseRouteRecord


class BaseAdapter[R: BaseRouteRecord](ABC):
    """
    Abstract base class for all ActionMachine protocol adapters.

    The auth_coordinator parameter is required. For open APIs, use
    NoAuthCoordinator as an explicit declaration of no authentication.

    Attributes:
        _machine : ActionProductMachine
            The action execution machine.

        _auth_coordinator : Any
            The authentication coordinator. AuthCoordinator or NoAuthCoordinator.
            This parameter is required and cannot be None.

        _connections_factory : Callable[..., dict[str, BaseResourceManager]] | None
            The connections factory.

        _routes : list[R]
            The list of registered routes.
    """

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: Any,
        connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = None,
    ) -> None:
        """
        Initializes the adapter.

        Args:
            machine: the action execution machine. Required parameter.
                     Must be an instance of ActionProductMachine.
            auth_coordinator: the authentication coordinator. Required parameter.
                              For open APIs, use NoAuthCoordinator().
                              None is not allowed — TypeError.
            connections_factory: the connections factory. If None,
                                 connections are not passed.

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
                "for authenticated APIs or NoAuthCoordinator() for open APIs. "
                "Example: adapter = FastApiAdapter(machine=machine, "
                "auth_coordinator=NoAuthCoordinator())"
            )

        self._machine: ActionProductMachine = machine
        self._auth_coordinator: Any = auth_coordinator
        self._connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = connections_factory
        self._routes: list[R] = []

    # ─────────────────────────────────────────────────────────────────────
    # Properties (read-only)
    # ─────────────────────────────────────────────────────────────────────

    @property
    def machine(self) -> ActionProductMachine:
        """Returns the action execution machine."""
        return self._machine

    @property
    def auth_coordinator(self) -> Any:
        """Returns the authentication coordinator."""
        return self._auth_coordinator

    @property
    def connections_factory(self) -> Callable[..., dict[str, BaseResourceManager]] | None:
        """Returns the connections factory (or None)."""
        return self._connections_factory

    @property
    def routes(self) -> list[R]:
        """Returns the list of registered routes."""
        return self._routes

    # ─────────────────────────────────────────────────────────────────────
    # Internal registration method (fluent)
    # ─────────────────────────────────────────────────────────────────────

    def _add_route(self, record: R) -> Self:
        """
        Adds a RouteRecord to the route list and returns self.

        Returning self enables a fluent API.
        """
        self._routes.append(record)
        return self

    # ─────────────────────────────────────────────────────────────────────
    # Abstract methods
    # ─────────────────────────────────────────────────────────────────────

    @abstractmethod
    def build(self) -> Any:
        """
        Creates the protocol application from registered routes.

        Returns:
            Protocol-specific application:
            - FastAPIAdapter.build() → FastAPI
            - MCPAdapter.build() → FastMCP
        """
