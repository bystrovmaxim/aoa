# packages/aoa-action-machine/src/aoa/action_machine/resources/sql/pool_protocol.py
# pylint: disable=unnecessary-ellipsis  # Protocol member bodies use ellipsis per PEP 544 stubs.
"""
PoolProtocol — the shape of a connection pool a SQL resource borrows from.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A SQL resource that owns no connection is handed a ready pool and takes one
connection from it for the length of its unit of work. The framework neither
creates, configures nor closes that pool: the pool is process state, created by
the application in its lifespan from its own connection parameters.

What the framework relies on is this shape. The driver's own ``asyncpg.Pool``
satisfies it: ``acquire(timeout=…)`` returns a proxy supporting both ``await``
and ``async with``, and ``release`` / ``close`` are coroutine functions. The
tests' fake pool satisfies it too, so a pool-backed resource is exercised with
no database running.

The protocol is deliberately not ``runtime_checkable``: nothing checks an object
against it at run time, and a pool is accepted as it is.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    application lifespan
        │  create_pool(dsn, min_size=…, max_size=…)
        v
    pool (process state)  ──acquire(timeout=…)──>  connection
        ^                                              │
        └───────────────release(connection)────────────┘
                       (the resource's ``close()``)

    The pool outlives every resource; a resource never closes it.

"""

from __future__ import annotations

from typing import Any, Protocol


class PoolProtocol(Protocol):
    """
    AI-CORE-BEGIN
    ROLE: Structural type of the connection pool a SQL resource borrows from.
    CONTRACT: ``acquire(timeout=…)`` waits for a free connection and returns an awaitable proxy; ``release(conn)`` returns it; ``close()`` closes the pool itself.
    INVARIANTS: The pool outlives every resource, a resource never closes it, and the wait for a free connection is bounded by the stated timeout rather than by nothing.
    AI-CORE-END
    """

    def acquire(self, *, timeout: float | None = None) -> Any:  # noqa: V107 - the driver's own keyword
        """Wait for a free connection and return a proxy that is awaited or used as a context manager."""
        ...

    async def release(self, conn: Any) -> None:  # noqa: V107 - the driver's own parameter
        """Return a borrowed connection to the pool, leaving the pool open."""
        ...

    async def close(self) -> None:
        """Close the pool itself, once every borrowed connection is back."""
        ...
