# packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/__init__.py
"""
PostgreSQL integration package for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose PostgreSQL resource-manager integration based on ``asyncpg``.
This package root provides the public import surface for PostgreSQL connection
lifecycle management used by ActionMachine runtime components.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    App bootstrap (lifespan)
         |  creates one pool for the process, from the same connection parameters
         v
    PostgresResource(pool=...)        or        PostgresResource({"dsn": ...})
         |  open(): one connection borrowed          open(): its own connection
         |  close(): returned, pool stays open       close(): the connection closed
         v
    ActionMachine resources used by actions

═══════════════════════════════════════════════════════════════════════════════
INSTALLATION
═══════════════════════════════════════════════════════════════════════════════

    pip install aoa-run[postgres]

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``PostgresResource``: resource manager for PostgreSQL connections. It holds at most one connection, only for its own unit of work: taken in ``open()`` from a pool or from the driver, given back in ``close()``.
"""
try:
    import asyncpg  # noqa: F401
except ImportError:
    raise ImportError(
        "To use action_machine.resources.postgres, install the optional dependency: " "pip install aoa-run[postgres]"
    ) from None

from aoa.action_machine.resources.postgres.postgres_resource import PostgresResource

__all__ = ["PostgresResource"]
