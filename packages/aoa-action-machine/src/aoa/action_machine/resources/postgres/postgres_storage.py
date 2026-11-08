# packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_storage.py
"""
Concrete PostgreSQL connection manager implementation.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``PostgresStorage`` is a ``SqlStorage`` implementation
backed by ``asyncpg``. It performs direct database operations: connect,
transaction control, and SQL execution.

One resource is one unit of work. It holds **at most one connection** for that
unit: it takes the connection in ``open()`` and gives it back in ``close()``.
How it obtains that connection is the application's choice, made at assembly:
with ``pool=`` it takes one from a ``PostgresPool``; with ``connection_params=``
it opens its own connection with ``asyncpg.connect`` and closes it. Exactly one
of the two is given, and the resource class is the same either way.

Two concurrent callers never share a connection, which is what
keeps their transactions apart.

Connection-state policy for child actions is enforced by
``SqlStorageWrapper``; this class handles low-level DB interaction.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    machine/action
         |
         v
    PostgresStorage
      | open()    -> pool.acquire() | asyncpg.connect(...)
      | begin()   -> "BEGIN"      (opens the transaction flag)
      | _execute() -> a statement, for a subclass
      | _fetchrow()-> the first row, for a subclass
      | _fetch()   -> every row, for a subclass
      | _fetchval()-> one value, for a subclass
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
``ROLLBACK`` itself, returns the connection to its pool (or closes it when it is
the resource's own), and then raises ``TransactionLeftOpenError``.

The raise is the signal that the caller's code must commit or roll back before
closing — so it is the error the caller sees, on a clean run and on a failed run
alike, with the run's own error chained as its cause. Returning the connection
*before* raising is what keeps fail-fast from becoming a leak.

"""

from __future__ import annotations

from typing import Any

import asyncpg

from aoa.action_machine.exceptions.connection_validation_error import ConnectionValidationError
from aoa.action_machine.exceptions.handle_error import HandleError
from aoa.action_machine.exceptions.transaction_left_open_error import TransactionLeftOpenError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.postgres.postgres_pool import PostgresPool
from aoa.action_machine.resources.sql import SqlStorage


