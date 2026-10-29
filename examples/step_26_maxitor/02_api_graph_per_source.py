"""
02_api_graph_per_source.py — one graph per source, and every request names it

Until #214 Maxitor kept one graph in one slot per process: whoever loaded last owned
the slot, so two users opening two services overwrote each other, and every open paid a
full download and build because there was nowhere to keep a second graph.

Now every graph read names the AOA service whose graph it wants — ``?source=<graph-json
URL>`` — and the process keeps one built graph per source. A read that finds no graph
builds it; a burst of readers on one link costs one build; a built graph stays until the store
is full — at most 50 are held, the one read longest ago leaves first — and at most four builds run
at once (spec 028 removed the hour-long idle removal: the next visitor no longer waits for a build). ``POST /api/load`` is no
longer "load this into the slot" but "rebuild this source", and it leaves every other
source alone.

This script drives the real FastAPI application, with no server and no browser, against a
store whose builder returns fixtures instead of downloading:

  1. two sources side by side — each answer is its own source's graph;
  2. a cold read builds once, and a repeat read costs nothing;
  3. a read without a source — 400 that names the missing parameter;
  4. a source that cannot be built — 422 with the reason, nothing stored;
  5. a busy store — 503 with ``Retry-After``, never a wrong graph;
  6. an explicit reload rebuilds one source and leaves the other untouched;
  7. a failed reload keeps the graph already built;
  8. a graph unread for hours is still held, and its next read builds nothing;
  9. a full store evicts the least recently read graph;
 10. a burst of readers on one link builds once;
 11. a reader who leaves during a build does not cancel it for the others.

Output:

    1. Two sources side by side
       A -> ['d.a.Dom:v1']
       B -> ['d.b.Dom:v1']
       again A -> ['d.a.Dom:v1']
       held: 2, builds: 2

    2. A cold read builds once; a repeat read costs nothing
       three more reads of A -> builds added: 0

    3. A read without a source
       GET /api/v1/list-domains     -> 400 {'detail': "Missing query parameter 'source': name the graph-json URL this read is for."}
       GET /api/sidebar             -> 400 {'detail': "Missing query parameter 'source': name the graph-json URL this read is for."}

    4. A source that cannot be built
       GET /api/sidebar?source=A -> 422 {'detail': 'service is down'}
       stored for that source: 0 graphs

    5. A busy store
       GET /api/sidebar?source=A -> 503 {'detail': 'Maxitor is busy building other graphs; try again shortly.'}
       Retry-After: 5 s

    6. An explicit reload rebuilds one source
       before: A -> ['d.a.Dom:v1'], B -> ['d.b.Dom:v1']
       POST /api/load B -> 200 {'status': 'ok'}
       after:  A -> ['d.a.Dom:v1'], B -> ['d.b.Dom:v2']

    7. A failed reload keeps the graph already built
       POST /api/load B -> 422 {'detail': 'service is down'}
       B still answers with: ['d.b.Dom:v2']

    8. A graph unread for hours is still held
       six hours later -> 200 {'level1_nodes': [], 'level2_diagrams': [], 'level2_nodes': [], 'level3_diagrams': [], 'fingerprint': ''}
       builds so far: 1 (only the first read built it)

    9. A full store evicts the least recently read graph
       held sources: ('https://a.aoa.run/graph-json', 'https://c.aoa.run/graph-json')
       B was read longest ago, so B is the graph that went

    10. A burst of readers on one link builds once
       60 simultaneous reads -> 60/60 answered, builds: 1

    11. A reader who leaves during a build does not cancel it for the others
       one reader left, the other was answered -> builds: 1, held: 1

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  topic: Maxitor (system graph)

Run:
    uv run python examples/step_26_maxitor/02_api_graph_per_source.py
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import httpx
from fastapi.testclient import TestClient

from maxitor.viewer.api.app import create_app
from maxitor.viewer.api.graph_store import (
    BUSY_DETAIL,
    GraphBuildError,
    GraphEntry,
    GraphStore,
    GraphStoreBusyError,
)
from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

SOURCE_A = "https://a.aoa.run/graph-json"
SOURCE_B = "https://b.aoa.run/graph-json"
DOMAIN_A = "d.a.Dom"
DOMAIN_B = "d.b.Dom"
SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])


def _graph(domain: str) -> DuckDBGraphResource:
    """Return a real in-process graph holding one domain."""
    return DuckDBGraphResource.build_from_json(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "id": domain,
                    "label": domain,
                    "type": "Domain",
                    "properties": {"name": domain, "description": ""},
                },
            ],
            "edges": [],
        },
    )


class FakeClock:
    """A monotonic clock the script moves by hand, so an hour costs nothing."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        """Return the current fake time."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the fake time forward."""
        self.now += seconds


