"""A resource whose open fails is finalized.

Construction and acquisition are separate steps. A resource can exist even when opening it fails.

Run: uv run python examples/step_17_connections/07_open_failure.py
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
    @exclude_graph_model
    class BrokenResource(TraceResource):
        """Fail while acquiring a connection."""
        async def open(self):
            """Report failed acquisition."""
            self.events.append("open failed")
            raise OSError("unavailable")
    events = []
    try:
        async with connection_scope({"db": PerCallConnection(
            lambda: BrokenResource(events), lambda resource: resource.close(),
        )}):
            raise AssertionError("The body must not run")
    except OSError as error:
        print(str(error))
    assert events == ["open failed", "close"]
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
