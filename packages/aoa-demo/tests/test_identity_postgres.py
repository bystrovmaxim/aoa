# packages/aoa-demo/tests/test_identity_postgres.py
"""
The identity domain: one connection per call, over a pool, and without a database.

This is the demo's own exercise of the pattern the #215 work introduced. It runs
in two modes, and both are checked here:

* **without a connection description** the route declares the in-memory store, so
  the demo answers with no PostgreSQL and with no driver installed;
* **with one** the route declares a per-call resource over the application's pool,
  and the pool is created at startup and closed at shutdown.

The pool is faked: ``IdentityStore`` only ever calls ``acquire``, ``release`` and
the connection's own ``execute`` / ``fetch``, so nothing here needs a server. The
connection enforces the driver's one-operation-at-a-time rule, which is what makes
"concurrent calls do not fail" mean something.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    identity_connection()
        │  no DSN  -> PerCallConnection(IdentityStoreStub)
        └── DSN     -> PerCallConnection(IdentityStore(pool=holder.require()))
                              │
                              v
                        _FakePool -> _FakeConnection   (one call, one connection)

"""

from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any

import pytest

from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.demo.fastapi_mcp_services.infrastructure import (
    DEMO_DSN_ENV,
    PoolHolder,
    identity_connection,
    pool_holder,
    pool_lifespan,
)
from aoa.demo.model.identity.resources.identity_store_stub import IdentityStoreStub

PERSON = {"id": "person-1", "email": "person-1@example.test", "display_name": "Person One"}
AT = "2026-10-16T12:00:00Z"
WAIT = 2.0


class _FakeConnection:
    """One connection: one operation at a time, with rows for the person lookup."""

    def __init__(self) -> None:
        self._busy = False
        self.operations: list[str] = []

    async def execute(self, query: str, *args: Any) -> str:
        """Run a statement, refusing a second operation while one is in flight."""
        return await self._operation(query)

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Answer the person lookup with the seeded row."""
        await self._operation(query)
        return [dict(PERSON)]

    async def _operation(self, query: str) -> str:
        if self._busy:
            raise RuntimeError("another operation is in progress")
        self._busy = True
        try:
            await asyncio.sleep(0)  # a real statement awaits; a concurrent caller must collide
            self.operations.append(query)
            return "OK"
        finally:
            self._busy = False


class _Acquire:
    """What ``_FakePool.acquire`` returns: awaitable, and usable as a context manager."""

    def __init__(self, pool: _FakePool) -> None:
        self._pool = pool
        self._conn: _FakeConnection | None = None

    async def _take(self) -> _FakeConnection:
        if self._conn is None:
            self._conn = await self._pool._take()
        return self._conn

    def __await__(self) -> Any:
        return self._take().__await__()

    async def __aenter__(self) -> _FakeConnection:
        return await self._take()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._conn is not None:
            await self._pool.release(self._conn)
            self._conn = None


class _FakePool:
    """A pool that hands out one connection per borrow and records its high-water mark.

    It deliberately does not bound anything: what this file checks is the per-call
    lifecycle — borrow, use, return — and the pool's own bounds are exercised by the
    resource-layer tests.
    """

    def __init__(self) -> None:
        self.closed = False
        self.high_water = 0
        self._free: list[_FakeConnection] = []
        self._held: set[_FakeConnection] = set()
        self._all: list[_FakeConnection] = []

    @property
    def held(self) -> int:
        """How many connections are currently borrowed."""
        return len(self._held)

    @property
    def connections(self) -> tuple[_FakeConnection, ...]:
        """Every connection this pool created, oldest first."""
        return tuple(self._all)

    def acquire(self, *, timeout: float | None = None) -> _Acquire:
        """Return an awaitable proxy that yields a connection."""
        return _Acquire(self)

    async def _take(self) -> _FakeConnection:
        conn = self._free.pop() if self._free else self._new_connection()
        self._held.add(conn)
        self.high_water = max(self.high_water, len(self._held))
        return conn

    def _new_connection(self) -> _FakeConnection:
        conn = _FakeConnection()
        self._all.append(conn)
        return conn

    async def release(self, conn: object) -> None:
        """Return a borrowed connection to the pool."""
        if not isinstance(conn, _FakeConnection):
            raise RuntimeError("connection did not come from this pool")
        self._held.discard(conn)
        self._free.append(conn)

    async def close(self) -> None:
        """Close the pool itself."""
        self.closed = True


async def _unit_of_work(pool: _FakePool) -> None:
    """One call's use of the store: open, read, write in one transaction, close."""
    store = _postgres_store(pool)
    await store.open()
    try:
        await store.read_person("person-1")
        await store.record_login("person-1", AT)
    finally:
        await store.close()


