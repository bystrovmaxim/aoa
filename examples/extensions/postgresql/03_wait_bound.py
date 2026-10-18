"""An exhausted pool has a bounded wait.

The only connection is held by the first resource. A second resource must time out rather than borrow that occupied connection.

Run: uv run python examples/extensions/postgresql/03_wait_bound.py
"""

import asyncio

from aoa.action_machine.exceptions import HandleError
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


async def main():
    """Run this case and verify its observable result."""
    class QuickResource(PostgresResource):
        """Use a short wait so this failure is quick to reproduce."""
        acquire_timeout = 0.01
    pool = RecordingPool()
    first = PostgresResource(pool=pool)
    second = QuickResource(pool=pool)
    await first.open()
    try:
        await second.open()
    except HandleError as error:
        assert isinstance(error.__cause__, TimeoutError)
        print(type(error).__name__, "caused by", type(error.__cause__).__name__)
    else:
        raise AssertionError("The occupied connection was reused")
    finally:
        await first.close()
        await second.close()
    assert not pool.held
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
