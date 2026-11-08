# tests/action_machine/resources/test_postgres_connection_modes.py
"""
``PostgresStorage`` chooses how it connects: a pool or its own connection parameters.

A resource takes exactly one of ``pool=`` and ``connection_params=``. With a pool it
borrows a connection in ``open()`` and gives it back in ``close()``; with connection
parameters it opens its own connection with ``asyncpg.connect``, keeps it for the unit
of work and closes it in ``close()``. The transaction is the resource's own in both
modes, and a resource of another kind refuses either argument.

No database runs: the pool is the fake from ``tests.support.fake_pool`` and
``asyncpg.connect`` is replaced for the own-connection mode.
"""

from __future__ import annotations

import inspect
import json
import textwrap
from typing import Any

import pytest

from aoa.action_machine.exceptions.connection_validation_error import ConnectionValidationError
from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.exceptions.transaction_left_open_error import TransactionLeftOpenError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_resource import BaseResource, resource_kind
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources.postgres import PostgresPool, PostgresStorage
from aoa.action_machine.resources.postgres import postgres_storage as module

from ...support.fake_pool import FakeConnection, FakePool
from ...support.isolated_entity_models import run_isolated_model
from ...support.pooled_storage import PooledStorage

# ═════════════════════════════════════════════════════════════════════════════
# The assembly shape — exactly one argument, by keyword
# ═════════════════════════════════════════════════════════════════════════════


def test_construction_has_exactly_the_documented_shape() -> None:
    """The resource is assembled from one connection choice, by keyword, plus rollup."""
    params = inspect.signature(PostgresStorage.__init__).parameters

    assert list(params) == ["self", "pool", "connection_params", "rollup"]
    for name in ("pool", "connection_params", "rollup"):
        assert params[name].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["pool"].default is None
    assert params["connection_params"].default is None
    assert params["rollup"].default is False


def test_both_a_pool_and_connection_parameters_are_refused() -> None:
    """One connection choice only: both are a construction error naming both arguments."""
    with pytest.raises(ConnectionValidationError) as caught:
        PooledStorage(pool=FakePool(), connection_params={"dsn": "postgresql://example"})
    message = str(caught.value)
    assert "pool" in message
    assert "connection_params" in message


def test_neither_a_pool_nor_connection_parameters_is_refused() -> None:
    """One connection choice is required: neither is a construction error naming both arguments."""
    with pytest.raises(ConnectionValidationError) as caught:
        PooledStorage()
    message = str(caught.value)
    assert "pool" in message
    assert "connection_params" in message


# ═════════════════════════════════════════════════════════════════════════════
# Pool mode — one connection borrowed and returned
# ═════════════════════════════════════════════════════════════════════════════


async def test_pool_mode_acquires_a_connection_on_open_and_releases_it_on_close() -> None:
    """The resource holds one connection while open and leaves none borrowed after close."""
    pool = FakePool(min_size=0, max_size=2)
    resource = PooledStorage(pool=pool)

    await resource.open()
    assert pool.held == 1
    await resource._execute("SELECT 1")

    await resource.close()
    assert pool.held == 0
    assert pool.free == 1
    assert pool.connections[0].operations == ["SELECT 1"]


async def test_pool_mode_works_through_a_postgres_pool() -> None:
    """A ``PostgresPool`` over a ready pool is the documented pool argument: it borrows and returns."""
    ready = FakePool(min_size=1)
    source = PostgresPool(pool=ready)
    resource = PooledStorage(pool=source)

    await resource.open()
    assert ready.held == 1
    await resource.close()

    assert ready.held == 0
    assert ready.closed is False


# ═════════════════════════════════════════════════════════════════════════════
# Connection-parameters mode — the resource's own connection
# ═════════════════════════════════════════════════════════════════════════════


def _connect_recorder(connection: FakeConnection) -> tuple[list[tuple[tuple[Any, ...], dict[str, Any]]], Any]:
    """Build a stand-in for ``asyncpg.connect`` and the list it records its calls into."""
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def connect(*args: Any, **kwargs: Any) -> FakeConnection:
        calls.append((args, kwargs))
        return connection

    return calls, connect


async def test_connection_parameters_mode_opens_its_own_connection_on_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """A mapping of parameters reaches ``asyncpg.connect`` as keyword arguments."""
    connection = FakeConnection()
    calls, connect = _connect_recorder(connection)
    monkeypatch.setattr(module.asyncpg, "connect", connect)

    resource = PooledStorage(connection_params={"dsn": "postgresql://example", "user": "shop"})
    await resource.open()

    assert calls == [((), {"dsn": "postgresql://example", "user": "shop"})]
    await resource.close()
    assert connection.closed is True


async def test_connection_parameters_mode_accepts_a_dsn_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """A DSN string reaches ``asyncpg.connect`` as its positional argument."""
    connection = FakeConnection()
    calls, connect = _connect_recorder(connection)
    monkeypatch.setattr(module.asyncpg, "connect", connect)

    resource = PooledStorage(connection_params="postgresql://example")
    await resource.open()
    await resource.close()

    assert calls == [(("postgresql://example",), {})]
    assert connection.closed is True