@exclude_graph_model
class PostgresStorage(SqlStorage):
    """
    AI-CORE-BEGIN
        ROLE: Concrete SQL manager for Postgres runtime operations.
        CONTRACT: Built from exactly one of a pool and connection parameters; open/begin/commit/rollback/close over asyncpg, and its subclasses run statements and reads through the protected ``_execute``, ``_fetchrow``, ``_fetch`` and ``_fetchval`` — one per driver answer.
        INVARIANTS: Holds at most one connection, only for its own unit of work; never closes the pool it borrows from; commit uses rollback when rollup=True; closing with a transaction open rolls it back, returns the connection, then raises ``TransactionLeftOpenError``.
        AI-CORE-END
    """

    def __init__(
        self,
        *,
        pool: PostgresPool | None = None,
        connection_params: dict[str, Any] | str | None = None,
        rollup: bool = False,
    ) -> None:
        """
        Initialize PostgreSQL connection manager from exactly one connection choice.

        Args:
            pool: the pool this resource takes a connection from; ``None`` when it opens its own.
            connection_params: arguments of ``asyncpg.connect`` — a mapping of keyword arguments,
                or a DSN string; ``None`` when the resource works through a pool.
            rollup: when True, ``commit()`` performs rollback instead.

        Raises:
            ConnectionValidationError: if both ``pool`` and ``connection_params`` are given, or neither.
        """
        super().__init__(rollup=rollup)
        if (pool is None) == (connection_params is None):
            raise ConnectionValidationError(
                f"{type(self).__name__} needs exactly one of pool and connection_params; "
                f"got pool={pool!r}, connection_params={connection_params!r}."
            )
        self._pool: PostgresPool | None = pool
        self._connection_params: dict[str, Any] | str | None = connection_params
        self._conn: asyncpg.Connection[asyncpg.Record] | None = None
        self._in_transaction: bool = False

    async def open(self) -> None:
        """
        Take this unit of work's connection: from the pool, or from the driver.

        Idempotent: a resource that already holds a connection keeps it.

        Raises:
            HandleError: if the connection cannot be taken.
        """
        if self._conn is not None:
            return
        try:
            self._conn = await self._acquire_connection()
        except Exception as e:
            raise HandleError(f"PostgreSQL connection error: {e}") from e

    async def _acquire_connection(self) -> asyncpg.Connection[asyncpg.Record]:
        """Take one connection from the pool, or open the resource's own and keep it for the unit."""
        if self._pool is not None:
            connection: asyncpg.Connection[asyncpg.Record] = await self._pool.acquire()
            return connection
        params = self._connection_params
        if isinstance(params, str):
            return await asyncpg.connect(params)
        return await asyncpg.connect(**(params or {}))

    async def begin(self) -> None:
        """
        Begin transaction using SQL ``BEGIN``.

        Raises:
            HandleError: if connection is closed or BEGIN fails.
        """
        conn = self._require_connection()
        try:
            await conn.execute("BEGIN")
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
        conn = self._require_connection()
        try:
            await conn.execute("COMMIT")
        except Exception as e:
            raise HandleError(f"COMMIT failed: {e}") from e
        self._in_transaction = False

    async def rollback(self) -> None:
        """
        Roll back transaction with SQL ``ROLLBACK``.

        Raises:
            HandleError: if connection is closed or ROLLBACK fails.
        """
        conn = self._require_connection()
        try:
            await conn.execute("ROLLBACK")
        except Exception as e:
            raise HandleError(f"ROLLBACK failed: {e}") from e
        self._in_transaction = False

    async def close(self) -> None:
        """
        Give this unit of work's connection back: to the pool, or closed when it is the resource's own.

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

    def _require_connection(self) -> asyncpg.Connection[asyncpg.Record]:
        """Return the connection this unit of work holds, or refuse with a clear error."""
        if self._conn is None:
            raise HandleError("Connection is not open")
        return self._conn

    async def _execute(self, query: str, params: tuple[Any, ...] | None = None) -> str:
        """
        Run a statement for a subclass and return its status.

        Args:
            query: SQL statement string.
            params: optional positional query params.

        Returns:
            The driver's command status, such as ``"INSERT 0 1"``. Rows are discarded;
            a subclass that reads rows uses ``_fetch`` for all of them or ``_fetchrow``
            for the first.

        Raises:
            HandleError: if connection is closed or SQL execution fails.
        """
        conn = self._require_connection()
        try:
            # The driver's stubs are absent, so its return is ``Any``; ``execute`` answers a status string.
            status: str = await conn.execute(query, *params if params else ())
            return status
        except Exception as e:
            raise HandleError(f"SQL execution failed: {e}") from e

    async def _fetchrow(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """
        Run a query for a subclass and return its first row.

        Answers the **first** row, not the only one: a statement that can match
        several rows without an ordering yields an arbitrary one, silently.

        Args:
            query: SQL query string.
            params: optional positional query params.

        Returns:
            The first row, or ``None`` when the query matched nothing.

        Raises:
            HandleError: if the connection is not open or the query fails.
        """
        conn = self._require_connection()
        try:
            row: Any = await conn.fetchrow(query, *params if params else ())
            return row
        except Exception as e:
            raise HandleError(f"SQL execution failed: {e}") from e

    async def _fetch(self, query: str, params: tuple[Any, ...] | None = None) -> list[Any]:
        """
        Run a query for a subclass and return all its rows.

        Answers every row the driver returned, in the driver's order: it neither
        sorts nor truncates. A single row arrives as a list of one.

        Args:
            query: SQL query string.
            params: optional positional query params.

        Returns:
            Every row, or ``[]`` when the query matched nothing.

        Raises:
            HandleError: if the connection is not open or the query fails.
        """
        conn = self._require_connection()
        try:
            rows: list[Any] = await conn.fetch(query, *params if params else ())
            return rows
        except Exception as e:
            raise HandleError(f"SQL execution failed: {e}") from e

    async def _fetchval(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """
        Run a query for a subclass and return the first value of its first row.

        Answers the **first** row's value, not one value per row: a statement
        that can match several rows without an ordering yields an arbitrary
        one, silently. No match answers ``None``, which is also what a matched
        row whose first value is SQL ``NULL`` gives — this helper cannot tell
        the two apart, so a caller that must know asks ``_fetchrow`` for the row.

        Args:
            query: SQL query string.
            params: optional positional query params.

        Returns:
            The first value of the first row, or ``None`` when the query matched
            nothing or that value is ``NULL``.

        Raises:
            HandleError: if the connection is not open or the query fails.
        """
        conn = self._require_connection()
        try:
            value: Any = await conn.fetchval(query, *params if params else ())
            return value
        except Exception as e:
            raise HandleError(f"SQL execution failed: {e}") from e
