"""A custom adapter owns the per-call scope.

A dictionary dispatcher is enough to demonstrate a transport boundary. Its handler must wrap the real machine call in connection_scope.

Run: uv run python examples/how_to/01_custom_adapter.py
"""

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import Field

from aoa.action_machine.adapters.base_adapter import BaseAdapter
from aoa.action_machine.adapters.base_route_record import (
    BaseRouteRecord,
    ensure_machine_params,
    ensure_protocol_response,
)
from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import ConnectionValue, PerCallConnection
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.resources import Connections


# ── 1. The route record: one route's contract (frozen, extends BaseRouteRecord) ──
@dataclass(frozen=True)
class CommandRouteRecord(BaseRouteRecord):
    """Describe one dispatcher command."""
    command: str = ""

    def __post_init__(self) -> None:
        """Validate the command after the base record."""
        super().__post_init__()                       # base validates action P/R + mapper rules
        if not self.command or not self.command.strip():
            raise ValueError("command must be a non-empty string.")


# ── 2. The adapter: registration (.command) + build() → dispatcher ───────────
class DictAdapter(BaseAdapter[CommandRouteRecord]):

    """Publish actions through an in-process dispatcher."""
    def command(
        self,
        name: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        *,
        connections: Mapping[str, ConnectionValue] | None = None,
    ) -> "DictAdapter":
        """Register one command and its resource declaration."""
        return self._add_route(CommandRouteRecord(
            action_class=action_class, request_model=request_model, response_model=response_model,
            params_mapper=params_mapper, response_mapper=response_mapper,
            connections=connections, command=name,
        ))

    def build(self) -> Callable[[str, dict[str, Any]], Any]:
        """Build the command dispatcher."""
        handlers = {r.command: self._make_handler(r) for r in self._routes}

        async def call(command: str, payload: dict[str, Any]) -> Any:
            """Dispatch one command."""
            return await handlers[command](payload)

        return call

    def _make_handler(self, record: CommandRouteRecord) -> Callable[[dict[str, Any]], Any]:
        """Build the handler for one route record."""
        async def handler(payload: dict[str, Any]) -> Any:
            # validate input into the effective request model, then map to Params
            """Validate and execute one call inside its resource scope."""
            body = record.effective_request_model.model_validate(payload)
            params = record.params_mapper(body) if record.params_mapper else body
            ensure_machine_params(params, record.params_type, adapter="Dict", route_label=record.command)
            # Context at the boundary, connections per route, then the real machine
            context = await self.effective_auth_coordinator(record).process(None)
            if context is None:
                raise AuthorizationError("Authentication required")
            async with connection_scope(record.connections) as connections:
                result = await self._machine.run(context, record.action_class(), params, connections)
            if record.response_mapper:
                mapped = record.response_mapper(result)
                ensure_protocol_response(mapped, record.effective_response_model, adapter="Dict", route_label=record.command)
                return mapped.model_dump() if hasattr(mapped, "model_dump") else mapped
            return result.model_dump()

        return handler


# ── A normal Action — it knows nothing about the new transport ───────────────
class GreetingDomain(BaseDomain):
    """Group the greeting example."""
    name = "greeting"
    description = "Greetings domain"


@meta(description="Supply a greeting prefix", domain=GreetingDomain)
class GreetingResource(BaseResource):
    """Represent a handle owned by one dispatcher call."""
    def __init__(self, events):
        """Keep the lifecycle log."""
        self.events = events
    def get_wrapper_class(self):
        """Allow direct use of this non-transactional handle."""
        return None
    async def open(self):
        """Record acquisition."""
        self.events.append("open")
    async def close(self):
        """Record release."""
        self.events.append("close")
    def prefix(self):
        """Return the transport-provided prefix."""
        return "Hello"


class GreetParams(BaseParams):
    """Describe the person to greet."""
    name: str = Field(description="Person to greet")


class GreetResult(BaseResult):
    """Return the greeting text."""
    message: str = Field(description="Greeting")


@meta(description="Greet a person", domain=GreetingDomain)
@check_roles(GuestRole)
@connection(GreetingResource, key="greeting")
class GreetAction(BaseAction[GreetParams, GreetResult]):
    """Build a greeting using the supplied resource."""

    @summary_aspect("Build greeting")
    async def greet_summary(self, params: GreetParams, state: BaseState, box: ToolsBox, connections: Connections) -> GreetResult:
        """Combine the prefix and requested name."""
        prefix = connections["greeting"].prefix()
        return GreetResult(message=f"{prefix}, {params.name}!")




async def main():
    """Run this case and verify its observable result."""
    events = []
    call = (DictAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=NoAuthCoordinator(context=Context()))
        .command("greet", GreetAction, connections={"greeting": PerCallConnection(
            lambda: GreetingResource(events), lambda resource: resource.close(),
        )}).build())
    result = await call("greet", {"name": "Alice"})
    assert result == {"message": "Hello, Alice!"}
    assert events == ["open", "close"]
    print(result)
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
