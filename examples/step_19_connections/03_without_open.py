"""A resource without open still has a finalizer.

A resource may hold only Python data. Its per-call declaration still has to specify what happens when the call ends.

Run: uv run python examples/step_19_connections/03_without_open.py
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
    @exclude_graph_model
    class NoteController(BaseController):
        """Carry a note for one call."""
        @classmethod
        def get_wrapper_class(cls):
            """Allow direct use."""
            return None

    events = []
    declaration = PerCallConnection(NoteController, lambda resource: events.append("finalize"))
    async with connection_scope({"note": declaration}):
        events.append("use")
    assert events == ["use", "finalize"]
    print(events)


if __name__ == "__main__":
    asyncio.run(main())
