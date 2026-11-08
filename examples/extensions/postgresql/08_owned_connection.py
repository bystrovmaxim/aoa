"""A pool keeps the connection parameters.

``PostgresPool`` holds the address and the pool options, and creates the driver's pool from
them when it opens; a storage built with ``pool=`` takes its connection from it. Replace only
create_pool so the example needs no database.

Run: uv run python examples/extensions/postgresql/08_owned_connection.py
"""

import asyncio
from unittest.mock import AsyncMock, patch

from aoa.action_machine.resources.postgres import PostgresPool, PostgresStorage


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





class ExampleStorage(PostgresStorage):
    """A PostgreSQL resource that works through the example's pool."""


async def main():
    """Run this case and verify its observable result."""
    pool = RecordingPool()
    create_pool = AsyncMock(return_value=pool)
    with patch("aoa.action_machine.resources.postgres.postgres_pool.asyncpg.create_pool", create_pool):
        async with PostgresPool("postgresql://example.invalid/demo", min_size=1, max_size=1) as source:
            db = ExampleStorage(pool=source)
            await db.open()
            await db.close()
    create_pool.assert_awaited_once_with("postgresql://example.invalid/demo", min_size=1, max_size=1)
    assert pool.closed
    print("create_pool calls:", create_pool.await_count)
    print("pool closed by PostgresPool:", pool.closed)


if __name__ == "__main__":
    asyncio.run(main())
