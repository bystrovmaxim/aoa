# packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_pool.py
"""
PostgresPool — the connection source a PostgreSQL resource is given.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The pool a ``PostgresStorage`` works through. It keeps the connection parameters
and the pool: given a DSN it creates the pool in ``open()``, and given a ready
pool it hands connections from that pool while leaving the closing to whoever
made it. ``acquire_timeout`` bounds the wait for a free connection; the driver's
``create_pool`` has no such bound, so it is stated here and applied at
``acquire``.

This is a plain class, assembled by the application and handed to a resource. It
has no ``@meta``, no resource kind and no graph node: the pool is not part of the
model. A service opens one pool in its lifespan and passes it to every resource
of that database::

    async with PostgresPool("postgresql://…", min_size=1, max_size=10) as shop:
        OrdersStorage(pool=shop)

═══════════════════════════════════════════════════════════════════════════════
THE POOL
═══════════════════════════════════════════════════════════════════════════════

Given connection parameters, the pool creates the pool in ``open()``
(``asyncpg.create_pool``) and closes it in ``close()``. Given a ready ``pool=`` —
one the application made itself, or a test's fake — it uses that pool and leaves
closing it to whoever made it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    application lifespan ── open() ──► pool (created, or given)
                                         ▲            │
                    release(conn) ───────┘            └── acquire() ──► PostgresStorage.open()
"""

from __future__ import annotations

from typing import Any

import asyncpg

from aoa.action_machine.exceptions.connection_validation_error import ConnectionValidationError
from aoa.action_machine.exceptions.handle_error import HandleError
from aoa.action_machine.resources.sql.pool_protocol import PoolProtocol


class PostgresPool:
    """
    AI-CORE-BEGIN
    ROLE: A PostgreSQL connection source: connection parameters and the pool.
    CONTRACT: Built from a DSN with pool options, or from a ready pool — exactly one; ``open``/``close`` and ``async with``; ``acquire()`` waits at most ``acquire_timeout``; ``release(connection)`` gives a connection back.
    INVARIANTS: Closes only a pool it created; hands out connections only while open; holds no transaction; never enters the model or the graph.
    AI-CORE-END
    """

    acquire_timeout: float | None = 30.0
    """Wait bound for a free connection; stated here, applied at ``acquire``."""

    def __init__(self, dsn: str | None = None, *, pool: PoolProtocol | None = None, **pool_options: Any) -> None:
        """
        Keep the connection parameters, or a ready pool.

        Args:
            dsn: the database address passed to ``asyncpg.create_pool``; ``None`` when a pool is given.
            pool: a ready pool to hand connections from; ``None`` when the pool is created here.
            **pool_options: further arguments of ``asyncpg.create_pool`` (``min_size``, ``max_size``, …).

        Raises:
            ConnectionValidationError: if both a DSN and a pool are given, or neither, or pool options come with a pool.
        """
        if (dsn is None) == (pool is None):
            raise ConnectionValidationError(f"{type(self).__name__} needs exactly one of dsn and pool; got dsn={dsn!r}, pool={pool!r}.")
        if pool is not None and pool_options:
            raise ConnectionValidationError(f"{type(self).__name__}: pool options {sorted(pool_options)} apply only to a pool it creates.")
        self._dsn = dsn
        self._pool_options = pool_options
        self._pool: PoolProtocol | None = pool
        self._owns_pool = False

    async def open(self) -> None:
        """
        Create the pool from the connection parameters; a given pool is used as it is.

        Idempotent: an open pool stays as it is.

        Raises:
            HandleError: if the pool cannot be created.
        """
        if self._pool is not None:
            return
        try:
            self._pool = await asyncpg.create_pool(self._dsn, **self._pool_options)
        except Exception as e:
            raise HandleError(f"PostgreSQL pool creation failed: {e}") from e
        self._owns_pool = True

    async def close(self) -> None:
        """Close the pool this pool created; a given pool is left to whoever made it."""
        if self._pool is not None and self._owns_pool:
            pool, self._pool, self._owns_pool = self._pool, None, False
            await pool.close()

    async def __aenter__(self) -> PostgresPool:
        """Open, and give the pool to the ``async with`` block."""
        await self.open()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close, whatever the block raised."""
        await self.close()

    async def acquire(self) -> Any:
        """
        Wait at most ``acquire_timeout`` for a free connection and return it.

        Raises:
            HandleError: if the pool is not open.
        """
        if self._pool is None:
            raise HandleError(f"{type(self).__name__} is not open: open it, or use it in async with, before a resource opens.")
        return await self._pool.acquire(timeout=self.acquire_timeout)

    async def release(self, connection: Any) -> None:
        """Give a connection back to the pool."""
        if self._pool is None:
            raise HandleError(f"{type(self).__name__} is not open: a connection cannot be given back.")
        await self._pool.release(connection)
