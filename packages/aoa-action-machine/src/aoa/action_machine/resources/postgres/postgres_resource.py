# packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py
"""
Concrete PostgreSQL connection manager implementation.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``PostgresResource`` is a ``SqlResource`` implementation
backed by ``asyncpg``. It performs direct database operations: connect,
transaction control, and SQL execution.

One resource is one unit of work. It holds **at most one connection**, it takes
that connection in ``open()`` — from a pool it was given, or from the driver
when it was built with connection parameters — and it gives the connection back
in ``close()``. Two concurrent callers never share a connection, which is what
keeps their transactions apart.

Connection-state policy for child actions is enforced by
``WrapperSqlResource``; this class handles low-level DB interaction.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    machine/action
         |
         v
    PostgresResource
      | open()    -> pool.acquire(timeout=acquire_timeout) | asyncpg.connect(...)
      | begin()   -> "BEGIN"      (opens the transaction flag)
      | execute() -> SQL statement
      | commit()  -> "COMMIT" or rollback when rollup=True (closes the flag)
      | rollback()-> "ROLLBACK"   (closes the flag)
      | close()   -> pool.release(conn) | conn.close()
         |
         v
    PostgreSQL server

═══════════════════════════════════════════════════════════════════════════════
ROLLUP BEHAVIOR
═══════════════════════════════════════════════════════════════════════════════

With ``rollup=True``, ``commit()`` is intercepted before real commit:
it calls ``rollback()`` and returns immediately. This guarantees that no
``COMMIT`` command reaches the database during rollup runs.

═══════════════════════════════════════════════════════════════════════════════
CLOSING WITH A TRANSACTION OPEN (FAIL FAST)
═══════════════════════════════════════════════════════════════════════════════

``begin()`` opens a transaction and ``commit()`` / ``rollback()`` close it; the
resource tracks that with ``_in_transaction``. A ``close()`` that finds the
transaction still open does not lean on the driver's own rollback: it issues
``ROLLBACK`` itself, returns the connection to its pool or closes it, and then
raises ``TransactionLeftOpenError``.

The raise is the signal that the caller's code must commit or roll back before
closing — so it is the error the caller sees, on a clean run and on a failed run
alike, with the run's own error chained as its cause. Returning the connection
*before* raising is what keeps fail-fast from becoming a leak.

"""

from typing import Any

import asyncpg

from aoa.action_machine.exceptions.connection_validation_error import ConnectionValidationError
from aoa.action_machine.exceptions.handle_error import HandleError
from aoa.action_machine.exceptions.transaction_left_open_error import TransactionLeftOpenError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.sql import SqlResource
from aoa.action_machine.resources.sql.pool_protocol import PoolProtocol


