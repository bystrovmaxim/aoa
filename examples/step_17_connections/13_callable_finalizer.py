"""Registration rejects a non-callable finalizer.

A present value is not enough: the adapter must be able to call finalize.

Run: uv run python examples/step_17_connections/13_callable_finalizer.py
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

from aoa.action_machine.resources.per_call_connection import validate_connection_entries


async def main():
    """Run this case and verify its observable result."""
    try:
        validate_connection_entries({"db": PerCallConnection(lambda: TraceResource([]), finalize=None)})
    except TypeError as error:
        assert str(error) == "PerCallConnection.finalize must be callable."
        print(str(error))
    else:
        raise AssertionError("Non-callable finalize was accepted")


if __name__ == "__main__":
    asyncio.run(main())
