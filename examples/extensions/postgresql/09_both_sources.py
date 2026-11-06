"""A PostgreSQL resource takes no connection parameters.

Connection parameters live only in a data source. A resource given them is refused.

Run: uv run python examples/extensions/postgresql/09_both_sources.py
"""

import asyncio

from aoa.action_machine.resources.postgres import PostgresDataSource, PostgresResource


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

class ExampleDataSource(PostgresDataSource):
    """The database of this example: it hands out the recording pool's connections."""


class ExampleResource(PostgresResource[ExampleDataSource]):
    """A PostgreSQL resource that works through the example's data source."""


async def main():
    """Run this case and verify its observable result."""
    try:
        ExampleResource({"dsn": "example"}, data_source=ExampleDataSource(pool=RecordingPool()))
    except TypeError:
        print("TypeError")
    else:
        raise AssertionError("Invalid construction was accepted")


if __name__ == "__main__":
    asyncio.run(main())
