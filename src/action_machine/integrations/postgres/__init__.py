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
    PostgresConnectionManager
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

- ``PostgresConnectionManager``: resource manager for PostgreSQL connections.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public namespace for PostgreSQL integration.
CONTRACT: Export PostgresConnectionManager and fail fast when asyncpg is missing.
INVARIANTS: Stable single-symbol export and explicit optional dependency guard.
FLOW: import package -> validate asyncpg -> use connection manager in runtime.
FAILURES: Missing asyncpg dependency.
EXTENSION POINTS: Manager-level configuration and lifecycle hooks.
AI-CORE-END
"""
try:
    import asyncpg  # noqa: F401
except ImportError:
    raise ImportError(
        "To use action_machine.integrations.postgres, install the optional dependency: "
        "pip install aoa-run[postgres]"
    ) from None

from action_machine.integrations.postgres.postgres_connection_manager import PostgresConnectionManager

__all__ = ["PostgresConnectionManager"]
