# tests/resources/__init__.py
"""
Tests for ActionMachine resource managers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers resource managers — components that manage connections to external systems
(databases, caches, message queues). Verifies opening/closing connections, running
queries, transaction handling, and proxy wrappers for nested actions.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

SqlManager
    Base class for SQL connection managers with transactions.
    Contract: open(), begin(), commit(), rollback(), execute().

PostgresConnectionManager
    SqlManager implementation for PostgreSQL using asyncpg.
    Supports rollup mode: with rollup=True, commit() runs ROLLBACK instead of COMMIT
    for safe testing against production-like databases.

WrapperSqlManager
    Proxy that forbids transaction control at nested levels but allows queries.
    Created automatically when connections are passed to child actions via ToolsBox.run().
    Concrete modules: ``action_machine.resources.sql``.

═══════════════════════════════════════════════════════════════════════════════
TEST LAYOUT
═══════════════════════════════════════════════════════════════════════════════

    tests/resources/
    ├── __init__.py                             — this file
    ├── test_postgres_connection_manager.py     — open/begin/execute/commit/rollback, rollup
    ├── test_sql_manager.py          — SqlManager, rollup, abstract API
    ├── test_wrapper_sql_manager.py  — transaction prohibition, execute delegation
    └── test_connections_dict.py                — connections dict typing
"""
