# tests/support/fake_data_source.py
"""
A PostgreSQL data source over a fake pool, and a resource that names it.

Tests of the pooled path build ``pooled(pool)``: a ``PooledStorage`` working through a
``FakeDataSource`` given that pool, with no database. Both classes are excluded from the
graph model, so no graph a test builds sees them.
"""

from __future__ import annotations

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.postgres import PostgresDataSource, PostgresStorage
from aoa.action_machine.resources.sql.pool_protocol import PoolProtocol


@exclude_graph_model
@meta(description="The database a test fakes")
class FakeDataSource(PostgresDataSource):
    """A PostgreSQL data source given a ready pool."""


@exclude_graph_model
class PooledStorage(PostgresStorage[FakeDataSource]):
    """A PostgreSQL resource that works through ``FakeDataSource``."""


def pooled(pool: PoolProtocol, *, rollup: bool = False) -> PooledStorage:
    """A resource working through a data source over ``pool``."""
    return PooledStorage(data_source=FakeDataSource(pool=pool), rollup=rollup)
