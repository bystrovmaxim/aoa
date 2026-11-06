# tests/action_machine/resources/test_postgres_data_source.py
"""
``PostgresDataSource`` keeps the connection parameters and the pool; ``PostgresResource``
takes exactly one of its own connection parameters and the data source it names.

No database runs: a fake pool stands in for a given pool, and ``asyncpg.create_pool`` is
replaced where the data source creates its own.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.exceptions.connection_validation_error import ConnectionValidationError
from aoa.action_machine.exceptions.data_source_declaration_error import DataSourceDeclarationError
from aoa.action_machine.exceptions.handle_error import HandleError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.postgres import PostgresDataSource, PostgresResource
from aoa.action_machine.resources.postgres import postgres_data_source as module

from ...support.fake_data_source import FakeDataSource, PooledResource
from ...support.fake_pool import FakePool


@exclude_graph_model
@meta(description="Another test database")
class _OtherDataSource(PostgresDataSource):
    pass


def test_a_data_source_takes_exactly_one_of_a_dsn_and_a_pool() -> None:
    """Both, neither, or pool options beside a ready pool are construction errors."""
    with pytest.raises(ConnectionValidationError, match="exactly one of dsn and pool"):
        FakeDataSource("postgresql://example", pool=FakePool())
    with pytest.raises(ConnectionValidationError, match="exactly one of dsn and pool"):
        FakeDataSource()
    with pytest.raises(ConnectionValidationError, match=r"pool options \['max_size'\] apply only to a pool it creates"):
        FakeDataSource(pool=FakePool(), max_size=3)


async def test_a_data_source_creates_its_pool_on_open_and_closes_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """From a DSN: the pool is created with the options in ``open`` and closed in ``close``; ``async with`` does both."""
    created: list[tuple[Any, dict[str, Any]]] = []
    pool = FakePool()

    async def create_pool(dsn: str, **options: Any) -> FakePool:
        created.append((dsn, options))
        return pool

    monkeypatch.setattr(module.asyncpg, "create_pool", create_pool)
    async with FakeDataSource("postgresql://example", min_size=1, max_size=4) as source:
        connection = await source.acquire()
        await source.release(connection)
    assert created == [("postgresql://example", {"min_size": 1, "max_size": 4})]
    assert pool.closed


async def test_a_given_pool_is_used_as_it_is_and_left_open() -> None:
    """A ready pool hands connections at once and is not closed by the data source."""
    pool = FakePool()
    source = FakeDataSource(pool=pool)
    connection = await source.acquire()
    await source.release(connection)
    await source.close()
    assert not pool.closed


async def test_a_data_source_not_open_hands_out_nothing() -> None:
    """From a DSN, ``acquire`` before ``open`` says the data source is not open."""
    with pytest.raises(HandleError, match="FakeDataSource is not open"):
        await FakeDataSource("postgresql://example").acquire()


def test_a_resource_that_names_a_data_source_takes_an_instance_of_it() -> None:
    """A data source of another class is refused by a resource that names one."""
    with pytest.raises(DataSourceDeclarationError, match="PooledResource works through FakeDataSource: pass data_source= of that class; got _OtherDataSource"):
        PooledResource(data_source=_OtherDataSource(pool=FakePool()))


def test_connection_parameters_are_not_given_to_a_resource() -> None:
    """Connection parameters live only in a data source: a resource takes none."""
    with pytest.raises(TypeError):
        PooledResource({"dsn": "postgresql://example"})  # type: ignore[misc,call-arg]
    with pytest.raises(TypeError, match="connection_params"):
        PooledResource(connection_params={"dsn": "postgresql://example"})  # type: ignore[call-arg]


def test_a_resource_that_names_no_data_source_is_refused() -> None:
    """``PostgresResource`` itself names none, so it is refused even when given a data source."""
    with pytest.raises(DataSourceDeclarationError, match="PostgresResource names no data source: a PostgreSQL resource names its data source"):
        PostgresResource(data_source=FakeDataSource(pool=FakePool()))


def test_a_pool_is_not_given_to_a_resource() -> None:
    """A pool lives only in a data source."""
    with pytest.raises(TypeError, match="pool"):
        PostgresResource(pool=FakePool())  # type: ignore[call-arg]
