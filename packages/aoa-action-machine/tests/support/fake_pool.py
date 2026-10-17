# tests/support/fake_pool.py
"""
FakePool — the connection harness the resource lifecycle tests run against.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

No test in this feature may need a database, and the defect under test appears
only under concurrency. This module supplies both halves of that instrument:

* ``FakeConnection`` — one connection that performs **one operation at a time**,
  the rule the real driver enforces with ``InterfaceError``. It answers both a
  statement (``execute``) and a row read (``fetchrow``), and it records the
  statement **and the positional parameters** of every call, so a test of a
  driver helper can assert that parameters were forwarded rather than dropped;
* ``FakePool`` — a pool with stated bounds that records its high-water mark, so
  a test can assert that the ceiling was never exceeded and that no borrowed
  connection was left behind.

Both are faithful to the driver where it matters and silent where it does not:
``acquire`` returns a proxy that is both awaitable and an async context manager,
``release`` and ``close`` are coroutines, and ``acquire(timeout=None)`` waits
forever exactly as the driver does — the resource passes its own stated bound.
Nothing here imports the driver, so the suite runs with the ``postgres`` extra
absent.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    FakePool.acquire(timeout=…)  ──>  FakeConnection   (awaitable / async CM)
          │                                  │
          │  at max_size: waits, then times out
          v                                  v
    FakePool.release(conn)       <──  the resource's ``close()``

    high_water — the most connections held at once, for the ceiling assertion
    held       — connections still borrowed, for the leak assertion

"""

from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any

__all__ = [
    "FakeConnection",
    "FakePool",
    "FakeReleaseError",
    "InterfaceError",
    "PoolAcquireTimeoutError",
]


class InterfaceError(RuntimeError):
    """Raised when one connection is asked to perform two operations at once."""


class FakeReleaseError(RuntimeError):
    """Raised when a connection is released twice, released foreign to a pool, or a pool closes while it is held."""


class PoolAcquireTimeoutError(TimeoutError):
    """Raised when no connection frees within the stated wait bound."""


class FakeConnection:
    """A connection that performs one operation at a time, like the driver's own."""

    def __init__(self, row: Any = None) -> None:
        self._busy = False
        self.closed = False
        self.operations: list[str] = []
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.row: Any = row

    @property
    def busy(self) -> bool:
        """Whether an operation is in flight on this connection."""
        return self._busy

    async def execute(self, query: str, *args: Any) -> str:
        """Run one statement, refusing a second operation while one is in flight."""
        await self._operate(query, args)
        return "OK"

    async def fetchrow(self, query: str, *args: Any) -> Any:
        """Answer with the row this connection holds, recording what it was asked for."""
        await self._operate(query, args)
        return self.row

    async def close(self) -> None:
        """Mark this connection closed."""
        self.closed = True

    async def _operate(self, query: str, args: tuple[Any, ...]) -> None:
        """Hold the connection for one operation, refusing a second one at the same time."""
        if self.closed:
            raise InterfaceError("connection is closed")
        if self._busy:
            raise InterfaceError("another operation is in progress")
        self._busy = True
        try:
            # Yield once while holding the connection, so a concurrent caller
            # reaches the guard above rather than queueing silently.
            await asyncio.sleep(0)
            self.operations.append(query)
            self.calls.append((query, args))
        finally:
            self._busy = False


class _Acquire:
    """What ``FakePool.acquire`` returns: awaitable, and usable as a context manager."""

    def __init__(self, pool: FakePool, timeout: float | None) -> None:
        self._pool = pool
        self._timeout = timeout
        self._conn: FakeConnection | None = None

    async def _take(self) -> FakeConnection:
        if self._conn is None:
            self._conn = await self._pool._acquire(self._timeout)
        return self._conn

    def __await__(self) -> Any:
        return self._take().__await__()

    async def __aenter__(self) -> FakeConnection:
        return await self._take()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._conn is not None:
            await self._pool.release(self._conn)
            self._conn = None


class FakePool:
    """A pool with stated bounds, a stated wait bound, and a high-water mark."""

    def __init__(
        self,
        *,
        min_size: int = 0,
        max_size: int = 10,
        timeout: float | None = 30.0,
    ) -> None:
        if min_size < 0:
            raise ValueError("min_size must be zero or greater")
        if max_size <= 0:
            raise ValueError("max_size must be greater than zero")
        if min_size > max_size:
            raise ValueError("min_size must not exceed max_size")
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.created = 0
        self.high_water = 0
        self.closed = False
        self._free: list[FakeConnection] = []
        self._held: set[FakeConnection] = set()
        self._all: list[FakeConnection] = []
        self._cond = asyncio.Condition()
        for _ in range(min_size):
            self._free.append(FakeConnection())
            self._all.append(self._free[-1])
            self.created += 1

    @property
    def held(self) -> int:
        """How many connections are currently borrowed."""
        return len(self._held)

    @property
    def free(self) -> int:
        """How many connections are currently idle in the pool."""
        return len(self._free)

    @property
    def borrowed(self) -> frozenset[FakeConnection]:
        """The connections currently borrowed, for assertions about who holds what."""
        return frozenset(self._held)

    @property
    def connections(self) -> tuple[FakeConnection, ...]:
        """Every connection this pool has created, for assertions about what ran where."""
        return tuple(self._all)

    def acquire(self, *, timeout: float | None = None) -> Any:
        """Return an awaitable proxy that yields a connection, waiting up to ``timeout``."""
        return _Acquire(self, timeout)

    async def _acquire(self, timeout: float | None) -> FakeConnection:
        loop = asyncio.get_running_loop()
        deadline = None if timeout is None else loop.time() + timeout
        while True:
            async with self._cond:
                if self.closed:
                    raise InterfaceError("pool is closing")
                if self._free:
                    conn = self._free.pop()
                elif self.created < self.max_size:
                    conn = FakeConnection()
                    self._all.append(conn)
                    self.created += 1
                else:
                    conn = None
                if conn is not None:
                    self._held.add(conn)
                    self.high_water = max(self.high_water, len(self._held))
                    return conn
                remaining = None if deadline is None else deadline - loop.time()
                if remaining is not None and remaining <= 0:
                    raise PoolAcquireTimeoutError(self._timeout_message(timeout))
                try:
                    await asyncio.wait_for(self._cond.wait(), remaining)
                except TimeoutError as exc:
                    raise PoolAcquireTimeoutError(self._timeout_message(timeout)) from exc

    async def release(self, conn: object) -> None:
        """Return a borrowed connection; a double release, or a foreign one, is refused."""
        if not isinstance(conn, FakeConnection):
            raise FakeReleaseError("connection did not come from this pool")
        async with self._cond:
            if conn in self._free:
                raise FakeReleaseError("connection was already released to this pool")
            if conn not in self._held:
                raise FakeReleaseError("connection is not borrowed from this pool")
            self._held.discard(conn)
            self._free.append(conn)
            self._cond.notify_all()

    async def close(self) -> None:
        """Close the pool; refused while a connection is still borrowed."""
        async with self._cond:
            if self._held:
                raise FakeReleaseError(
                    f"cannot close the pool: {len(self._held)} connection(s) still borrowed"
                )
            for conn in self._free:
                conn.closed = True
            self._free.clear()
            self.closed = True
            self._cond.notify_all()

    def _timeout_message(self, timeout: float | None) -> str:
        """Describe a wait that exceeded its stated bound."""
        return f"no connection within {timeout}s (max_size={self.max_size})"
