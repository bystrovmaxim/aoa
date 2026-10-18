"""An earlier resource is cleaned up when a later factory fails.

Two resources are declared. The first opens successfully; construction of the second fails before the operation starts.

Run: uv run python examples/step_17_connections/06_factory_failure.py
"""

import asyncio

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import PerCallConnection


@exclude_graph_model
class TraceResource(BaseResource):
    """Record lifecycle calls without opening an external connection."""
    def __init__(self, events):
        """Keep the event list supplied by the example."""
        self.events = events
    def get_wrapper_class(self):
        """Allow direct use by nested actions."""
        return None
    async def open(self):
        """Record acquisition."""
        self.events.append("open")
    async def close(self):
        """Record release."""
        self.events.append("close")


async def main():
    """Run this case and verify its observable result."""
    events = []
    def fail_factory():
        """Fail before returning a resource."""
        raise ValueError("second factory failed")
    try:
        async with connection_scope({
            "first": PerCallConnection(lambda: TraceResource(events), lambda resource: resource.close()),
            "second": PerCallConnection(fail_factory, lambda resource: events.append("unexpected")),
        }):
            raise AssertionError("The body must not run")
    except ValueError as error:
        print(str(error))
    assert events == ["open", "close"]
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
