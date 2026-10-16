# tests/action_machine/resources/test_resource_unit_of_work.py
"""
Tests for one connection per unit of work — concurrency, isolation, and the two paths out.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``PostgresResource`` must hold one connection for the length of one unit of work
and share it with nobody. Two defects follow from the old shape — a single
connection per process — and this module is written to catch both:

* concurrent callers on one connection make the driver refuse the second
  operation ("another operation is in progress");
* a transaction that yields between ``BEGIN`` and ``COMMIT`` lets a second
  caller's statements, and a second caller's ``COMMIT``, into its session.

No test here needs a database. The instrument is the fake pool and the fake
connection from ``tests.support.fake_pool``: the connection enforces the
driver's one-operation-at-a-time rule, and the pool records both a high-water
mark and how many connections are still borrowed.

The resource's other construction form — its own connection from
``connection_params`` — deliberately has no unit test here: creating that
connection is the driver's call, and the plan exercises it in the demo and the
examples rather than by faking the driver.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    test
      │  creates one resource per unit of work, from one shared pool
      v
    PostgresResource(pool=…) ──open()──> FakeConnection ──release──> FakePool
      │                                    │
      │                                    └── one operation at a time
      └── the test itself plays the boundary: open, use, close in a finally

"""

from __future__ import annotations

import asyncio
import inspect

import pytest

from aoa.action_machine.exceptions import ConnectionValidationError, TransactionLeftOpenError
from aoa.action_machine.resources.postgres.postgres_resource import PostgresResource

from ...support.fake_pool import FakePool, InterfaceError

CONCURRENT_UNITS = 30


async def _unit_of_work(
    pool: FakePool,
    statements: tuple[str, ...],
    *,
    opened: asyncio.Event | None = None,
    gate: asyncio.Event | None = None,
) -> None:
    """
    Play the boundary's shape: build a resource from the pool, open it, work, close it.

    ``opened`` is set once the resource holds its connection, so a test can act at
    a known point; ``gate`` lets a test hold a unit inside its transaction.
    """
    resource = PostgresResource(pool=pool)
    await resource.open()
    try:
        if opened is not None:
            opened.set()
        if gate is not None:
            await gate.wait()  # only the cancellation test uses this, and it cancels the task
        for statement in statements:
            await resource.execute(statement)
    finally:
        await resource.close()


# ═════════════════════════════════════════════════════════════════════════════
# FR-005 / SC-022 — the two construction forms, and nothing else
# ═════════════════════════════════════════════════════════════════════════════


