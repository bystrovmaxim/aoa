# tests/support/pooled_storage.py
"""
A PostgreSQL resource over a fake pool, and the helper that builds it.

Tests of the pooled path build ``pooled(pool)``: a ``PooledStorage`` given that pool,
with no database and no ``PostgresPool`` wrapper. ``PooledStorage`` is excluded from
the graph model, so no graph a test builds sees it.
"""

from __future__ import annotations

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.postgres import PostgresPool, PostgresStorage
from aoa.action_machine.resources.sql.pool_protocol import PoolProtocol


@exclude_graph_model
class PooledStorage(PostgresStorage):
    """A PostgreSQL resource that takes its connection from a pool."""


def pooled(pool: PoolProtocol | PostgresPool, *, rollup: bool = False) -> PooledStorage:
    """A resource working through ``pool``."""
    return PooledStorage(pool=pool, rollup=rollup)  # type: ignore[arg-type]
