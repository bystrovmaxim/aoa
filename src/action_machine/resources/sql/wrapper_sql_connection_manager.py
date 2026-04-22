# src/action_machine/resources/sql/wrapper_sql_connection_manager.py
"""
Proxy wrapper that forbids transaction control in nested scopes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``WrapperSqlConnectionManager`` wraps a real ``SqlConnectionManager``.
It is created automatically when connections are propagated to child actions
via ``ToolsBox.run()``. The wrapper forbids lifecycle operations
(``open``, ``begin``, ``commit``, ``rollback``) for nested actions, but allows
query execution via ``execute``.

This guarantees transaction ownership remains at root action level. Child
actions operate inside the same transaction without the ability to commit or
rollback it directly.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP PROPAGATION
═══════════════════════════════════════════════════════════════════════════════

``WrapperSqlConnectionManager`` preserves rollup flag from original manager.
This provides end-to-end rollup mode propagation across nested action chains:

    Root action (rollup=True)
        │
        ├── connections["db"] = PostgresConnectionManager(rollup=True)
        │
        └── box.run(ChildAction, params, connections)
                │
                └── connections["db"] = WrapperSqlConnectionManager(original)
                        _rollup = original._rollup (True)
                        │
                        └── box.run(GrandChildAction, params, connections)
                                │
                                └── connections["db"] = WrapperSqlConnectionManager(wrapper)
                                        _rollup = wrapper._rollup (True)

At each nesting level, wrapper inherits rollup from previous level. If the
root manager was created with ``rollup=True``, all wrappers also expose
``rollup=True``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    SqlConnectionManager (ABC)
        │
        ├── PostgresConnectionManager       <- real manager
        │       open()   -> DB connection
        │       begin()  -> BEGIN
        │       commit() -> COMMIT (or ROLLBACK in rollup)
        │       execute()-> SQL query
        │
        └── WrapperSqlConnectionManager     <- proxy
                open/begin/commit/rollback -> TransactionProhibitedError
                execute() -> delegates to real manager
                _rollup   -> inherited from original

"""

from typing import Any

from action_machine.model.exceptions import HandleError, TransactionProhibitedError
from action_machine.resources.sql.sql_connection_manager import (
    SqlConnectionManager,
)


class WrapperSqlConnectionManager(SqlConnectionManager):
    """
    SQL manager proxy for nested actions.

    Forbids transaction lifecycle operations and delegates query execution to
    the original manager while preserving rollup mode.
    """

    def __init__(self, connection_manager: SqlConnectionManager) -> None:
        """Initialize proxy and inherit rollup flag from original manager."""
        super().__init__(rollup=connection_manager.rollup)
        self._connection_manager = connection_manager

    async def open(self) -> None:
        """Forbid opening connection from nested action scope."""
        raise TransactionProhibitedError(
            "Opening connection is allowed only in the action that created the resource. "
            "Current action received a proxy connection, so open is unavailable."
        )

    async def begin(self) -> None:
        """Forbid starting transaction from nested action scope."""
        raise TransactionProhibitedError(
            "Transaction control is allowed only for connection owner action. "
            "Current action received a proxy connection, so begin is unavailable."
        )

    async def commit(self) -> None:
        """Forbid commit from nested action scope."""
        raise TransactionProhibitedError(
            "Transaction commit is allowed only in the action that created the resource. "
            "Current action received a proxy connection, so commit is unavailable."
        )

    async def rollback(self) -> None:
        """Forbid rollback from nested action scope."""
        raise TransactionProhibitedError(
            "Transaction rollback is allowed only in the action that created the resource. "
            "Current action received a proxy connection, so rollback is unavailable."
        )

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """Execute query by delegating to underlying manager."""
        try:
            return await self._connection_manager.execute(query, params)
        except Exception as e:
            raise HandleError(f"SQL execution error: {e}") from e

    def get_wrapper_class(self) -> type["SqlConnectionManager"] | None:
        """Return wrapper class for further nesting levels."""
        return WrapperSqlConnectionManager
