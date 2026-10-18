"""Reading a page and a count through the protected helpers.

``_fetch`` answers every row the driver returned; ``_fetchval`` answers the first value of the
first row. Both take positional parameters the way the existing pair does, refuse a resource
that is not open with the framework's named error, and wrap a driver failure with its cause.

Run: uv run python examples/extensions/postgresql/15_fetch_and_fetchval.py
"""

import asyncio
from typing import Any

from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.resources.postgres import PostgresResource


class RecordingConnection:
    """A connection that answers the two new reads and records what it was asked for."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.value: Any = None
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.closed = False

    async def fetch(self, query: str, *params: Any) -> list[dict[str, Any]]:
        """Answer the seeded page and record the statement with its parameters."""
        self._check_open()
        self.calls.append((query, params))
        return [dict(row) for row in self.rows]

    async def fetchval(self, query: str, *params: Any) -> Any:
        """Answer the seeded value and record the statement with its parameters."""
        self._check_open()
        self.calls.append((query, params))
        return self.value

    async def close(self) -> None:
        """Mark the physical connection closed."""
        self.closed = True

    def _check_open(self) -> None:
        """Refuse a read once the connection is closed, as the driver does."""
        if self.closed:
            raise RuntimeError("connection is closed")


class RecordingPool:
    """A pool of one observable connection, without a server."""

    def __init__(self, size: int = 1) -> None:
        """Create the fixed capacity this case borrows from."""
        self.connections = [RecordingConnection() for _ in range(size)]
        self.free = list(self.connections)
        self.held: set[RecordingConnection] = set()
        self.closed = False

    async def acquire(self, *, timeout: float | None = None) -> RecordingConnection:
        """Hand out a free connection."""
        connection = self.free.pop()
        self.held.add(connection)
        return connection

    async def release(self, connection: RecordingConnection) -> None:
        """Take one borrowed connection back."""
        self.held.remove(connection)
        self.free.append(connection)

    async def close(self) -> None:
        """Close the pool after every borrower has returned."""
        assert not self.held
        for connection in self.connections:
            await connection.close()
        self.closed = True


class NotesResource(PostgresResource):
    """The notes domain's resource: a page through ``_fetch``, a count through ``_fetchval``."""

    async def list_notes(self, limit: int = 2, offset: int = 0) -> list[dict[str, Any]]:
        """Return one ordered, bounded page of notes as plain mappings."""
        rows = await self._fetch(
            "SELECT id, text FROM notes ORDER BY id LIMIT $1 OFFSET $2",
            (limit, offset),
        )
        return [dict(row) for row in rows]

    async def count_notes(self) -> int:
        """Return how many notes exist, with the helper's ``None`` answered as zero."""
        total = await self._fetchval("SELECT count(*) FROM notes")
        return 0 if total is None else int(total)


async def main() -> None:
    """Run this case and verify its observable result."""
    pool = RecordingPool()
    resource = NotesResource(pool=pool)
    await resource.open()
    connection = pool.connections[0]

    connection.rows = [{"id": "n1", "text": "first"}, {"id": "n2", "text": "second"}]
    print("page  :", await resource.list_notes(limit=2))

    connection.rows = []
    print("empty :", await resource.list_notes())

    connection.value = 2
    print("count :", await resource.count_notes())

    connection.value = None
    print("absent:", await resource.count_notes())

    await resource.close()
    await pool.close()
    try:
        await resource.list_notes()
    except HandleError as error:
        print("closed:", error)

    print("calls :", connection.calls)
    assert [call[1] for call in connection.calls[:2]] == [(2, 0), (2, 0)]
    print("borrowed:", len(pool.held))


if __name__ == "__main__":
    asyncio.run(main())
