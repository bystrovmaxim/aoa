"""A resource can own its connection without a pool.

The direct form calls asyncpg.connect in open and the connection’s close in cleanup. Replace only connect so the example needs no database.

Run: uv run python examples/extensions/postgresql/08_owned_connection.py
"""

import asyncio
from aoa.action_machine.resources.postgres import PostgresResource
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.exceptions import HandleError, TransactionLeftOpenError

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

from unittest.mock import AsyncMock, patch


async def main():
    """Run this case and verify its observable result."""
    connection = RecordingConnection(1)
    connect = AsyncMock(return_value=connection)
    with patch("aoa.action_machine.resources.postgres.postgres_resource.asyncpg.connect", connect):
        db = PostgresResource({"dsn": "postgresql://example.invalid/demo"})
        await db.open()
        await db.close()
    connect.assert_awaited_once_with(dsn="postgresql://example.invalid/demo")
    assert connection.closed
    print("connect calls:", connect.await_count)
    print("physical connection closed:", connection.closed)


if __name__ == "__main__":
    asyncio.run(main())
