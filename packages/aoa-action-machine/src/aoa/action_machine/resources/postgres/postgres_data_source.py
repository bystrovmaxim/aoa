# packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_data_source.py
"""
PostgresDataSource — one PostgreSQL database shared by several resources, with its pool.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The kind of data source a ``PostgresResource`` works through. It keeps what the
resources of one database share: the connection parameters and the pool. A resource
that names it takes one connection from it in ``open()`` and gives it back in
``close()``; the transaction stays the resource's own.

An application derives its own data source from this kind and creates it once, in its
lifespan; it then passes the instance to every resource that names it::

    @meta(description="Main shop database")
    class ShopDataSource(PostgresDataSource): ...

    async with ShopDataSource("postgresql://…", min_size=1, max_size=10) as shop:
        OrdersResource(data_source=shop)

═══════════════════════════════════════════════════════════════════════════════
THE POOL
═══════════════════════════════════════════════════════════════════════════════

Given connection parameters, the data source creates the pool in ``open()``
(``asyncpg.create_pool``) and closes it in ``close()``. Given a ready ``pool=`` — one
the application made itself, or a test's fake — it uses that pool and leaves closing it
to whoever made it. ``acquire_timeout`` bounds the wait for a free connection; the
driver's ``create_pool`` has no such bound, so it is stated here and applied at
``acquire``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    application lifespan ── open() ──► pool (created, or given)
                                         ▲            │
                    release(conn) ───────┘            └── acquire() ──► PostgresResource.open()
"""

from __future__ import annotations

from typing import Any

import asyncpg

from aoa.action_machine.exceptions.connection_validation_error import ConnectionValidationError
from aoa.action_machine.exceptions.handle_error import HandleError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_data_source import BaseDataSource
from aoa.action_machine.resources.sql.pool_protocol import PoolProtocol


@exclude_graph_model
class PostgresDataSource(BaseDataSource):
    """
    AI-CORE-BEGIN
    ROLE: The kind of data source of a PostgreSQL database: connection parameters and the pool.
    CONTRACT: Built from a DSN with pool options, or from a ready pool — exactly one; ``open``/``close`` and ``async with``; ``acquire()`` waits at most ``acquire_timeout``; ``release(connection)`` gives a connection back.
    INVARIANTS: Closes only a pool it created; hands out connections only while open; holds no transaction.
    AI-CORE-END
    """

    acquire_timeout: float | None = 30.0
    """Wait bound for a free connection; stated here, applied at ``acquire``."""

    def __init__(self, dsn: str | None = None, *, pool: PoolProtocol | None = None, **pool_options: Any) -> None:
        """
        Keep the connection parameters, or a ready pool.

        Args:
            dsn: the database address passed to ``asyncpg.create_pool``; ``None`` when a pool is given.
            pool: a ready pool to hand connections from; ``None`` when the data source creates its own.
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

        Idempotent: an open data source stays as it is.

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
        """Close the pool this data source created; a given pool is left to whoever made it."""
        if self._pool is not None and self._owns_pool:
            pool, self._pool, self._owns_pool = self._pool, None, False
            await pool.close()

    async def __aenter__(self) -> PostgresDataSource:
        """Open, and give the data source to the ``async with`` block."""
        await self.open()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close, whatever the block raised."""
        await self.close()

    async def acquire(self) -> Any:
        """
        Wait at most ``acquire_timeout`` for a free connection and return it.

        Raises:
            HandleError: if the data source is not open.
        """
        if self._pool is None:
            raise HandleError(f"{type(self).__name__} is not open: open it, or use it in async with, before a resource opens.")
        return await self._pool.acquire(timeout=self.acquire_timeout)

    async def release(self, connection: Any) -> None:
        """Give a connection back to the pool."""
        if self._pool is None:
            raise HandleError(f"{type(self).__name__} is not open: a connection cannot be given back.")
        await self._pool.release(connection)