async def test_connection_parameters_mode_closes_its_own_connection_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """The own connection is opened once, closed once, and a second close has nothing left to close."""
    connection = FakeConnection()
    calls, connect = _connect_recorder(connection)
    monkeypatch.setattr(module.asyncpg, "connect", connect)

    resource = PooledStorage(connection_params={"dsn": "postgresql://example"})
    await resource.open()
    await resource._execute("SELECT 1")
    await resource.close()
    await resource.close()

    assert len(calls) == 1
    assert connection.operations == ["SELECT 1"]
    assert connection.closed is True


# ═════════════════════════════════════════════════════════════════════════════
# Transactions stay inside the resource, both ways
# ═════════════════════════════════════════════════════════════════════════════


async def test_connection_parameters_mode_keeps_the_transaction_on_its_own_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BEGIN, the statements and COMMIT all run on the one connection the resource opened."""
    connection = FakeConnection()
    _, connect = _connect_recorder(connection)
    monkeypatch.setattr(module.asyncpg, "connect", connect)

    resource = PooledStorage(connection_params={"dsn": "postgresql://example"})
    await resource.open()
    await resource.begin()
    await resource._execute("INSERT INTO orders VALUES (1)")
    await resource.commit()
    await resource.close()

    assert connection.operations == ["BEGIN", "INSERT INTO orders VALUES (1)", "COMMIT"]
    assert connection.closed is True


async def test_connection_parameters_mode_closes_the_connection_before_reporting_an_open_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Closing with a transaction open rolls back, closes the own connection, and only then raises."""
    connection = FakeConnection()
    _, connect = _connect_recorder(connection)
    monkeypatch.setattr(module.asyncpg, "connect", connect)

    resource = PooledStorage(connection_params={"dsn": "postgresql://example"})
    await resource.open()
    await resource.begin()
    await resource._execute("INSERT INTO orders VALUES (1)")

    with pytest.raises(TransactionLeftOpenError):
        await resource.close()

    assert connection.operations == ["BEGIN", "INSERT INTO orders VALUES (1)", "ROLLBACK"]
    assert connection.closed is True


# ═════════════════════════════════════════════════════════════════════════════
# A resource of another kind takes neither argument
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
class _CacheStorage(BaseStorage):
    """A resource of a kind that knows no pool."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        return None


def test_a_resource_of_another_kind_takes_no_pool() -> None:
    """Only a PostgreSQL resource has a pool argument: another kind refuses it instead of accepting it."""
    with pytest.raises(TypeError):
        _CacheStorage(pool=FakePool())


def test_a_resource_of_another_kind_takes_no_connection_parameters() -> None:
    """Only a PostgreSQL resource has a connection-parameters argument: another kind refuses it."""
    with pytest.raises(TypeError):
        _CacheStorage(connection_params={"dsn": "postgresql://example"})


# ═════════════════════════════════════════════════════════════════════════════
# The pool is in neither the model nor the graph
# ═════════════════════════════════════════════════════════════════════════════


def test_the_pool_is_a_plain_class_outside_the_resource_kinds() -> None:
    """``PostgresPool`` has no kind, no ``@meta`` and no ``@entities`` declaration."""
    assert not issubclass(PostgresPool, BaseResource)
    assert not hasattr(PostgresPool, "_meta_info")
    assert not hasattr(PostgresPool, "_entities_info")
    with pytest.raises(DeclarationStructureError):
        resource_kind(PostgresPool)


_MODEL = textwrap.dedent(
    """
    import json

    from pydantic import Field

    from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.intents.entities import entities
    from aoa.action_machine.intents.entity import entity
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources.postgres import PostgresPool, PostgresStorage


    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Shop"


    @entity(description="Customer order", domain=ShopDomain)
    class ShopOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")


    @meta(description="The shop database")
    @entities(ShopOrderCoreEntity)
    class ShopDatabaseStorage(PostgresStorage):
        pass


    pool = PostgresPool(pool=object())
    ShopDatabaseStorage(pool=pool)
    print(create_node_graph_coordinator().to_json())
    """
)


@pytest.fixture(scope="module")
def built_graph() -> dict[str, Any]:
    """A graph built in a fresh interpreter from a PostgreSQL resource assembled with a pool."""
    result = run_isolated_model(_MODEL)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_a_built_graph_has_no_trace_of_the_pool(built_graph: dict[str, Any]) -> None:
    """The resource is a node; the pool it holds is not a node, an edge end, or a property."""
    labels = {node["label"] for node in built_graph["nodes"]}

    assert "ShopDatabaseStorage" in labels
    assert all(node["type"] != "DataSource" for node in built_graph["nodes"])
    assert "PostgresPool" not in json.dumps(built_graph)
