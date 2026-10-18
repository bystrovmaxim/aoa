# tests/resources/test_postgres_helpers.py
"""
Tests for the driver's protected helpers.

The query surface left the SQL contract, and a domain resource runs its statements
through two protected members of the driver it holds: ``_execute`` for a statement
and ``_fetchrow`` for a row. Both go through one check — a resource that never
opened, or one already closed, refuses with the framework's named error rather than
an attribute error — and both turn a failure of the connection into ``HandleError``
with the driver's own error chained as its cause.

Scenarios covered:
    - ``_execute`` on a resource that never opened: the named failure.
    - ``_fetchrow`` on a resource that never opened: the named failure.
    - both helpers on a closed resource: the same named failure.
    - a connection that refuses: ``HandleError`` with the driver's error chained.
    - parameters reach the connection positionally, and ``None`` equals ``()``.
    - ``_fetchrow`` answers the row the connection holds, and ``None`` when it holds none.
    - ``_fetch`` answers every row in the driver's order, a list of one for a single
      row, and ``[]`` when it holds none.
    - ``_fetch`` forwards positional parameters, and ``None`` equals ``()``.
    - ``_fetchval`` answers the first value of the first row, not the row or a
      tuple, and ``None`` when nothing matched.
    - ``_fetchval`` answers ``None`` for a matched row whose first value is SQL
      ``NULL`` too, and says so: the two cases are indistinguishable here.
    - the new pair refuses a never-opened and a closed resource with the same
      named failure, and wraps a driver failure with its cause, like the pair it
      joins.
    - the driver offers exactly four query members, no driver type appears in the
      new signatures, and the wrapper exposes none of them.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.resources.postgres.postgres_resource import PostgresResource
from aoa.action_machine.resources.sql.wrapper_sql_resource import WrapperSqlResource

from ...support.fake_pool import FakeConnection, FakePool


async def _open(resource: PostgresResource, pool: FakePool) -> FakeConnection:
    """Open the resource and hand back the one connection it holds."""
    await resource.open()
    return next(iter(pool.borrowed))


async def test_execute_without_a_connection_names_the_failure() -> None:
    """A statement on a resource that never opened is the framework's error, not an attribute error."""
    resource = PostgresResource(pool=FakePool())

    with pytest.raises(HandleError, match="Connection is not open"):
        await resource._execute("SELECT 1")


async def test_fetchrow_without_a_connection_names_the_failure() -> None:
    """A read on a resource that never opened refuses the same way."""
    resource = PostgresResource(pool=FakePool())

    with pytest.raises(HandleError, match="Connection is not open"):
        await resource._fetchrow("SELECT 1")


async def test_both_helpers_refuse_a_closed_resource() -> None:
    """After closing, the connection is gone and both helpers say so instead of failing obscurely."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    await resource.open()
    await resource.close()

    with pytest.raises(HandleError, match="Connection is not open"):
        await resource._execute("SELECT 1")
    with pytest.raises(HandleError, match="Connection is not open"):
        await resource._fetchrow("SELECT 1")


async def test_a_failing_connection_arrives_as_handle_error_with_its_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The driver's own error never reaches the caller raw; it is the cause of the framework's error."""

    async def refuse(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("the server went away")

    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)
    monkeypatch.setattr(connection, "execute", refuse)
    monkeypatch.setattr(connection, "fetchrow", refuse)

    # Built lazily: a failing first call must not leave the second coroutine unawaited.
    for call in (lambda: resource._execute("SELECT 1"), lambda: resource._fetchrow("SELECT 1")):
        with pytest.raises(HandleError, match="SQL execution failed") as exc_info:
            await call()
        assert isinstance(exc_info.value.__cause__, RuntimeError)


async def test_parameters_reach_the_connection_positionally() -> None:
    """Both helpers forward the positional parameters the domain method wrote."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    await resource._execute("UPDATE t SET seen = true WHERE id = $1", ("p1",))
    await resource._fetchrow("SELECT id FROM t WHERE id = $1", ("p1",))

    assert connection.calls == [
        ("UPDATE t SET seen = true WHERE id = $1", ("p1",)),
        ("SELECT id FROM t WHERE id = $1", ("p1",)),
    ]


async def test_none_and_an_empty_tuple_are_the_same_call() -> None:
    """A statement without parameters takes the same path whether they are omitted or empty."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    await resource._execute("SELECT 1", None)
    await resource._execute("SELECT 1", ())

    assert [call[1] for call in connection.calls] == [(), ()]


async def test_fetchrow_answers_the_row_and_the_absence_of_one() -> None:
    """The row helper returns what the connection holds, or nothing when it holds nothing."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    connection.row = {"id": "p1"}
    assert await resource._fetchrow("SELECT id FROM t WHERE id = $1", ("p1",)) == {"id": "p1"}

    connection.row = None
    assert await resource._fetchrow("SELECT id FROM t WHERE id = $1", ("p1",)) is None


async def test_fetch_answers_an_empty_list_when_nothing_matches() -> None:
    """A page with no match is an empty list, not nothing, so the caller iterates without a guard."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    connection.rows = []

    assert await resource._fetch("SELECT id FROM t WHERE false") == []