class RevisionBuilder:
    """A builder whose every build of a source is a new revision; it can also be told to fail."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.fail = False
        self._revisions: dict[str, int] = {}

    async def __call__(self, source: str) -> GraphEntry:
        """Record the call and return the next revision of that source, or fail."""
        self.calls.append(source)
        if self.fail:
            raise GraphBuildError("service is down")
        self._revisions[source] = self._revisions.get(source, 0) + 1
        domain = {SOURCE_A: DOMAIN_A, SOURCE_B: DOMAIN_B}.get(source, "d.other.Dom")
        return GraphEntry(
            source=source,
            graph=_graph(f"{domain}:v{self._revisions[source]}"),
            sidebar=SIDEBAR,
            last_read=0.0,
        )


class BusyStore:
    """A store whose every read finds no free build slot."""

    held = 0
    running = 0
    queued = 0

    async def acquire(self, source: str) -> GraphEntry:
        """Refuse the read, as a store that waited out its slot limit does."""
        raise GraphStoreBusyError(BUSY_DETAIL)


def _client(store: Any) -> TestClient:
    """Return a client over the real application, with ``store`` in place of the built one."""
    app = create_app()
    app.state.graph_store = store
    return TestClient(app, raise_server_exceptions=False)


def _domains(client: TestClient, source: str) -> list[str]:
    """Return the domain qualnames the list-domains route answers for ``source``."""
    answer = client.get("/api/v1/list-domains", params={"source": source})
    assert answer.status_code == 200, answer.text[:200]
    return [row["qualname"] for row in answer.json()["list_domains"]]


def _built(builder: RevisionBuilder) -> int:
    """Return how many builds the builder has run."""
    return len(builder.calls)


def main() -> None:
    """Run every case of the request contract and print what the server answered."""
    builder = RevisionBuilder()
    store = GraphStore(builder)
    client = _client(store)

    print("1. Two sources side by side")
    print(f"   A -> {_domains(client, SOURCE_A)}")
    print(f"   B -> {_domains(client, SOURCE_B)}")
    print(f"   again A -> {_domains(client, SOURCE_A)}")
    print(f"   held: {store.held}, builds: {_built(builder)}")

    print("\n2. A cold read builds once; a repeat read costs nothing")
    calls_before = _built(builder)
    for _ in range(3):
        _domains(client, SOURCE_A)
    print(f"   three more reads of A -> builds added: {_built(builder) - calls_before}")

    print("\n3. A read without a source")
    for path in ("/api/v1/list-domains", "/api/sidebar"):
        answer = client.get(path)
        print(f"   GET {path:24s} -> {answer.status_code} {answer.json()}")

    print("\n4. A source that cannot be built")
    broken = RevisionBuilder()
    broken.fail = True
    broken_store = GraphStore(broken)
    broken_client = _client(broken_store)
    answer = broken_client.get("/api/sidebar", params={"source": SOURCE_A})
    print(f"   GET /api/sidebar?source=A -> {answer.status_code} {answer.json()}")
    print(f"   stored for that source: {broken_store.held} graphs")

    print("\n5. A busy store")
    busy = _client(BusyStore())
    answer = busy.get("/api/sidebar", params={"source": SOURCE_A})
    print(f"   GET /api/sidebar?source=A -> {answer.status_code} {answer.json()}")
    print(f"   Retry-After: {answer.headers['retry-after']} s")

    print("\n6. An explicit reload rebuilds one source")
    print(f"   before: A -> {_domains(client, SOURCE_A)}, B -> {_domains(client, SOURCE_B)}")
    answer = client.post("/api/load", json={"service_url": SOURCE_B})
    print(f"   POST /api/load B -> {answer.status_code} {answer.json()}")
    print(f"   after:  A -> {_domains(client, SOURCE_A)}, B -> {_domains(client, SOURCE_B)}")

    print("\n7. A failed reload keeps the graph already built")
    builder.fail = True
    answer = client.post("/api/load", json={"service_url": SOURCE_B})
    builder.fail = False
    print(f"   POST /api/load B -> {answer.status_code} {answer.json()}")
    print(f"   B still answers with: {_domains(client, SOURCE_B)}")

    print("\n8. A graph unread for hours is still held")
    clock = FakeClock()
    quiet_builder = RevisionBuilder()
    quiet_store = GraphStore(quiet_builder, clock=clock)
    quiet_client = _client(quiet_store)
    _domains(quiet_client, SOURCE_A)
    clock.advance(6 * 3600.0)
    answer = quiet_client.get("/api/sidebar", params={"source": SOURCE_A})
    print(f"   six hours later -> {answer.status_code} {answer.json()}")
    print(f"   builds so far: {_built(quiet_builder)} (only the first read built it)")

    print("\n9. A full store evicts the least recently read graph")
    small_builder = RevisionBuilder()
    small_clock = FakeClock()
    small_store = GraphStore(small_builder, max_graphs=2, clock=small_clock)
    small_client = _client(small_store)
    _domains(small_client, SOURCE_A)
    small_clock.advance(1.0)
    _domains(small_client, SOURCE_B)
    small_clock.advance(1.0)
    _domains(small_client, SOURCE_A)  # A is now the most recently read
    small_clock.advance(1.0)
    _domains(small_client, "https://c.aoa.run/graph-json")
    print(f"   held sources: {small_store.held_sources()}")
    print("   B was read longest ago, so B is the graph that went")

    print("\n10. A burst of readers on one link builds once")
    burst_builder = RevisionBuilder()
    burst_store = GraphStore(burst_builder)
    burst_app = create_app()
    burst_app.state.graph_store = burst_store

    async def burst() -> tuple[int, int]:
        transport = httpx.ASGITransport(app=burst_app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://maxitor.test") as http:
            answers = await asyncio.gather(
                *(http.get("/api/sidebar", params={"source": SOURCE_A}) for _ in range(60)),
            )
        return sum(1 for answer in answers if answer.status_code == 200), len(answers)

    okay, total = asyncio.run(burst())
    print(f"   60 simultaneous reads -> {okay}/{total} answered, builds: {_built(burst_builder)}")

    print("\n11. A reader who leaves during a build does not cancel it for the others")
    gate = asyncio.Event()
    leaving_builder = RevisionBuilder()

    async def gated(source: str) -> GraphEntry:
        leaving_builder.calls.append(source)
        await gate.wait()
        return GraphEntry(source=source, graph=_graph(DOMAIN_A), sidebar=SIDEBAR, last_read=0.0)

    leaving_store = GraphStore(gated)

    async def leaving_reader() -> str:
        leaving = asyncio.create_task(leaving_store.acquire(SOURCE_A))
        waiting = asyncio.create_task(leaving_store.acquire(SOURCE_A))
        await asyncio.sleep(0)
        leaving.cancel()
        try:
            await leaving
        except asyncio.CancelledError:
            pass
        gate.set()
        await waiting
        return f"builds: {len(leaving_builder.calls)}, held: {leaving_store.held}"

    print(f"   one reader left, the other was answered -> {asyncio.run(leaving_reader())}")


if __name__ == "__main__":
    main()
