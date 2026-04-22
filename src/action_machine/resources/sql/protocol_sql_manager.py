# src/action_machine/resources/sql/protocol_sql_manager.py
# pylint: disable=unnecessary-ellipsis  # Protocol member bodies use ellipsis per PEP 544 stubs.
"""
ProtocolSqlManager — structural contract for transactional SQL access.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Defines the surface required for lifecycle + execution against a SQL-backed
resource: ``rollup`` visibility, ``open`` / transaction boundaries, and
``execute``. Implementations may be concrete drivers (for example Postgres) or
thin proxies; static checking uses this protocol without importing those types.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ProtocolSqlManager (typing.Protocol)
              │
              △ structural match
              │
    SqlManager / wrappers / integrations

"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolSqlManager(Protocol):
    """
AI-CORE-BEGIN
    ROLE: Typed contract for async SQL connection lifecycle and execution.
    CONTRACT: Implementations expose rollup, open/begin/commit/rollback, execute.
    INVARIANTS: Structural subtyping only; no runtime enforcement beyond isinstance.
AI-CORE-END
"""

    @property
    def rollup(self) -> bool:
        """Whether rollup (commit-as-rollback) mode is active for this manager."""
        ...

    def check_rollup_support(self) -> bool:
        """Same contract as ``BaseResourceManager.check_rollup_support`` for SQL managers."""
        ...

    async def open(self) -> None:
        """Establish the underlying connection when applicable."""
        ...

    async def begin(self) -> None:
        """Start a transaction scope."""
        ...

    async def commit(self) -> None:
        """Commit the active transaction."""
        ...

    async def rollback(self) -> None:
        """Roll back the active transaction."""
        ...

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """Run a SQL statement with optional positional parameters."""
        ...
