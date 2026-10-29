# packages/maxitor/front/src/maxitor/front/api/graph_store.py
"""
GraphStore — built graphs keyed by the source they were built from.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor draws diagrams of an AOA service the user names in ``?source=``. Until #214 the
application kept one graph in one slot, so two users opening two services overwrote each
other and every open paid a full download and build. The store below keeps one entry per
source instead: the DuckDB graph and the sidebar built from it travel together, a source
is built once however many readers arrive, and a burst of readers on one link costs one
download.

What the store does not do matters as much as what it does. It never closes a DuckDB
connection by force: removing or replacing an entry only drops the store's reference, and
a request that already holds the entry keeps it. It never re-checks a source on a timer.
And it bounds its own cost: at most ``max_graphs`` entries — a built graph stays until that
limit is reached, and then the one read longest ago leaves — and at most
``max_concurrent_builds`` builds run at once, so a burst of *different* sources cannot create
hundreds of graphs before the capacity limit could act. A graph nobody read for an hour is
kept on purpose: the first visitor after a quiet period gets it without a download.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    acquire(source) ──► sweep() ──► held? ──► touch last_read, return
                            │              │
                            │              └► failed recently? ──► GraphBuildError(reason)
                            │
                            └► one build in flight? ──► await it (shielded)
                                       │
                                       └► start build task ──► builder(source)
                                                                 │
                                             asyncio.Semaphore  │ download + DuckDB build
                                                                 ▼
                                                    store entry, evict beyond max_graphs

    reload(source) ──► sweep() ──► wait for the one build in flight (no slot held)
                            └────► build again; replace the entry only when the build
                                   succeeds, ignore the failure memory

Every build runs as its own task and every waiter awaits it through ``asyncio.shield``:
a reader who closes the tab stops waiting, but the build goes on for everyone else and
its entry is still stored. The build takes its slot *inside* the task and only after any
wait on the in-flight build — a caller that held a slot while waiting for another build
would deadlock once four callers did it.

``POST /api/sidebar``-era callers see the sidebar answered from the entry's ``sidebar``;
diagram actions see its ``graph``. Removing or replacing an entry drops only the store's
reference: CPython frees the graph when the last request still using it lets go.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from maxitor.front.model.core.actions.left_sidebar_action import GetLeftMenuSidebarDataAction
from maxitor.front.model.core.actions.load_aoa_service_action import LoadAOAServiceAction, LoadAOAServiceParams
from maxitor.front.model.core.resources.graph_source_gateway import GRAPH_SOURCE_CONNECTION_KEY, GraphSourceGateway
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

from aoa.action_machine.context import Context
from aoa.action_machine.model import ParamsStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

#: A source that failed to build is refused without a new download for this long.
FAILURE_MEMORY_SECONDS = 10.0

#: A build that waits longer than this for a free slot is refused with "busy".
SLOT_WAIT_SECONDS = 30.0

#: The 503 the middleware answers with; kept beside the wait it belongs to.
BUSY_DETAIL = "Maxitor is busy building other graphs; try again shortly."


class GraphBuildError(Exception):
    """A source could not be downloaded or built; the reason is the message."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class GraphStoreBusyError(Exception):
    """No build slot freed within the wait limit, so the source was not even tried."""


@dataclass(slots=True)
class GraphEntry:
    """
    One build of one source: its DuckDB graph and the sidebar built from that same graph.

    AI-CORE-BEGIN
    ROLE: The unit the store keeps, hands to one request, and drops when it is evicted.
    CONTRACT: ``graph`` answers every diagram query of a request; ``sidebar`` answers the sidebar read.
    INVARIANTS: ``graph``, ``sidebar`` and ``content_sha256`` come from one build; the entry is never
    mutated after it is built, except ``last_read`` (moved on every read), ``last_checked`` and
    ``checking`` (moved by the freshness checks of the source).
    AI-CORE-END
    """

    source: str
    graph: DuckDBGraphResource
    sidebar: Any
    last_read: float
    content_sha256: str = ""
    """SHA-256 of the ``graph-json`` body the graph was built from."""
    etag: str | None = None
    """The source's ``ETag`` for that body, when it gave one."""
    last_modified: str | None = None
    """The source's ``Last-Modified`` for that body, when it gave one."""
    last_checked: float = 0.0
    """When the source was last asked whether its graph changed."""
    checking: bool = False
    """Whether a check of the source is running now; checks of one source never overlap."""

    @property
    def fingerprint(self) -> str:
        """What identifies the built content to a tab: the SHA-256 of the body it was built from."""
        return self.content_sha256


