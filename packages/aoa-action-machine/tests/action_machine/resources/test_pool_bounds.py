# tests/action_machine/resources/test_pool_bounds.py
"""
The pool's stated bounds, seen through the resource that borrows from it.

The pool belongs to the application — the framework neither creates it nor closes
it — and what the resource owes is narrow: take one connection, wait when the
ceiling is reached instead of opening a private one, and give the connection
back. These tests exercise that pair with no database. The fake pool records its
high-water mark and how many connections are borrowed, and it bounds the wait.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    PostgresResource(pool=…) ──open()──> FakePool ──> FakeConnection
                                     │
                                     ├── at max_size the caller waits
                                     ├── the wait ends named, at the stated bound
                                     └── close() returns the connection, pool stays open

"""

from __future__ import annotations

import asyncio
import time

import pytest

from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.resources.postgres.postgres_resource import PostgresResource

from ...support.fake_pool import FakePool, PoolAcquireTimeoutError

pytestmark = pytest.mark.benchmark

WAIT = 10.0


async def _one_unit(pool: FakePool) -> None:
    """One unit of work against the pool: open, run one statement, close."""
    resource = PostgresResource(pool=pool)
    await resource.open()
    try:
        await resource._execute("SELECT 1")
    finally:
        await resource.close()


async def test_a_third_caller_waits_for_a_ceiling_of_two() -> None:
    """At a ceiling of two, the third unit waits — the ceiling holds and it still completes."""
    pool = FakePool(min_size=0, max_size=2, timeout=5.0)
    started = [asyncio.Event(), asyncio.Event()]
    gates = [asyncio.Event(), asyncio.Event()]

    async def holder(index: int) -> None:
        resource = PostgresResource(pool=pool)
        await resource.open()
        started[index].set()
        await gates[index].wait()
        await resource.close()

    first = asyncio.create_task(holder(0))
    second = asyncio.create_task(holder(1))
    await asyncio.wait_for(started[0].wait(), timeout=WAIT)
    await asyncio.wait_for(started[1].wait(), timeout=WAIT)
    assert pool.held == 2
    assert pool.high_water == 2

    third = asyncio.create_task(_one_unit(pool))
    await asyncio.sleep(0.05)  # let the third reach the wait, if it is going to
    assert not third.done(), "the third unit must wait for a free connection"
    assert pool.held == 2, "waiting must not open a connection of its own"

    gates[0].set()
    await asyncio.wait_for(third, timeout=WAIT)
    gates[1].set()
    await asyncio.gather(first, second)

    assert pool.held == 0
    assert pool.high_water <= pool.max_size


async def test_a_wait_that_never_frees_ends_in_a_named_failure() -> None:
    """The wait is bounded by the stated value and ends in the pool's own named failure."""
    pool = FakePool(min_size=0, max_size=1, timeout=30.0)
    holder = PostgresResource(pool=pool)
    await holder.open()

    waiter = PostgresResource(pool=pool)
    waiter.acquire_timeout = 0.05
    started = time.monotonic()
    with pytest.raises(HandleError) as caught:
        await waiter.open()
    elapsed = time.monotonic() - started

    assert isinstance(caught.value.__cause__, PoolAcquireTimeoutError)
    assert 0.04 <= elapsed < 3.0, f"waited {elapsed:.3f}s for a 0.05s bound"
    assert pool.held == 1, "the holder still holds; the failed waiter left nothing behind"

    await holder.close()
    assert pool.held == 0


async def test_the_ceiling_is_never_exceeded_under_load() -> None:
    """Thirty units through a ceiling of three: the held count never goes above it."""
    pool = FakePool(min_size=0, max_size=3, timeout=5.0)

    await asyncio.gather(*(_one_unit(pool) for _ in range(30)))

    assert pool.high_water <= 3
    assert pool.held == 0


async def test_a_borrowed_connection_returns_to_a_still_open_pool() -> None:
    """The connection goes back and is handed out again; the pool itself stays open."""
    pool = FakePool(min_size=0, max_size=1, timeout=1.0)

    first = PostgresResource(pool=pool)
    await first.open()
    borrowed = pool.borrowed
    await first.close()

    assert pool.held == 0
    assert pool.free == 1
    assert pool.closed is False

    second = PostgresResource(pool=pool)
    await second.open()
    assert pool.borrowed == borrowed, "the same connection is handed out again"
    await second.close()
