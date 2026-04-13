"""
PostgreSQL integration package for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose PostgreSQL resource-manager integration based on ``asyncpg``.
This package root provides the public import surface for PostgreSQL connection
lifecycle management used by ActionMachine runtime components.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Optional dependency ``asyncpg`` must be available at import time.
- ``PostgresConnectionManager`` is the only public symbol exported here.
- Runtime behavior is implemented in the manager module; package root acts as
  dependency guard + stable API namespace.

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

    pip install action-machine[postgres]

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``PostgresConnectionManager``: resource manager for PostgreSQL connections.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Importing this package without ``asyncpg`` raises ``ImportError`` with
  installation guidance.
- This module exposes integration contracts only; SQL behavior belongs to the
  manager implementation.

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
        "pip install action-machine[postgres]"
    ) from None

from action_machine.integrations.postgres.postgres_connection_manager import PostgresConnectionManager

__all__ = ["PostgresConnectionManager"]
