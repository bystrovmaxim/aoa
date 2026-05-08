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

    App bootstrap
         |
         v
    PostgresResource
         |
         v
    asyncpg pool / connections
         |
         v
    ActionMachine resources used by actions

═══════════════════════════════════════════════════════════════════════════════
INSTALLATION
═══════════════════════════════════════════════════════════════════════════════

    pip install aoa-run[postgres]

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``PostgresResource``: resource manager for PostgreSQL connections.
"""
try:
    import asyncpg  # noqa: F401
except ImportError:
    raise ImportError(
        "To use action_machine.integrations.postgres, install the optional dependency: "
        "pip install aoa-run[postgres]"
    ) from None

from action_machine.integrations.postgres.postgres_resource import PostgresResource

__all__ = ["PostgresResource"]
