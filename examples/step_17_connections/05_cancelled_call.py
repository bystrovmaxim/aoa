"""Cancellation also runs cleanup.

Cancellation asks an asynchronous task to stop. It is a separate exit path from a normal result or an ordinary exception.

Run: uv run python examples/step_17_connections/05_cancelled_call.py
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
    started = asyncio.Event()
    async def work():
        """Wait until the caller cancels this task."""
        declaration = PerCallConnection(lambda: TraceResource(events), lambda resource: resource.close())
        async with connection_scope({"db": declaration}):
            started.set()
            await asyncio.Event().wait()
    task = asyncio.create_task(work())
    await started.wait()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("CancelledError")
    assert events == ["open", "close"]
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
