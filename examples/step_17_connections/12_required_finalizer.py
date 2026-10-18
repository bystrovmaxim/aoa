"""A per-call declaration must include cleanup.

Omitting finalize fails when the declaration is constructed, before any call is served.

Run: uv run python examples/step_17_connections/12_required_finalizer.py
"""

import asyncio

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_resource import BaseResource
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
    try:
        PerCallConnection(factory=lambda: TraceResource([]))
    except TypeError as error:
        assert "finalize" in str(error)
        print("TypeError: finalize is required")
    else:
        raise AssertionError("Missing finalize was accepted")


if __name__ == "__main__":
    asyncio.run(main())