async def test_fetch_answers_a_list_of_one_for_a_single_row() -> None:
    """One matching row arrives as a list of one, not as the row itself."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    connection.rows = [{"id": "p1"}]

    answer = await resource._fetch("SELECT id FROM t WHERE id = $1", ("p1",))

    assert answer == [{"id": "p1"}]
    assert isinstance(answer, list)


async def test_fetch_answers_every_row_in_the_driver_order() -> None:
    """The helper neither sorts nor truncates: each statement answers what the connection returned."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    connection.rows = [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]
    assert await resource._fetch("SELECT id FROM t ORDER BY id") == connection.rows

    connection.rows = [{"id": "p3"}, {"id": "p1"}, {"id": "p2"}]
    assert await resource._fetch("SELECT id FROM t") == connection.rows


async def test_fetch_forwards_its_parameters_positionally() -> None:
    """The page path takes its parameters the way the existing pair does."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    await resource._fetch("SELECT id FROM t WHERE id = $1", ("p1",))

    assert connection.calls == [("SELECT id FROM t WHERE id = $1", ("p1",))]


async def test_fetch_treats_no_parameters_and_an_empty_tuple_alike() -> None:
    """A page without parameters takes the same path whether they are omitted or empty."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    await resource._fetch("SELECT id FROM t", None)
    await resource._fetch("SELECT id FROM t", ())

    assert [call[1] for call in connection.calls] == [(), ()]


async def test_fetchval_answers_the_first_value_not_the_row() -> None:
    """The value helper answers the first column of the first row, not the row and not a tuple."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    connection.row = {"total": 2}
    connection.value = 2

    answer = await resource._fetchval("SELECT count(*) FROM t")

    assert answer == 2
    assert not isinstance(answer, (dict, tuple))


async def test_fetchval_answers_nothing_when_nothing_matches() -> None:
    """A value with no match is nothing, so the caller decides what absence means."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    connection.value = None

    assert await resource._fetchval("SELECT count(*) FROM t WHERE false") is None


async def test_fetchval_cannot_tell_sql_null_from_no_row() -> None:
    """A matched row whose first value is NULL and no row at all answer the same None, by design."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    connection.row = {"total": None}
    connection.value = None

    assert await resource._fetchval("SELECT count(*) FROM t") is None
    assert await resource._fetchval("SELECT count(*) FROM t WHERE false") is None


async def test_fetchval_forwards_its_parameters_positionally() -> None:
    """The value path takes its parameters the way the other three helpers do."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)

    await resource._fetchval("SELECT count(*) FROM t WHERE id = $1", ("p1",))

    assert connection.calls == [("SELECT count(*) FROM t WHERE id = $1", ("p1",))]


async def test_the_new_pair_refuses_a_resource_that_never_opened() -> None:
    """Neither new helper runs without a connection, and neither fails on a missing attribute."""
    resource = PostgresResource(pool=FakePool())

    with pytest.raises(HandleError, match="Connection is not open"):
        await resource._fetch("SELECT 1")
    with pytest.raises(HandleError, match="Connection is not open"):
        await resource._fetchval("SELECT 1")


async def test_the_new_pair_refuses_a_closed_resource() -> None:
    """After closing, the connection is gone and both new helpers say so instead of failing obscurely."""
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    await resource.open()
    await resource.close()

    with pytest.raises(HandleError, match="Connection is not open"):
        await resource._fetch("SELECT 1")
    with pytest.raises(HandleError, match="Connection is not open"):
        await resource._fetchval("SELECT 1")


async def test_the_new_pair_wraps_a_driver_failure_with_its_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The driver's own error never reaches the caller raw, for either new helper."""

    async def refuse(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("the server went away")

    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    connection = await _open(resource, pool)
    monkeypatch.setattr(connection, "fetch", refuse)
    monkeypatch.setattr(connection, "fetchval", refuse)

    # Built lazily: a failing first call must not leave the second coroutine unawaited.
    for call in (lambda: resource._fetch("SELECT 1"), lambda: resource._fetchval("SELECT 1")):
        with pytest.raises(HandleError, match="SQL execution failed") as exc_info:
            await call()
        assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_the_new_pair_annotations_name_no_driver_type() -> None:
    """The domain-facing signatures answer plain shapes, not the driver's records."""
    fetch_return = str(inspect.signature(PostgresResource._fetch).return_annotation)
    fetchval_return = str(inspect.signature(PostgresResource._fetchval).return_annotation)

    assert "asyncpg" not in fetch_return
    assert "list[Any]" in fetch_return
    assert fetchval_return == "Any"


def test_the_driver_offers_exactly_four_query_helpers() -> None:
    """Four driver answers, four members: a convenience helper beside them would be a fifth surface."""
    names = {name for name in dir(PostgresResource) if name.startswith(("_execute", "_fetch"))}

    assert names == {"_execute", "_fetchrow", "_fetch", "_fetchval"}


def test_the_wrapper_exposes_no_query_member() -> None:
    """A nested action receives the wrapper, so no query member of any shape may be reachable there."""
    for name in ("_execute", "_fetchrow", "_fetch", "_fetchval"):
        assert not hasattr(WrapperSqlResource, name)
