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

SqlResource
    Base class for SQL connection managers with transactions.
    Contract: open(), begin(), commit(), rollback(), execute().

PostgresResource
    SqlResource implementation for PostgreSQL using asyncpg.
    Supports rollup mode: with rollup=True, commit() runs ROLLBACK instead of COMMIT
    for safe testing against production-like databases.

WrapperSqlResource
    Proxy that forbids transaction control at nested levels but allows queries.
    Created automatically when connections are passed to child actions via ToolsBox.run().
    Concrete modules: ``action_machine.resources.sql``.

═══════════════════════════════════════════════════════════════════════════════
TEST LAYOUT
═══════════════════════════════════════════════════════════════════════════════

    tests/resources/
    ├── __init__.py                             — this file
    ├── test_sql_resource.py          — SqlResource, rollup, abstract API
    ├── test_wrapper_sql_resource.py  — transaction prohibition, execute delegation
    ├── test_external_service_resource.py        — ExternalServiceResource, rollup flag
    ├── test_wrapper_external_service_resource.py — nested proxy for external clients
    └── test_connections_dict.py                — connections dict typing
"""
