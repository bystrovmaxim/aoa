"""One storage class, three ways to reach its database.

The application chooses how a PostgreSQL storage connects when it assembles it: a pool opened
in a service's lifespan, the storage's own connection for one script run, or a substitute pool
in a test. The storage class is the same in all three, and its transactions stay inside it.
Replace only the driver so the example needs no database.

Run: uv run python examples/extensions/postgresql/16_three_ways.py
"""

import asyncio
from unittest.mock import AsyncMock, patch

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
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


@meta(description="The shop database")
@entities()
class ShopDatabaseStorage(PostgresStorage):
    """One storage class; how it connects is decided when it is built."""

    async def record_visit(self) -> None:
        """Run one statement inside the storage's own transaction."""
        await self._execute("INSERT INTO visits DEFAULT VALUES")


async def unit_of_work(db: ShopDatabaseStorage) -> None:
    """Open, begin, write, commit and close — the same body for every assembly."""
    await db.open()
    await db.begin()
    await db.record_visit()
    await db.commit()
    await db.close()


async def main():
    """Assemble the same storage three ways and run the same unit of work."""
    # 1. A service: one pool for its lifetime, opened in the lifespan.
    service_pool = RecordingPool()
    with patch("aoa.action_machine.resources.postgres.postgres_pool.asyncpg.create_pool", AsyncMock(return_value=service_pool)):
        async with PostgresPool("postgresql://example.invalid/shop", min_size=1, max_size=2) as pool:
            await unit_of_work(ShopDatabaseStorage(pool=pool))
    print("service pool:", service_pool.connections[0].commands, "pool closed:", service_pool.closed)

    # 2. A script: the storage opens its own connection and closes it.
    own = RecordingConnection(1)
    connect = AsyncMock(return_value=own)
    with patch("aoa.action_machine.resources.postgres.postgres_storage.asyncpg.connect", connect):
        await unit_of_work(ShopDatabaseStorage(connection_params="postgresql://example.invalid/shop"))
    print("own connection:", own.commands, "closed:", own.closed)

    # 3. A test: a substitute pool the test holds, wrapped by PostgresPool(pool=...).
    substitute = RecordingPool()
    async with PostgresPool(pool=substitute) as pool:
        await unit_of_work(ShopDatabaseStorage(pool=pool))
    print("substitute pool:", substitute.connections[0].commands)


if __name__ == "__main__":
    asyncio.run(main())
