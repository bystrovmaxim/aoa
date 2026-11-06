"""A factory can return the same object.

PerCallConnection calls the factory every time. It cannot guarantee that the factory creates a new resource.

Run: uv run python examples/step_19_connections/11_shared_factory.py
"""

import asyncio

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources import BaseController
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import PerCallConnection


@exclude_graph_model
class TraceController(BaseController):
    """Record lifecycle calls without opening an external connection."""
    def __init__(self, events):
        """Keep the event list supplied by the example."""
        self.events = events
    @classmethod
    def get_wrapper_class(cls):
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
    shared = TraceController(events)
    declaration = PerCallConnection(lambda: shared, lambda resource: resource.close())
    for _ in range(2):
        async with connection_scope({"db": declaration}) as connections:
            assert connections["db"] is shared
    assert events == ["open", "close", "open", "close"]
    print("same object: True")
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
