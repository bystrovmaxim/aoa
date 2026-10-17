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
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.resources.postgres.postgres_resource import PostgresResource

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
