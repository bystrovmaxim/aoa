# src/action_machine/integrations/postgres/postgres_connection_manager.py
"""
Concrete PostgreSQL connection manager implementation.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``PostgresConnectionManager`` is a ``SqlConnectionManager`` implementation
backed by ``asyncpg``. It performs direct database operations: connect,
transaction control, and SQL execution.

Connection-state policy for child actions is enforced by
``WrapperSqlConnectionManager``; this class handles low-level DB interaction.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``rollup`` mode is inherited from ``SqlConnectionManager``.
- ``commit()`` checks ``self.rollup`` first; when true, it executes
  ``rollback()`` and never sends SQL ``COMMIT``.
- Transaction commands are explicit SQL statements:
  ``BEGIN``, ``COMMIT``, ``ROLLBACK``.
- Each operation requires an opened connection, otherwise ``HandleError``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    machine/action
         |
         v
    PostgresConnectionManager
      | open()    -> asyncpg.connect(...)
      | begin()   -> "BEGIN"
      | execute() -> SQL statement
      | commit()  -> "COMMIT" or rollback when rollup=True
      | rollback()-> "ROLLBACK"
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
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Production mode:
    db = PostgresConnectionManager(
        connection_params={"host": "localhost", "database": "orders"},
    )
    await db.open()
    await db.begin()
    await db.execute("INSERT INTO orders (id, amount) VALUES ($1, $2)", (1, 100.0))
    await db.commit()  # real COMMIT

    # Safe testing against production-like DB with rollup:
    db = PostgresConnectionManager(
        connection_params={"host": "localhost", "database": "orders"},
        rollup=True,
    )
    await db.open()
    await db.begin()
    await db.execute("INSERT INTO orders (id, amount) VALUES ($1, $2)", (1, 100.0))
    await db.commit()  # ROLLBACK (changes are not persisted)

    # Pass manager to action runtime:
    result = await machine.run(
        context=ctx,
        action=CreateOrderAction(),
        params=order_params,
        connections={"db": db},
    )

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``HandleError`` for connection, transaction, and SQL failures.
- Uses SQL transaction commands directly because asyncpg does not expose
  ``commit()``/``rollback()`` methods on connection as adapter API.

AI-CORE-BEGIN
ROLE: Production PostgreSQL SQL connection manager.
CONTRACT: Execute SQL and transaction lifecycle with optional rollup interception.
INVARIANTS: open connection required; rollup commit always resolves to rollback.
FLOW: open -> begin -> execute* -> commit/rollback.
FAILURES: Any asyncpg failure is wrapped into HandleError.
EXTENSION POINTS: Wrapper class for restricted child-action access.
AI-CORE-END
"""

from typing import Any

import asyncpg

from action_machine.model.exceptions import HandleError
from action_machine.resources.sql_connection_manager import SqlConnectionManager
from action_machine.resources.wrapper_sql_connection_manager import (
    WrapperSqlConnectionManager,
)


class PostgresConnectionManager(SqlConnectionManager):
    """
    Asyncpg-backed SQL connection manager for PostgreSQL.

    AI-CORE-BEGIN
    ROLE: Concrete SQL manager for Postgres runtime operations.
    CONTRACT: Implements open/begin/execute/commit/rollback over asyncpg.
    INVARIANTS: commit uses rollback when rollup=True.
    AI-CORE-END
    """

    def __init__(
        self,
        connection_params: dict[str, Any],
        rollup: bool = False,
    ) -> None:
        """
        Initialize PostgreSQL connection manager.

        Args:
            connection_params: parameters passed to ``asyncpg.connect()``.
            rollup: when True, ``commit()`` performs rollback instead.
        """
        super().__init__(rollup=rollup)
        self._connection_params = connection_params
        self._conn: asyncpg.Connection[asyncpg.Record] | None = None

    async def open(self) -> None:
        """
        Open PostgreSQL connection via ``asyncpg.connect()``.

        Raises:
            HandleError: if connection fails.
        """
        try:
            self._conn = await asyncpg.connect(**self._connection_params)
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

    def get_wrapper_class(self) -> type[SqlConnectionManager] | None:
        """
        Return wrapper class for child-action usage.

        ``WrapperSqlConnectionManager`` blocks transaction-control methods
        in child actions and allows query execution.

        Returns:
            WrapperSqlConnectionManager class.
        """
        return WrapperSqlConnectionManager