def _postgres_store(pool: _FakePool) -> Any:
    """Build the PostgreSQL store over the fake pool; the driver import is the caller's gate."""
    from aoa.demo.model.identity.resources.identity_store import IdentityStore

    return IdentityStore(pool=pool)


# ═════════════════════════════════════════════════════════════════════════════
# The holder (FR-013) — no driver, no database
# ═════════════════════════════════════════════════════════════════════════════


def test_the_holder_names_the_situation_before_it_is_filled() -> None:
    """Reading an unfilled holder is a named failure, not an attribute error."""
    with pytest.raises(HandleError, match="no pool"):
        PoolHolder().require()


async def test_without_a_dsn_the_route_declares_the_in_memory_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """The database-free mode answers through the stub, and the lifecycle is the same."""
    monkeypatch.delenv(DEMO_DSN_ENV, raising=False)

    async with connection_scope({"identity": identity_connection()}) as connections:
        store = connections["identity"]
        assert isinstance(store, IdentityStoreStub)
        rows = await store.read_person("person-1")
        await store.record_login("person-1", AT)

    assert rows == [PERSON]
    assert store.logins == [{"person_id": "person-1", "at": AT}]


# ═════════════════════════════════════════════════════════════════════════════
# The PostgreSQL mode — the driver is imported only by the tests that need it
# ═════════════════════════════════════════════════════════════════════════════


async def test_concurrent_calls_do_not_fail() -> None:
    """Twenty concurrent calls, one connection each, none refused for sharing a session."""
    pytest.importorskip("asyncpg")
    pool = _FakePool()

    results = await asyncio.gather(*(_unit_of_work(pool) for _ in range(20)), return_exceptions=True)

    assert [r for r in results if isinstance(r, BaseException)] == []
    assert pool.held == 0
    assert pool.high_water == 20, "twenty concurrent calls hold twenty connections"


async def test_two_transactions_do_not_interleave() -> None:
    """Both transactions are open at once, and each connection keeps its own statements."""
    pytest.importorskip("asyncpg")
    pool = _FakePool()
    barrier = asyncio.Barrier(2)

    async def login(tag: str) -> None:
        store = _postgres_store(pool)
        await store.open()
        try:
            await store.begin()
            await asyncio.wait_for(barrier.wait(), timeout=WAIT)
            await store.execute(f"INSERT {tag}")
            await store.commit()
        finally:
            await store.close()

    await asyncio.gather(login("a"), login("b"))

    per_connection = [conn.operations for conn in pool.connections]
    assert sorted(per_connection) == [["BEGIN", "INSERT a", "COMMIT"], ["BEGIN", "INSERT b", "COMMIT"]]
    assert pool.held == 0


async def test_the_finalizer_runs_once_per_call() -> None:
    """The boundary closes each call's store, so the connection comes back every time."""
    pytest.importorskip("asyncpg")
    pool = _FakePool()
    finalized: list[int] = []

    async def finalize(store: BaseResource) -> None:
        finalized.append(1)
        await store.close()  # type: ignore[attr-defined]

    declaration = PerCallConnection(factory=lambda: _postgres_store(pool), finalize=finalize)
    for _ in range(3):
        async with connection_scope({"identity": declaration}) as connections:
            await connections["identity"].read_person("person-1")  # type: ignore[attr-defined]

    assert finalized == [1, 1, 1]
    assert pool.held == 0


def test_the_postgres_store_states_its_wait_bound() -> None:
    """FR-009's stated value lives on the resource: the pool's creation carries no wait bound."""
    pytest.importorskip("asyncpg")
    from aoa.demo.model.identity.resources.identity_store import IdentityStore

    assert IdentityStore.acquire_timeout == 30.0


async def test_the_pool_is_created_once_and_closed_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    """The lifespan is the one place the pool exists: created with stated bounds, closed after."""
    asyncpg = pytest.importorskip("asyncpg")
    pool = _FakePool()
    seen: dict[str, Any] = {}

    async def fake_create_pool(dsn: str, **kwargs: Any) -> _FakePool:
        seen["dsn"] = dsn
        seen["kwargs"] = kwargs
        return pool

    monkeypatch.setattr(asyncpg, "create_pool", fake_create_pool)
    monkeypatch.setenv(DEMO_DSN_ENV, "postgresql://example/db")

    async with pool_lifespan(None):
        assert pool_holder.pool is pool

    assert pool.closed is True
    assert pool_holder.pool is None
    assert seen["dsn"] == "postgresql://example/db"
    assert seen["kwargs"] == {"min_size": 1, "max_size": 10}
