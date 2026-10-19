"""The same per-call lifecycle for an MCP tool.

Call the server in process. The counter action and per-call declaration are the same as for HTTP.

Run: uv run python examples/step_17_connections/15_mcp_call.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox


class CounterDomain(BaseDomain):
    """Group this example's resource and action."""
    name = "counter"
    description = "Counter example"

class EmptyParams(BaseParams):
    """No input fields are needed for this case."""

@meta(description="Count calls in memory", domain=CounterDomain)
class CounterResource(BaseResource):
    """Keep a count and record lifecycle events."""
    def __init__(self, events):
        """Start with an empty count."""
        self.count = 0
        self.events = events
    def get_wrapper_class(self):
        """Allow direct use of this in-memory counter."""
        return None
    async def open(self):
        """Record opening without resetting the count."""
        self.events.append("open")
    async def close(self):
        """Record cleanup without acquiring external handles."""
        self.events.append("close")

class CountResult(BaseResult):
    """Expose the count reached by one call."""
    count: int = Field(description="Number of calls seen by this resource")

@meta(description="Increment the supplied counter", domain=CounterDomain)
@check_roles(GuestRole)
@connection(CounterResource, key="counter")
class CountAction(BaseAction[EmptyParams, CountResult]):
    """Increment the supplied resource once."""
    @summary_aspect("Count one call")
    async def count_summary(self, params: EmptyParams, state: BaseState, box: ToolsBox, connections: Connections) -> CountResult:
        """Return the updated count."""
        counter = connections["counter"]
        counter.count += 1
        return CountResult(count=counter.count)

import json
from contextlib import asynccontextmanager

from aoa.mcp import McpAdapter
from aoa.action_machine.resources import Connections


async def main():
    """Run this case and verify its observable result."""
    events = []
    @asynccontextmanager
    async def lifespan(server):
        """Surround tool calls with service startup and shutdown."""
        events.append("startup")
        try:
            yield
        finally:
            events.append("shutdown")
    server = (McpAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=NoAuthCoordinator(context=Context()))
        .tool("count", CountAction, connections={"counter": PerCallConnection(
            lambda: CounterResource(events), lambda resource: resource.close(),
        )}).build(lifespan=lifespan))
    # Direct calls do not start a network server; enter its configured lifespan explicitly.
    async with server.settings.lifespan(server):
        response = await server.call_tool("count", {})
        payload = json.loads(response.content[0].text)
        assert payload["data"] == {"count": 1}
        print(payload)
    assert events == ["startup", "open", "close", "shutdown"]
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
