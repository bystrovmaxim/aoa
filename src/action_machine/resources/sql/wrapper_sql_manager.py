# src/action_machine/resources/sql/wrapper_sql_manager.py
"""
Proxy wrapper that forbids transaction control in nested scopes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``WrapperSqlManager`` wraps a manager that implements ``ProtocolSqlManager``.
It is created when connections are propagated to child actions via
``ToolsBox.run()``. The wrapper forbids lifecycle operations
(``open``, ``begin``, ``commit``, ``rollback``) for nested actions, but allows
query execution via ``execute``.

``rollup`` is not stored on the wrapper: reads delegate to the wrapped manager.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP PROPAGATION
═══════════════════════════════════════════════════════════════════════════════

Nested wrappers chain onto the same underlying owner; ``rollup`` seen through the
proxy always reflects the inner manager's value.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ProtocolSqlManager (real manager, e.g. Postgres)
        │
        └── WrapperSqlManager (BaseResourceManager + Protocol)
                open/begin/commit/rollback -> TransactionProhibitedError
                execute() -> delegates to inner
                rollup -> delegates to inner

"""

from typing import Any

from action_machine.exceptions import HandleError, TransactionProhibitedError
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.sql.protocol_sql_manager import ProtocolSqlManager


class WrapperSqlManager(BaseResourceManager, ProtocolSqlManager):
    """
    SQL manager proxy for nested actions.

    Forbids transaction lifecycle operations and delegates query execution and
    rollup visibility to the wrapped manager.
    """

    def __init__(self, connection_manager: ProtocolSqlManager) -> None:
        """Initialize proxy; rollup is always read from ``connection_manager``."""
        self._connection_manager = connection_manager

    @property
    def rollup(self) -> bool:
        """Delegate rollup to the wrapped connection owner."""
        return self._connection_manager.rollup

    def check_rollup_support(self) -> bool:
        """Delegate to the wrapped manager."""
        return self._connection_manager.check_rollup_support()

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

    def get_wrapper_class(self) -> type[BaseResourceManager] | None:
        """Return wrapper class for further nesting levels."""
        return WrapperSqlManager
