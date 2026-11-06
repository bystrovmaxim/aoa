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
that connection in ``open()`` — from its data source, or from the driver when it
was built with connection parameters — and it gives the connection back in
``close()``.

A resource works one of two ways, never both:

- **with its own connection**: ``PostgresResource(connection_params={...})`` opens a
  connection per unit of work and closes it; there is no pool, and the resource names
  no data source;
- **through a data source**: a resource that names one —
  ``class OrdersResource(PostgresResource[ShopDataSource])`` — is built with
  ``data_source=`` and takes a connection from that data source's pool.

Two concurrent callers never share a connection, which is what
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
      | open()    -> data_source.acquire() | asyncpg.connect(...)
      | begin()   -> "BEGIN"      (opens the transaction flag)
      | _execute() -> a statement, for a subclass
      | _fetchrow()-> the first row, for a subclass
      | _fetch()   -> every row, for a subclass
      | _fetchval()-> one value, for a subclass
      | commit()  -> "COMMIT" or rollback when rollup=True (closes the flag)
      | rollback()-> "ROLLBACK"   (closes the flag)
      | close()   -> data_source.release(conn) | conn.close()
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
``ROLLBACK`` itself, returns the connection to its data source or closes it, and then
raises ``TransactionLeftOpenError``.

The raise is the signal that the caller's code must commit or roll back before
closing — so it is the error the caller sees, on a clean run and on a failed run
alike, with the run's own error chained as its cause. Returning the connection
*before* raising is what keeps fail-fast from becoming a leak.

"""

from __future__ import annotations

from typing import Any

import asyncpg
from typing_extensions import TypeVar

from aoa.action_machine.exceptions.connection_validation_error import ConnectionValidationError
from aoa.action_machine.exceptions.handle_error import HandleError
from aoa.action_machine.exceptions.transaction_left_open_error import TransactionLeftOpenError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.postgres.postgres_data_source import PostgresDataSource
from aoa.action_machine.resources.sql import SqlResource

TPostgresDataSource_co = TypeVar("TPostgresDataSource_co", bound=PostgresDataSource, default=PostgresDataSource, covariant=True)
"""The PostgreSQL data source a resource names; one that names none leaves it at its default."""


@exclude_graph_model
class PostgresResource(SqlResource[TPostgresDataSource_co]):
    """
    AI-CORE-BEGIN
        ROLE: Concrete SQL manager for Postgres runtime operations.
        CONTRACT: Built from connection parameters or from the data source it names — exactly one; open/begin/commit/rollback/close over asyncpg, and its subclasses run statements and reads through the protected ``_execute``, ``_fetchrow``, ``_fetch`` and ``_fetchval`` — one per driver answer.
        INVARIANTS: Holds at most one connection, only for its own unit of work; never closes its data source's pool; commit uses rollback when rollup=True; closing with a transaction open rolls it back, returns the connection, then raises ``TransactionLeftOpenError``.
        AI-CORE-END
    """

    def __init__(
        self,
        connection_params: dict[str, Any] | None = None,
        *,
        data_source: PostgresDataSource | None = None,
        rollup: bool = False,
    ) -> None:
        """
        Initialize PostgreSQL connection manager from exactly one of two forms.

        Args:
            connection_params: parameters passed to ``asyncpg.connect()``; ``None`` when the resource works through a data source.
            data_source: the data source this resource names, to take connections from; ``None`` when it opens its own.
            rollup: when True, ``commit()`` performs rollback instead.

        Raises:
            ConnectionValidationError: if both forms, or neither, are given.
            DataSourceDeclarationError: if the resource names a data source and is not given an instance of it,
                or names none and is given one.
        """
        super().__init__(rollup=rollup)
        if (connection_params is None) == (data_source is None):
            raise ConnectionValidationError(
                f"{type(self).__name__} needs exactly one of connection_params and data_source; "
                f"got connection_params={connection_params!r}, data_source={data_source!r}."
            )
        self._check_data_source(data_source)
        self._connection_params: dict[str, Any] | None = connection_params
        self._data_source: PostgresDataSource | None = data_source
        self._conn: asyncpg.Connection[asyncpg.Record] | None = None
        self._in_transaction: bool = False

    async def open(self) -> None:
        """
        Take this unit of work's connection — from the data source, or from the driver.

        Idempotent: a resource that already holds a connection keeps it.

        Raises:
            HandleError: if the connection cannot be taken.
        """
        if self._conn is not None:
            return
        try:
            if self._data_source is not None:
                self._conn = await self._data_source.acquire()
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
        Give this unit of work's connection back — to the data source, or closed when it is its own.

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
            if self._data_source is not None:
                await self._data_source.release(conn)
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
