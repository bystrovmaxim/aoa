# packages/aoa-action-machine/src/aoa/action_machine/resources/sql/protocol_sql_resource.py
# pylint: disable=unnecessary-ellipsis  # Protocol member bodies use ellipsis per PEP 544 stubs.
"""
ProtocolSqlResource — structural contract for transactional SQL access.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Defines the surface required for the lifecycle of a SQL-backed resource:
``rollup`` visibility, ``open`` / transaction boundaries and ``close``.
Implementations may be concrete drivers (for example Postgres) or thin proxies;
static checking uses this protocol without importing those types.

The contract carries **no query member**. A statement is run by a domain method
through the protected helpers of the driver it holds, and the proxy a nested
action receives has nothing of its own to delegate — a nested action cannot reach
the connection at all, by construction rather than by a rule.

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

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolSqlResource(Protocol):
    """
    AI-CORE-BEGIN
        ROLE: Typed contract for async SQL connection lifecycle and transaction boundaries.
        CONTRACT: Implementations expose rollup, open/begin/commit/rollback/close; no query member is part of the contract.
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
