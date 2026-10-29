# packages/maxitor/front/tests/test_api_graph_store.py
"""Tests for GraphStore: one built graph per source, built once, bounded, and never forced shut."""

from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest
from maxitor.front.api import graph_store as graph_store_module
from maxitor.front.api.graph_store import GraphBuildError, GraphEntry, GraphStore, GraphStoreBusyError

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _entry(source: str, marker: str) -> GraphEntry:
    """Return an entry whose graph and sidebar both carry ``marker``."""
    return GraphEntry(source=source, graph=cast(Any, marker), sidebar=cast(Any, marker), last_read=0.0)


class FakeClock:
    """A monotonic clock the test moves by hand, so nothing sleeps."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        """Return the current fake time."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the fake time forward."""
        self.now += seconds


class RecordingBuilder:
    """A builder that records calls and can hold a build open, slow it down, or fail it."""

    def __init__(self, *, delay: float = 0.0, gate: asyncio.Event | None = None) -> None:
        self.calls: list[str] = []
        self.running = 0
        self.max_running = 0
        self._delay = delay
        self._gate = gate
        self._counter = 0
        self.fail_with: str | None = None

    async def __call__(self, source: str) -> GraphEntry:
        """Record the call, wait as configured, then return a fresh entry or fail."""
        self.calls.append(source)
        self._counter += 1
        marker = f"{source}#{self._counter}"
        self.running += 1
        self.max_running = max(self.max_running, self.running)
        try:
            if self._gate is not None:
                await self._gate.wait()
            if self._delay:
                await asyncio.sleep(self._delay)
            if self.fail_with is not None:
                raise GraphBuildError(self.fail_with)
            return _entry(source, marker)
        finally:
            self.running -= 1


# ─── Holding graphs by source ───────────────────────────────────────────────


async def test_two_sources_live_side_by_side() -> None:
    """Two sources are held at once, and reading one does not build the other again."""
    builder = RecordingBuilder()
    store = GraphStore(builder, clock=FakeClock())

    first = await store.acquire("https://a.test/graph-json")
    second = await store.acquire("https://b.test/graph-json")

    assert first.graph is not second.graph
    assert store.held == 2
    again = await store.acquire("https://a.test/graph-json")
    assert again is first
    assert builder.calls == ["https://a.test/graph-json", "https://b.test/graph-json"]


async def test_concurrent_reads_of_one_source_build_it_once() -> None:
    """Ten readers of one cold source share one build and one entry."""
    builder = RecordingBuilder(delay=0.01)
    store = GraphStore(builder, clock=FakeClock())

    entries = await asyncio.gather(*(store.acquire("https://a.test/graph-json") for _ in range(10)))

    assert builder.calls == ["https://a.test/graph-json"]
    assert len({id(entry) for entry in entries}) == 1


async def test_first_reader_leaving_does_not_cancel_the_build() -> None:
    """A cancelled waiter stops waiting; the build goes on and its entry is stored for the rest."""
    gate = asyncio.Event()
    builder = RecordingBuilder(gate=gate)
    store = GraphStore(builder, clock=FakeClock())

    leaving = asyncio.create_task(store.acquire("https://a.test/graph-json"))
    waiting = asyncio.create_task(store.acquire("https://a.test/graph-json"))
    await asyncio.sleep(0)
    leaving.cancel()
    with pytest.raises(asyncio.CancelledError):
        await leaving

    gate.set()
    entry = await waiting
    assert builder.calls == ["https://a.test/graph-json"]
    assert store.held == 1
    assert (await store.acquire("https://a.test/graph-json")) is entry


# ─── Failures ───────────────────────────────────────────────────────────────


async def test_a_failed_source_is_remembered_for_ten_seconds() -> None:
    """A failure is refused without a new download for 10 s, then the source is tried again."""
    builder = RecordingBuilder()
    builder.fail_with = "unreachable"
    clock = FakeClock()
    store = GraphStore(builder, clock=clock)

    with pytest.raises(GraphBuildError, match="unreachable"):
        await store.acquire("https://a.test/graph-json")
    with pytest.raises(GraphBuildError, match="unreachable"):
        await store.acquire("https://a.test/graph-json")
    assert builder.calls == ["https://a.test/graph-json"]

    clock.advance(11.0)
    with pytest.raises(GraphBuildError, match="unreachable"):
        await store.acquire("https://a.test/graph-json")
    assert len(builder.calls) == 2