def test_construction_has_exactly_the_documented_shape() -> None:
    """No substitution parameter and no positional pool: exactly the two forms plus rollup."""
    params = inspect.signature(PostgresResource.__init__).parameters

    assert list(params) == ["self", "connection_params", "pool", "rollup"]
    assert params["connection_params"].default is None
    assert params["pool"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["rollup"].kind is inspect.Parameter.KEYWORD_ONLY


def test_construction_rejects_both_forms_at_once() -> None:
    """A resource with a connection description *and* a pool is a construction error."""
    with pytest.raises(ConnectionValidationError):
        PostgresResource({"dsn": "postgresql://example"}, pool=FakePool())


def test_construction_rejects_neither_form() -> None:
    """A resource with no way to reach a connection is a construction error."""
    with pytest.raises(ConnectionValidationError):
        PostgresResource()


def test_pool_cannot_be_passed_positionally() -> None:
    """The pool is the second form, and a keyword keeps the two from being confused."""
    with pytest.raises(TypeError):
        PostgresResource({"dsn": "postgresql://example"}, FakePool())  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# FR-001 to FR-003 / SC-001, SC-003 — thirty concurrent units of work
# ═════════════════════════════════════════════════════════════════════════════


async def test_thirty_concurrent_units_of_work_all_succeed() -> None:
    """Thirty callers, one shared pool, one connection each: 0 failures, 0 interface errors."""
    pool = FakePool(min_size=0, max_size=10, timeout=5.0)

    results = await asyncio.gather(
        *(_unit_of_work(pool, ("SELECT 1", "SELECT 2")) for _ in range(CONCURRENT_UNITS)),
        return_exceptions=True,
    )

    failures = [r for r in results if isinstance(r, BaseException)]
    interface_errors = [r for r in failures if isinstance(r, InterfaceError)]
    assert failures == []
    assert interface_errors == []
    assert pool.held == 0
    assert pool.high_water <= pool.max_size


async def test_correctness_does_not_depend_on_the_pool_ceiling() -> None:
    """The same declaration succeeds with a ceiling of one (serialized) and of ten (parallel)."""
    for ceiling in (1, 10):
        pool = FakePool(min_size=0, max_size=ceiling, timeout=5.0)
        results = await asyncio.gather(
            *(_unit_of_work(pool, ("SELECT 1",)) for _ in range(CONCURRENT_UNITS)),
            return_exceptions=True,
        )
        failures = [r for r in results if isinstance(r, BaseException)]
        assert failures == [], f"ceiling {ceiling}: {failures[:1]}"
        assert pool.held == 0
        assert pool.high_water <= ceiling


# ═════════════════════════════════════════════════════════════════════════════
# FR-002 / SC-002 — two concurrent transactions stay apart
# ═════════════════════════════════════════════════════════════════════════════


async def test_two_concurrent_transactions_do_not_interleave() -> None:
    """Both transactions open at once; neither one's statements appear on the other's connection."""
    pool = FakePool(min_size=0, max_size=2, timeout=5.0)
    barrier = asyncio.Barrier(2)

    async def transaction(tag: str) -> None:
        resource = PostgresResource(pool=pool)
        await resource.open()
        try:
            await resource.begin()
            # Bounded for the same reason: two units must meet here, and a red run must fail fast.
            await asyncio.wait_for(barrier.wait(), timeout=2.0)
            await resource.execute(f"{tag}:insert")
            await resource.execute(f"{tag}:update")
            await resource.commit()
        finally:
            await resource.close()

    await asyncio.gather(transaction("a"), transaction("b"))

    per_connection = [conn.operations for conn in pool.connections]
    assert sorted(per_connection) == [
        ["BEGIN", "a:insert", "a:update", "COMMIT"],
        ["BEGIN", "b:insert", "b:update", "COMMIT"],
    ]
    assert pool.held == 0


# ═════════════════════════════════════════════════════════════════════════════
# FR-006 / SC-004 — every path out returns the connection
# ═════════════════════════════════════════════════════════════════════════════


async def test_a_unit_of_work_that_raises_still_returns_its_connection() -> None:
    """An exception inside the unit of work does not keep the connection."""
    pool = FakePool(min_size=0, max_size=2, timeout=5.0)

    class UnitOfWorkError(Exception):
        """Raised by the unit of work under test."""

    async def failing_unit() -> None:
        resource = PostgresResource(pool=pool)
        await resource.open()
        try:
            await resource.execute("SELECT 1")
            raise UnitOfWorkError
        finally:
            await resource.close()

    with pytest.raises(UnitOfWorkError):
        await failing_unit()

    assert pool.held == 0
    assert pool.free == 1


async def test_a_cancelled_unit_of_work_still_returns_its_connection() -> None:
    """Cancellation mid-operation is a path out too, and the connection comes back."""
    pool = FakePool(min_size=0, max_size=2, timeout=5.0)
    opened = asyncio.Event()
    gate = asyncio.Event()

    task = asyncio.create_task(_unit_of_work(pool, ("SELECT 1",), opened=opened, gate=gate))
    # Bounded on purpose: a red run must fail here, not wait for an event nobody will set.
    # On that red path the task is collected below, so no exception is left unretrieved.
    try:
        await asyncio.wait_for(opened.wait(), timeout=2.0)
    except TimeoutError:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise
    assert pool.held == 1

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert pool.held == 0
    assert pool.free == 1
    assert all(not conn.busy for conn in pool.connections)


# ═════════════════════════════════════════════════════════════════════════════
# FR-044 / SC-023 — closing with a transaction still open fails fast, after cleanup
# ═════════════════════════════════════════════════════════════════════════════


async def test_close_with_a_transaction_open_returns_the_connection_then_raises() -> None:
    """Rollback, return, and only then the violation — fail-fast never costs a connection."""
    pool = FakePool(min_size=0, max_size=1, timeout=1.0)
    resource = PostgresResource(pool=pool)
    await resource.open()
    await resource.begin()
    await resource.execute("INSERT")

    with pytest.raises(TransactionLeftOpenError):
        await resource.close()

    assert pool.held == 0
    assert pool.free == 1
    assert pool.connections[0].operations == ["BEGIN", "INSERT", "ROLLBACK"]


async def test_a_second_close_is_silent_and_returns_nothing_twice() -> None:
    """The resource is empty after the first close, so the second one has nothing to say."""
    pool = FakePool(min_size=0, max_size=1, timeout=1.0)
    resource = PostgresResource(pool=pool)
    await resource.open()
    await resource.begin()

    with pytest.raises(TransactionLeftOpenError):
        await resource.close()

    assert await resource.close() is None
    assert pool.held == 0


async def test_a_committed_transaction_leaves_nothing_to_report() -> None:
    """Committing closes the transaction flag, so closing afterwards is silent."""
    pool = FakePool(min_size=0, max_size=1, timeout=1.0)
    resource = PostgresResource(pool=pool)
    await resource.open()
    await resource.begin()
    await resource.commit()

    assert await resource.close() is None
    assert pool.connections[0].operations == ["BEGIN", "COMMIT"]


async def test_a_rollup_commit_closes_the_flag_through_rollback() -> None:
    """With rollup the commit is a rollback, and it ends the transaction just the same."""
    pool = FakePool(min_size=0, max_size=1, timeout=1.0)
    resource = PostgresResource(pool=pool, rollup=True)
    await resource.open()
    await resource.begin()
    await resource.commit()

    assert await resource.close() is None
    assert pool.connections[0].operations == ["BEGIN", "ROLLBACK"]
