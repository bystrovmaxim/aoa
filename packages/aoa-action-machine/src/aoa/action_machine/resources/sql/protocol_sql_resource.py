# packages/aoa-action-machine/src/aoa/action_machine/resources/sql/protocol_sql_resource.py
# pylint: disable=unnecessary-ellipsis  # Protocol member bodies use ellipsis per PEP 544 stubs.
"""
ProtocolSqlResource — structural contract for transactional SQL access.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Defines the surface required for lifecycle + execution against a SQL-backed
resource: ``rollup`` visibility, ``open`` / transaction boundaries, ``close``,
and ``execute``. Implementations may be concrete drivers (for example Postgres)
or thin proxies; static checking uses this protocol without importing those
types.

``close`` carries a concrete harmless body, so that a manager which holds no
connection of its own — the eight demo stubs, the test doubles — needs no edit
to satisfy the contract; only a manager that really holds a connection
overrides it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ProtocolSqlResource (typing.Protocol)
              │
              △ structural match
              │
    SqlResource / wrappers / integrations

"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolSqlResource(Protocol):
    """
    AI-CORE-BEGIN
        ROLE: Typed contract for async SQL connection lifecycle and execution.
        CONTRACT: Implementations expose rollup, open/begin/commit/rollback/close, execute.
        INVARIANTS: Structural subtyping only; no runtime enforcement beyond isinstance. ``close`` has a harmless default, so a manager holding no connection still satisfies the contract.
    AI-CORE-END
    """

    @property
    def rollup(self) -> bool:
        """Whether rollup (commit-as-rollback) mode is active for this manager."""
        ...

    async def check_rollup_support(self) -> bool:
        """Same contract as ``BaseResource.check_rollup_support`` for SQL managers."""
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

    async def close(self) -> None:
        """Release the connection this manager holds; harmless when it holds none."""

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """Run a SQL statement with optional positional parameters."""
        ...