async def test_a_busy_store_does_not_remember_the_source_as_failed() -> None:
    """A missing slot says nothing about the source: the next read builds it."""
    gate = asyncio.Event()
    builder = RecordingBuilder(gate=gate)
    store = GraphStore(builder, max_concurrent_builds=1, clock=FakeClock())
    original = graph_store_module.SLOT_WAIT_SECONDS
    graph_store_module.SLOT_WAIT_SECONDS = 0.02
    holding = asyncio.create_task(store.acquire("https://a.test/graph-json"))
    try:
        await asyncio.sleep(0)
        # The timeout makes a store without the slot bound fail at once instead of hanging here.
        with pytest.raises(GraphStoreBusyError):
            await asyncio.wait_for(store.acquire("https://b.test/graph-json"), timeout=1.0)
    finally:
        graph_store_module.SLOT_WAIT_SECONDS = original
        gate.set()
        await holding

    # B was not remembered as a failure: the same store builds it now that a slot is free.
    built = await store.acquire("https://b.test/graph-json")
    assert built.source == "https://b.test/graph-json"
    assert "https://b.test/graph-json" in builder.calls


# ─── Bounds ─────────────────────────────────────────────────────────────────


async def test_the_least_recently_read_graph_is_evicted_when_full() -> None:
    """With two graphs held, a third removes the one read longest ago — not the newest."""
    builder = RecordingBuilder()
    clock = FakeClock()
    store = GraphStore(builder, max_graphs=2, clock=clock)

    await store.acquire("A")
    clock.advance(1.0)
    await store.acquire("B")
    clock.advance(1.0)
    await store.acquire("A")  # A is now the most recently read
    clock.advance(1.0)
    await store.acquire("C")

    assert store.held_sources() == ("A", "C")


async def test_a_graph_unread_for_hours_is_still_held() -> None:
    """A held graph is not removed for being idle: hours later it answers without a new build (spec 028, FR-080)."""
    builder = RecordingBuilder()
    clock = FakeClock()
    store = GraphStore(builder, clock=clock)

    await store.acquire("A")
    clock.advance(3 * 3600.0)
    await store.acquire("B")  # sweeps, and must not drop A
    again = await store.acquire("A")

    assert store.held_sources() == ("A", "B")
    assert cast(str, again.graph) == "A#1"
    assert builder.calls == ["A", "B"]


async def test_an_entry_held_by_a_reader_survives_eviction() -> None:
    """Evicting an entry only drops the store's reference; the reader keeps its graph."""
    builder = RecordingBuilder()
    store = GraphStore(builder, max_graphs=1, clock=FakeClock())

    held = await store.acquire("A")
    await store.acquire("B")  # the limit evicts A

    assert "A" not in store.held_sources()
    assert cast(str, held.graph) == "A#1"


async def test_a_read_started_before_a_rebuild_keeps_its_entry() -> None:
    """A rebuild swaps the store's entry; a request that already holds the old one keeps it."""
    builder = RecordingBuilder()
    store = GraphStore(builder, clock=FakeClock())

    held = await store.acquire("A")
    await store.reload("A")

    assert cast(str, held.graph) == "A#1"
    assert cast(str, cast(GraphEntry, store.peek("A")).graph) == "A#2"


async def test_peek_does_not_count_as_a_read() -> None:
    """``peek`` returns the held entry without moving its last read, so it never keeps a graph alive."""
    builder = RecordingBuilder()
    clock = FakeClock()
    store = GraphStore(builder, max_graphs=2, clock=clock)

    await store.acquire("A")
    clock.advance(10.0)
    await store.acquire("B")
    clock.advance(10.0)
    assert store.peek("A") is not None  # does not make A the most recent
    await store.acquire("C")  # evicts the least recently read: A

    assert store.held_sources() == ("B", "C")
    assert store.peek("missing") is None


async def test_twenty_cold_sources_never_build_more_than_four_at_once() -> None:
    """The bound is across sources, not only per source (SC-009)."""
    builder = RecordingBuilder(delay=0.01)
    store = GraphStore(builder, max_concurrent_builds=4, clock=FakeClock())

    entries = await asyncio.gather(*(store.acquire(f"S{index}") for index in range(20)))

    assert len(entries) == 20
    assert builder.max_running <= 4


