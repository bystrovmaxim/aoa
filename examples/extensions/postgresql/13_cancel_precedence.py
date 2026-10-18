"""Cancellation remains primary after a contract violation.

Cancel a call while its transaction is open. Cleanup must release its connection without turning cancellation into an ordinary error.

Run: uv run python examples/extensions/postgresql/13_cancel_precedence.py
"""

import asyncio

from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import PerCallConnection
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
    pool = RecordingPool()
    started = asyncio.Event()
    async def work():
        """Wait with an intentionally unfinished transaction."""
        async with connection_scope({"db": PerCallConnection(lambda: PostgresResource(pool=pool), lambda resource: resource.close())}) as connections:
            await connections["db"].begin()
            started.set()
            await asyncio.Event().wait()
    task = asyncio.create_task(work())
    await started.wait()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError as error:
        assert "TransactionLeftOpenError" in error.__notes__[0]
        print("CancelledError")
        print("contract violation recorded:", "TransactionLeftOpenError" in error.__notes__[0])
    assert not pool.held
    print(pool.connections[0].commands)
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
