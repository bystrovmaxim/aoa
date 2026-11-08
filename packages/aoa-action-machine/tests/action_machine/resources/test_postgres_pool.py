# tests/action_machine/resources/test_postgres_pool.py
"""
``PostgresPool`` keeps the connection parameters and the pool, with no place in the model.

It carries the body ``PostgresDataSource`` had before #487: a DSN or a ready pool — exactly one — with
``open``/``close``, ``acquire``/``release`` and ``async with``. No database runs: a fake
pool stands in for a given pool, and ``asyncpg.create_pool`` is replaced where the pool
creates its own.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.exceptions.connection_validation_error import ConnectionValidationError
from aoa.action_machine.exceptions.handle_error import HandleError
from aoa.action_machine.resources.postgres import postgres_pool as module
from aoa.action_machine.resources.postgres.postgres_pool import PostgresPool

from ...support.fake_pool import FakePool


def test_the_pool_takes_exactly_one_of_a_dsn_and_a_pool() -> None:
    """Both, neither, or pool options beside a ready pool are construction errors."""
    with pytest.raises(ConnectionValidationError, match="exactly one of dsn and pool"):
        PostgresPool("postgresql://example", pool=FakePool())
    with pytest.raises(ConnectionValidationError, match="exactly one of dsn and pool"):
        PostgresPool()
    with pytest.raises(ConnectionValidationError, match=r"pool options \['max_size'\] apply only to a pool it creates"):
        PostgresPool(pool=FakePool(), max_size=3)


async def test_the_pool_creates_its_pool_on_open_and_closes_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """From a DSN: the pool is created with the options in ``open`` and closed in ``close``; ``async with`` does both."""
    created: list[tuple[Any, dict[str, Any]]] = []
    pool = FakePool()

    async def create_pool(dsn: str, **options: Any) -> FakePool:
        created.append((dsn, options))
        return pool

    monkeypatch.setattr(module.asyncpg, "create_pool", create_pool)
    async with PostgresPool("postgresql://example", min_size=1, max_size=4) as source:
        connection = await source.acquire()
        await source.release(connection)
    assert created == [("postgresql://example", {"min_size": 1, "max_size": 4})]
    assert pool.closed


async def test_a_given_pool_is_used_as_it_is_and_left_open() -> None:
    """A ready pool hands connections at once and is not closed by the pool object."""
    pool = FakePool()
    source = PostgresPool(pool=pool)
    connection = await source.acquire()
    await source.release(connection)
    await source.close()
    assert not pool.closed


async def test_a_pool_not_open_hands_out_nothing() -> None:
    """From a DSN, ``acquire`` before ``open`` says the pool is not open."""
    with pytest.raises(HandleError, match="PostgresPool is not open"):
        await PostgresPool("postgresql://example").acquire()


async def test_a_pool_not_open_takes_nothing_back() -> None:
    """A connection cannot be released to a pool object that was never opened."""
    with pytest.raises(HandleError, match="PostgresPool is not open"):
        await PostgresPool("postgresql://example").release(object())