async def test_counters_report_held_running_and_queued() -> None:
    """The counters the health answer reports follow the store's real state."""
    gate = asyncio.Event()
    builder = RecordingBuilder(gate=gate)
    store = GraphStore(builder, max_concurrent_builds=1, clock=FakeClock())

    first = asyncio.create_task(store.acquire("A"))
    await asyncio.sleep(0)
    second = asyncio.create_task(store.acquire("B"))
    for _ in range(10):  # let B reach the semaphore and start waiting
        await asyncio.sleep(0)
        if store.queued:
            break

    assert store.running == 1
    assert store.queued == 1

    gate.set()
    await asyncio.gather(first, second)
    assert store.held == 2
    assert store.running == 0
    assert store.queued == 0


# ─── Reload ─────────────────────────────────────────────────────────────────


async def test_reload_replaces_one_source_and_keeps_the_old_entry_on_failure() -> None:
    """A successful reload swaps the entry; a failed one keeps the graph already built."""
    builder = RecordingBuilder()
    store = GraphStore(builder, clock=FakeClock())

    old = await store.acquire("A")
    fresh = await store.reload("A")
    assert fresh is not old
    assert cast(str, fresh.graph) == "A#2"
    assert (await store.acquire("A")) is fresh

    builder.fail_with = "service is down"
    with pytest.raises(GraphBuildError, match="service is down"):
        await store.reload("A")
    kept = await store.acquire("A")
    assert kept is fresh


async def test_reload_during_a_cold_build_stores_the_reloads_graph() -> None:
    """`reload` waits for the build already running; the entry stored last is always its own (SC-010)."""
    cold_started = asyncio.Event()
    release = asyncio.Event()
    calls: list[str] = []

    async def builder(source: str) -> GraphEntry:
        calls.append(source)
        if len(calls) == 1:
            cold_started.set()
            await release.wait()
            return _entry(source, "cold")
        return _entry(source, "fresh")

    store = GraphStore(builder, clock=FakeClock())
    cold = asyncio.create_task(store.acquire("A"))
    await cold_started.wait()

    reloaded = asyncio.create_task(store.reload("A"))
    await asyncio.sleep(0.01)  # reload is now waiting on the in-flight build, holding no slot
    release.set()

    await cold
    entry = await asyncio.wait_for(reloaded, timeout=2.0)

    assert cast(str, entry.graph) == "fresh"
    assert cast(str, (await store.acquire("A")).graph) == "fresh"
    assert calls == ["A", "A"]


async def test_reload_alongside_a_cold_read_does_not_deadlock() -> None:
    """`reload` and `acquire` of one cold source both finish: the reload holds no slot while it waits."""
    builder = RecordingBuilder()
    store = GraphStore(builder, max_concurrent_builds=1, clock=FakeClock())

    cold = asyncio.create_task(store.acquire("A"))
    reloaded = asyncio.create_task(store.reload("A"))

    await asyncio.wait_for(asyncio.gather(cold, reloaded), timeout=2.0)
    assert len(builder.calls) == 2


async def test_a_build_that_cannot_get_a_slot_raises_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Waiting past the slot limit raises the busy error instead of hanging (FR-025)."""
    gate = asyncio.Event()
    builder = RecordingBuilder(gate=gate)
    store = GraphStore(builder, max_concurrent_builds=1, clock=FakeClock())
    monkeypatch.setattr(graph_store_module, "SLOT_WAIT_SECONDS", 0.02)

    holding = asyncio.create_task(store.acquire("A"))
    try:
        await asyncio.sleep(0)
        with pytest.raises(GraphStoreBusyError, match="busy"):
            await asyncio.wait_for(store.acquire("B"), timeout=1.0)
    finally:
        gate.set()
        await holding


async def test_sweep_forgets_a_failure_older_than_its_memory_window() -> None:
    """The failure map does not grow forever: sweep trims what is past the window."""
    builder = RecordingBuilder()
    builder.fail_with = "boom"
    clock = FakeClock()
    store = GraphStore(builder, clock=clock)

    with pytest.raises(GraphBuildError):
        await store.acquire("A")
    clock.advance(11.0)
    store.sweep()

    builder.fail_with = None
    assert (await store.acquire("A")).source == "A"
