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
         |  opens one data source per database: the connection parameters and the pool
         v
    OrdersResource(data_source=shop)        # class OrdersResource(PostgresResource[ShopDataSource])
         |  open(): one connection borrowed from the data source
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

- ``PostgresDataSource``: the kind of data source of a PostgreSQL database — connection parameters and the pool several resources share.
- ``PostgresResource``: resource manager for PostgreSQL connections. It always names its data source and holds at most one connection, only for its own unit of work: taken from the data source in ``open()``, given back in ``close()``.
"""
try:
    import asyncpg  # noqa: F401
except ImportError:
    raise ImportError(
        "To use action_machine.resources.postgres, install the optional dependency: " "pip install aoa-run[postgres]"
    ) from None

from aoa.action_machine.resources.postgres.postgres_data_source import PostgresDataSource
from aoa.action_machine.resources.postgres.postgres_resource import PostgresResource

__all__ = ["PostgresDataSource", "PostgresResource"]