class GraphStore:
    """
    Process-local map from a source to its built graph, with single flight and bounded cost.

    AI-CORE-BEGIN
    ROLE: The one place that knows which sources this process has built, and builds the rest.
    CONTRACT: ``acquire`` never hands back "not loaded" — it builds; ``reload`` rebuilds one source,
    replaces its entry only when the build succeeds and leaves every other alone; a build that cannot
    get a slot raises ``GraphStoreBusyError``.
    INVARIANTS: At most ``max_graphs`` entries; at most ``max_concurrent_builds`` builds running;
    one build in flight per source of any kind; a failed source is remembered ``FAILURE_MEMORY_SECONDS``
    but a busy one never is; an entry is only ever dropped, never closed.
    AI-CORE-END
    """

    def __init__(
        self,
        builder: Callable[[str], Awaitable[GraphEntry]],
        *,
        max_graphs: int = 50,
        max_concurrent_builds: int = 4,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._builder = builder
        self._max_graphs = max_graphs
        self._clock = clock
        self._entries: dict[str, GraphEntry] = {}
        self._in_flight: dict[str, asyncio.Task[GraphEntry]] = {}
        self._failures: dict[str, tuple[str, float]] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_builds)
        self._running = 0
        self._queued = 0

    @property
    def held(self) -> int:
        """Number of graphs held right now."""
        return len(self._entries)

    @property
    def running(self) -> int:
        """Number of builds running right now."""
        return self._running

    @property
    def queued(self) -> int:
        """Number of builds waiting for a free slot right now."""
        return self._queued

    def now(self) -> float:
        """The store's clock: the time ``last_read`` and ``last_checked`` are measured on."""
        return self._clock()

    def held_sources(self) -> tuple[str, ...]:
        """Return the sources held right now, in insertion order."""
        return tuple(self._entries)

    def peek(self, source: str) -> GraphEntry | None:
        """Return the entry held for ``source`` without counting it as a read, or ``None``."""
        return self._entries.get(source)

    async def acquire(self, source: str) -> GraphEntry:
        """Return the built entry for ``source``, building it when the store does not hold it."""
        self.sweep()
        entry = self._entries.get(source)
        if entry is not None:
            entry.last_read = self._clock()
            return entry
        failure = self._failures.get(source)
        if failure is not None:
            raise GraphBuildError(failure[0])
        return await asyncio.shield(self._build_task(source))

    async def reload(self, source: str) -> GraphEntry:
        """Build ``source`` again and replace its entry; on failure keep the entry and raise."""
        self.sweep()
        running = self._in_flight.get(source)
        if running is not None:
            # Wait before taking a slot: a caller that held a slot while awaiting another build
            # would deadlock as soon as enough callers did it.
            try:
                await asyncio.shield(running)
            except (GraphBuildError, GraphStoreBusyError):
                pass
        entry = await asyncio.shield(self._build_task(source))
        self._failures.pop(source, None)
        return entry

    def sweep(self) -> None:
        """Forget failures older than the memory window; held graphs leave only beyond ``max_graphs``."""
        now = self._clock()
        for source in [
            name for name, (_, failed_at) in self._failures.items() if now - failed_at > FAILURE_MEMORY_SECONDS
        ]:
            del self._failures[source]

    def _build_task(self, source: str) -> asyncio.Task[GraphEntry]:
        """Start the one build for ``source``, or return the one already running."""
        task = self._in_flight.get(source)
        if task is None:
            task = asyncio.create_task(self._build_and_store(source))
            self._in_flight[source] = task
        return task

    async def _build_and_store(self, source: str) -> GraphEntry:
        """Build ``source`` inside a slot, remember its failure, and store it on success."""
        try:
            entry = await self._build_under_slot(source)
        except GraphBuildError as exc:
            self._failures[source] = (exc.reason, self._clock())
            raise
        finally:
            if self._in_flight.get(source) is asyncio.current_task():
                del self._in_flight[source]
        entry.last_read = self._clock()
        # A graph just built from a fresh download needs no check before its interval has passed.
        entry.last_checked = entry.last_read
        self._store(source, entry)
        self._failures.pop(source, None)
        return entry

    async def _build_under_slot(self, source: str) -> GraphEntry:
        """Wait for a free slot with the busy timeout, then run the builder."""
        self._queued += 1
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=SLOT_WAIT_SECONDS)
        except TimeoutError:
            raise GraphStoreBusyError(BUSY_DETAIL) from None
        finally:
            self._queued -= 1

        self._running += 1
        try:
            return await self._builder(source)
        except GraphBuildError:
            raise
        except Exception as exc:
            raise GraphBuildError(str(exc)) from exc
        finally:
            self._running -= 1
            self._semaphore.release()

    def _store(self, source: str, entry: GraphEntry) -> None:
        """Insert or replace ``source``'s entry, evicting the least recently read one if needed."""
        if source not in self._entries and len(self._entries) >= self._max_graphs:
            oldest = min(self._entries, key=lambda name: self._entries[name].last_read)
            del self._entries[oldest]
        self._entries[source] = entry


async def build_graph_entry(machine: ActionProductMachine, gateway: GraphSourceGateway, source: str) -> GraphEntry:
    """Build one entry for ``source`` by running the two actions the load route runs; download through ``gateway``."""
    try:
        load_result = await machine.run(
            Context(),
            LoadAOAServiceAction(),
            LoadAOAServiceParams(service_url=source),
            connections={GRAPH_SOURCE_CONNECTION_KEY: gateway},
        )
        sidebar_result = await machine.run(
            Context(),
            GetLeftMenuSidebarDataAction(),
            ParamsStub(),
            connections={DUCKDB_GRAPH_CONNECTION_KEY: load_result.graph_resource},
        )
    except Exception as exc:
        raise GraphBuildError(str(exc)) from exc
    return GraphEntry(
        source=source,
        graph=load_result.graph_resource,
        sidebar=sidebar_result,
        last_read=0.0,
        content_sha256=load_result.content_sha256,
        etag=load_result.etag or None,
        last_modified=load_result.last_modified or None,
    )
