"""A child cannot enter the owner’s lifecycle.

The standard wrapper does not let a child manage its owner’s connection.

Run: uv run python examples/step_19_resource/06_wrapper_context.py
"""

import asyncio

from aoa.action_machine.resources.postgres import PostgresResource


class RecordingConnection:
    """Record commands; do not parse SQL or simulate database storage."""
    def __init__(self, number):
        """Give this connection a visible identity."""
        self.number = number
        self.commands = []
        self.busy = False
        self.closed = False
    async def execute(self, query, *params):
        """Reject concurrent use and record one command."""
        if self.busy or self.closed:
            raise RuntimeError("connection is busy or closed")
        self.busy = True
        try:
            await asyncio.sleep(0)
            self.commands.append(query)
            return "OK"
        finally:
            self.busy = False
    async def close(self):
        """Mark the physical connection closed."""
        self.closed = True

class RecordingPool:
    """Offer a fixed number of observable connections without a server."""
    def __init__(self, size=1):
        """Create the fixed capacity used by this example."""
        self.connections = [RecordingConnection(i + 1) for i in range(size)]
        self.free = asyncio.Queue()
        for connection in self.connections:
            self.free.put_nowait(connection)
        self.held = set()
        self.closed = False
    async def acquire(self, *, timeout=None):
        """Wait for an available connection with the supplied bound."""
        connection = await asyncio.wait_for(self.free.get(), timeout)
        self.held.add(connection)
        return connection
    async def release(self, connection):
        """Return a borrowed connection exactly once."""
        self.held.remove(connection)
        self.free.put_nowait(connection)
    async def close(self):
        """Close the pool only after all borrowers have returned."""
        assert not self.held
        for connection in self.connections:
            await connection.close()
        self.closed = True

from aoa.action_machine.exceptions import TransactionProhibitedError
from aoa.action_machine.resources.sql import WrapperSqlResource


async def main():
    """Run this case and verify its observable result."""
    pool = RecordingPool()
    owner = PostgresResource(pool=pool)
    await owner.open()
    child_view = WrapperSqlResource(owner)
    try:
        async with child_view:
           raise AssertionError("The context must not open")
    except TransactionProhibitedError as error:
        print(type(error).__name__)
    else:
        raise AssertionError("The wrapper allowed lifecycle control")
    assert len(pool.held) == 1
    print("owner still holds connection:", len(pool.held) == 1)
    await owner.close()
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
