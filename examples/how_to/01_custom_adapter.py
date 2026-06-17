"""
01_custom_adapter.py — Write your own transport adapter

An adapter publishes the same Action over a new transport (gRPC, a queue, a CLI)
without touching the Action. You implement two small things on top of the base
classes:

  - a frozen `BaseRouteRecord` subclass — one route's contract (which Action,
    optional external models + mappers, per-route connections);
  - a `BaseAdapter[YourRecord]` subclass — a registration method that appends
    routes, and build() that turns them into your transport, where each handler
    runs the same per-request flow every shipped adapter uses:
        validate input -> params -> auth_coordinator.process -> resolve_connections
        -> machine.run -> (response_mapper) -> serialize

Here the "transport" is a plain async dispatcher `call(command, payload_dict)` —
enough to show the contract end-to-end, in process.

How-to: ../../docs/how-to/authoring-adapter_draft.md

Run:
    uv run python examples/how_to/01_custom_adapter.py
"""

import asyncio
from dataclasses import dataclass
from typing import Any
from collections.abc import Callable, Mapping

from pydantic import Field

from aoa.action_machine.adapters.base_adapter import BaseAdapter
from aoa.action_machine.adapters.base_route_record import BaseRouteRecord, ensure_machine_params
from aoa.action_machine.auth import NoAuthCoordinator, NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.per_call_connection import ConnectionValue, resolve_connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


# ── 1. The route record: one route's contract (frozen, extends BaseRouteRecord) ──
@dataclass(frozen=True)
class CommandRouteRecord(BaseRouteRecord):
    command: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()                       # base validates action P/R + mapper rules
        if not self.command or not self.command.strip():
            raise ValueError("command must be a non-empty string.")


# ── 2. The adapter: registration (.command) + build() → dispatcher ───────────
class DictAdapter(BaseAdapter[CommandRouteRecord]):

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
        return self._add_route(CommandRouteRecord(
            action_class=action_class, request_model=request_model, response_model=response_model,
            params_mapper=params_mapper, response_mapper=response_mapper,
            connections=connections, command=name,
        ))

    def build(self) -> Callable[[str, dict[str, Any]], Any]:
        handlers = {r.command: self._make_handler(r) for r in self._routes}

        async def call(command: str, payload: dict[str, Any]) -> Any:
            return await handlers[command](payload)

        return call

    def _make_handler(self, record: CommandRouteRecord) -> Callable[[dict[str, Any]], Any]:
        async def handler(payload: dict[str, Any]) -> Any:
            # validate input into the effective request model, then map to Params
            body = record.effective_request_model.model_validate(payload)
            params = record.params_mapper(body) if record.params_mapper else body
            ensure_machine_params(params, record.params_type, adapter="Dict", route_label=record.command)
            # Context at the boundary, connections per route, then the real machine
            context = await self._auth_coordinator.process(None) or Context()
            connections = resolve_connections(record.connections)
            result = await self._machine.run(context, record.action_class(), params, connections)
            if record.response_mapper:
                mapped = record.response_mapper(result)
                return mapped.model_dump() if hasattr(mapped, "model_dump") else mapped
            return result.model_dump()

        return handler


# ── A normal Action — it knows nothing about the new transport ───────────────
class GreetingDomain(BaseDomain):
    name = "greeting"
    description = "Greetings domain"


class GreetParams(BaseParams):
    name: str = Field(description="Person to greet")


class GreetResult(BaseResult):
    message: str = Field(description="Greeting")


@meta(description="Greet a person", domain=GreetingDomain)
@check_roles(NoneRole)
class GreetAction(BaseAction[GreetParams, GreetResult]):
    @summary_aspect("Build greeting")
    async def greet_summary(self, params, state, box, connections):
        return GreetResult(message=f"Hello, {params.name}!")


async def main() -> None:
    call = (
        DictAdapter(machine=ActionProductMachine(), auth_coordinator=NoAuthCoordinator())
        .command("greet", GreetAction)
        .build()
    )
    out = await call("greet", {"name": "Alice"})
    print(f'call("greet", {{"name": "Alice"}}) -> {out}')


if __name__ == "__main__":
    asyncio.run(main())
