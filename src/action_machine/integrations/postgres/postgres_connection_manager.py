# src/action_machine/integrations/postgres/postgres_connection_manager.py
"""
Concrete PostgreSQL connection manager implementation.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``PostgresConnectionManager`` is a ``SqlManager`` implementation
backed by ``asyncpg``. It performs direct database operations: connect,
transaction control, and SQL execution.

Connection-state policy for child actions is enforced by
``WrapperSqlManager``; this class handles low-level DB interaction.

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

"""

from typing import Any

import asyncpg

from action_machine.exceptions import HandleError
from action_machine.resources.sql import SqlManager


class PostgresConnectionManager(SqlManager):
    """
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
