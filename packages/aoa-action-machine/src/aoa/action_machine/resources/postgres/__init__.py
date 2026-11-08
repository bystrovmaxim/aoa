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
         |  opens one pool per database: the connection parameters and the pool
         v
    OrdersStorage(pool=shop)
         |  open(): one connection borrowed from the pool
         |  close(): returned, the pool stays open
         v
    ActionMachine resources used by actions

═══════════════════════════════════════════════════════════════════════════════
INSTALLATION
═══════════════════════════════════════════════════════════════════════════════

    pip install aoa-run[postgres]

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``PostgresPool``: the connection source of a PostgreSQL database — connection parameters and the pool several resources share. A plain class: it is in neither the model nor the graph.
- ``PostgresStorage``: resource manager for PostgreSQL connections. It takes exactly one of ``pool=`` and ``connection_params=`` and holds at most one connection, only for its own unit of work.
"""
try:
    import asyncpg  # noqa: F401
except ImportError:
    raise ImportError(
        "To use action_machine.resources.postgres, install the optional dependency: " "pip install aoa-run[postgres]"
    ) from None

from aoa.action_machine.resources.postgres.postgres_pool import PostgresPool
from aoa.action_machine.resources.postgres.postgres_storage import PostgresStorage

__all__ = ["PostgresPool", "PostgresStorage"]
