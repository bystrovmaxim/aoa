"""A failed call still releases its resource.

The body of the scope fails after acquisition. Watch the event order, then inspect the error outside the scope.

Run: uv run python examples/step_19_connections/04_failed_call.py
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
    declaration = PerCallConnection(lambda: TraceController(events), lambda resource: resource.close())
    try:
        async with connection_scope({"db": declaration}):
            events.append("use")
            raise ValueError("work failed")
    except ValueError as error:
        print(type(error).__name__ + ": " + str(error))
    assert events == ["open", "use", "close"]
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