@exclude_graph_model
class PostgresResource(SqlResource):
    """
    AI-CORE-BEGIN
        ROLE: Concrete SQL manager for Postgres runtime operations.
        CONTRACT: Built from connection parameters or from a pool — exactly one; open/begin/execute/commit/rollback/close over asyncpg.
        INVARIANTS: Holds at most one connection, only for its own unit of work; never closes the pool; commit uses rollback when rollup=True; closing with a transaction open rolls it back, returns the connection, then raises ``TransactionLeftOpenError``.
        AI-CORE-END
    """

    acquire_timeout: float | None = 30.0
    """Wait bound for a connection from the pool; stated here, applied at ``acquire``."""

    def __init__(
        self,
        connection_params: dict[str, Any] | None = None,
        *,
        pool: PoolProtocol | None = None,
        rollup: bool = False,
    ) -> None:
        """
        Initialize PostgreSQL connection manager from exactly one of two forms.

        Args:
            connection_params: parameters passed to ``asyncpg.connect()``; ``None`` when a pool is given.
            pool: a ready pool to borrow one connection from; ``None`` when the resource opens its own.
            rollup: when True, ``commit()`` performs rollback instead.

        Raises:
            ConnectionValidationError: if both forms, or neither, are given.
        """
        super().__init__(rollup=rollup)
        if (connection_params is None) == (pool is None):
            raise ConnectionValidationError(
                "PostgresResource needs exactly one of connection_params and pool; "
                f"got connection_params={connection_params!r}, pool={pool!r}."
            )
        self._connection_params: dict[str, Any] | None = connection_params
        self._pool: PoolProtocol | None = pool
        self._conn: asyncpg.Connection[asyncpg.Record] | None = None
        self._in_transaction: bool = False

    async def open(self) -> None:
        """
        Take this unit of work's connection — from the pool, or from the driver.

        Idempotent: a resource that already holds a connection keeps it.

        Raises:
            HandleError: if the connection cannot be taken.
        """
        if self._conn is not None:
            return
        try:
            if self._pool is not None:
                self._conn = await self._pool.acquire(timeout=self.acquire_timeout)
            else:
                self._conn = await asyncpg.connect(**(self._connection_params or {}))
        except Exception as e:
            raise HandleError(f"PostgreSQL connection error: {e}") from e

    async def begin(self) -> None:
        """
        Begin transaction using SQL ``BEGIN``.

        Raises:
            HandleError: if connection is closed or BEGIN fails.
        """
        if self._conn is None:
            raise HandleError("Connection is not open")
        try:
            await self._conn.execute("BEGIN")
        except Exception as e:
            raise HandleError(f"BEGIN failed: {e}") from e
        self._in_transaction = True

    async def commit(self) -> None:
        """
        Commit transaction or rollback when ``rollup=True``.

        Raises:
            HandleError: if connection is closed or COMMIT fails.
        """
        # Rollup interception: use rollback and skip real COMMIT.
        if self.rollup:
            await self.rollback()
            return

        # rollup=False -> execute real COMMIT
        if self._conn is None:
            raise HandleError("Connection is not open")
        try:
            await self._conn.execute("COMMIT")
        except Exception as e:
            raise HandleError(f"COMMIT failed: {e}") from e
        self._in_transaction = False

    async def rollback(self) -> None:
        """
        Roll back transaction with SQL ``ROLLBACK``.

        Raises:
            HandleError: if connection is closed or ROLLBACK fails.
        """
        if self._conn is None:
            raise HandleError("Connection is not open")
        try:
            await self._conn.execute("ROLLBACK")
        except Exception as e:
            raise HandleError(f"ROLLBACK failed: {e}") from e
        self._in_transaction = False

    async def close(self) -> None:
        """
        Give this unit of work's connection back — to the pool, or closed when it is its own.

        Harmless when no connection is held, so a second close is silent and never
        returns the same connection twice.

        Raises:
            HandleError: if the rollback it issues, or the release, fails.
            TransactionLeftOpenError: if a transaction was still open — after the
                rollback and after the connection is back, never before.
        """
        if self._conn is None:
            return
        conn, self._conn = self._conn, None
        leaked, self._in_transaction = self._in_transaction, False
        try:
            if leaked:
                try:
                    await conn.execute("ROLLBACK")
                except Exception as e:
                    raise HandleError(f"ROLLBACK on close failed: {e}") from e
        finally:
            if self._pool is not None:
                await self._pool.release(conn)
            else:
                await conn.close()
        if leaked:
            raise TransactionLeftOpenError(
                "The resource was closed with a transaction still open: it has been rolled back "
                "and the connection returned. Commit or roll back before closing — the code that "
                "opened the transaction owns ending it."
            )

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """
        Execute SQL query via asyncpg.

        Args:
            query: SQL statement string.
            params: optional positional query params.

        Returns:
            Raw asyncpg execution result.

        Raises:
            HandleError: if connection is closed or SQL execution fails.
        """
        if self._conn is None:
            raise HandleError("Connection is not open")
        try:
            return await self._conn.execute(query, *params if params else ())
        except Exception as e:
            raise HandleError(f"SQL execution failed: {e}") from e
