"""Cleanup failure after successful work.

The body succeeds, but its finalizer fails. A successful body does not make the entire call successful.

Run: uv run python examples/step_17_connections/08_close_failure.py
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


def fail_close(resource):
    """Simulate an operational release failure."""
    resource.events.append("close failed")
    raise OSError("release unavailable")


async def main():
    """Run this case and verify its observable result."""
    events = []
    try:
        async with connection_scope({"db": PerCallConnection(lambda: TraceResource(events), fail_close)}):
            events.append("use")
    except OSError as error:
        print(type(error).__name__ + ": " + str(error))
    assert events == ["open", "use", "close failed"]
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
